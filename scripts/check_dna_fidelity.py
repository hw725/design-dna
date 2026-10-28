#!/usr/bin/env python3
"""design-dna Phase 3 산출물이 DNA JSON에 충실한지 기계적으로 대조한다.

references/generation-guide.md 의 Quality Checks 중 **자동 판정 가능한 항목만**
검사한다. mood·composition 같은 정성 항목은 사람이 본다 — 여기서 PASS가 나와도
"DNA를 배신하지 않았다"는 뜻이지 "좋은 디자인이다"는 뜻이 아니다.

사용:
    py check_dna_fidelity.py <dna.json> <output.html> [--json-out FILE]

종료 코드: 0 = 위반 없음, 1 = 위반 있음, 2 = 입력 오류.

로컬 추가(upstream zanwei/design-dna 에는 없음) — 2026-08-16.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ── CJK Text Contract E3 (CJK-TEXT-CONTRACT.md) ──────────────────
# 한국어 Windows 콘솔의 기본은 cp949 다. 한글은 cp949 에 있지만 《—》·《《》》·《✓》 는
# 없어서, 그런 글자를 print 하면 UnicodeEncodeError 로 **즉사한다.** 이 PC 는
# 사용자 환경변수 PYTHONUTF8=1 이 박혀 있어 겪지 않는다 — 받는 사람 PC 에는 없다.
# 스킬끼리는 import 하지 않으므로(각자 junction 으로 따로 배포된다) 네 줄을 품는다.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        pass  # 파이프·리다이렉트 등 재설정 불가 환경

# ── WCAG 임계값 ────────────────────────────────────────────────────────────
AA_BODY = 4.5
AA_LARGE = 3.0

# visual_effects.<key> 가 enabled:false 인데 산출물에 나타나면 위반.
# 키는 스키마의 효과 카테고리, 값은 코드에서 그 효과를 쓴 증거가 되는 패턴.
EFFECT_EVIDENCE = {
    "canvas_2d": r"<canvas\b|getContext\(\s*['\"]2d",
    "webgl_3d": r"getContext\(\s*['\"]webgl|three\.module|THREE\.|<script[^>]+three",
    "particles": r"particles?\.js|tsparticles",
    "shaders": r"createShader|fragmentShader|vertexShader|glsl",
    "scroll_effects": r"IntersectionObserver|ScrollTrigger|scroll-timeline",
    "cursor_effects": r"cursor-trail|mousemove.*(?:trail|follow)",
    "svg_animation": r"<animate\b|<animateTransform\b",
    "glassmorphism": r"backdrop-filter",
    "gradient_animation": r"@keyframes[^}]*gradient|animation:[^;]*gradient",
}


def strip_comments(text: str) -> str:
    """주석을 제거한다.

    주석은 실행 코드가 아니다. 제거하지 않으면 "이 효과를 쓰지 않는다"고
    설명한 문장이 "그 효과를 썼다"는 증거로 오탐된다(2026-08-16 실측:
    enabled:false 를 설명한 주석의 'webgl' 단어가 위반으로 잡혔다).
    """

    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    return text


def hexes(text: str) -> set[str]:
    return {m.group(0).upper() for m in re.finditer(r"#[0-9A-Fa-f]{3,8}\b", text)}


def _luminance(value: str) -> float:
    h = value.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    h = h[:6]
    channels = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))

    def linear(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (linear(c) for c in channels)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg: str, bg: str) -> float:
    a, b = _luminance(fg), _luminance(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def collect_pairs(dna: dict) -> list[tuple[str, str, str]]:
    """DNA에서 대비를 재야 할 (라벨, 전경, 배경) 쌍을 만든다.

    스키마가 자유 필드라 위치가 고정적이지 않으므로, surface 계열을 배경
    후보로, ink/text/primary 계열을 전경 후보로 삼아 조합한다. 찾지 못하면
    빈 목록을 돌려주고 검사를 건너뛴다 — 없는 근거로 판정하지 않는다.
    """

    blob = json.dumps(dna, ensure_ascii=False)
    backgrounds: dict[str, str] = {}
    foregrounds: dict[str, str] = {}
    for m in re.finditer(r'"([\w.\- ]+)"\s*:\s*"(#[0-9A-Fa-f]{3,8})"', blob):
        key, value = m.group(1).lower(), m.group(2)
        if any(k in key for k in ("background", "ground", "card", "surface", "bg")):
            backgrounds.setdefault(key, value)
        elif any(k in key for k in ("ink", "text", "foreground", "accent", "primary")):
            foregrounds.setdefault(key, value)

    # `*_ink`/`on-*` 계열은 **그 짝 배경 위에서만** 쓰이는 전경이다
    # (accent_ink는 accent 버튼 위 글자다). 일반 배경과 조합하면 실제로
    # 존재하지 않는 쌍을 만들어 오탐이 된다(2026-08-16 실측: accent_ink
    # on ground 1.19:1 같은 쌍 3건이 WARN으로 잡혔다).
    def paired_surface(fg_key: str) -> str | None:
        m = re.match(r"(.+?)[_\-]?(?:ink|text|on)$", fg_key)
        return m.group(1).strip("_- ") if m else None

    pairs = []
    for fk, fv in foregrounds.items():
        owner = paired_surface(fk)
        if owner:
            for ok, ov in {**backgrounds, **foregrounds}.items():
                if ok.strip("_- ") == owner and len(ov) <= 7 and len(fv) <= 7:
                    pairs.append((f"{fk} on {ok}", fv, ov))
            continue
        for bk, bv in backgrounds.items():
            if len(fv) > 7 or len(bv) > 7:  # 알파 포함 값은 합성 결과를 알 수 없다
                continue
            pairs.append((f"{fk} on {bk}", fv, bv))
    return pairs


def main() -> int:
    ap = argparse.ArgumentParser(description="design-dna Phase 3 산출물 충실도 검사")
    ap.add_argument("dna", type=Path, help="Phase 2 산출 DNA JSON")
    ap.add_argument("output", type=Path, help="Phase 3 산출 HTML")
    ap.add_argument("--json-out", type=Path, help="결과를 JSON으로 저장")
    args = ap.parse_args()

    for path in (args.dna, args.output):
        if not path.is_file():
            print(f"입력 없음: {path}", file=sys.stderr)
            return 2

    dna = json.loads(args.dna.read_text(encoding="utf-8"))
    raw = args.output.read_text(encoding="utf-8", errors="replace")
    code = strip_comments(raw)

    findings: list[dict] = []

    # 1. 색상 추적성 — 산출물의 모든 색이 DNA 팔레트 안에 있어야 한다
    palette = hexes(json.dumps(dna, ensure_ascii=False))
    used = hexes(code)
    stray = sorted(used - palette)
    if stray:
        findings.append({
            "check": "color-traceability", "severity": "FAIL", "detail": stray,
            "hint": "DNA에 없는 색이다. 창작한 색이면 지우고, 원본에 있는데 추출에서 빠진 색이면 DNA를 보강한다(이중 테마 누락이 흔하다).",
        })

    # 2. elevation — DNA가 그림자를 쓰지 않으면 산출물도 쓰지 않는다
    shadow_used = len(re.findall(r"box-shadow\s*:", code))
    dna_blob = json.dumps(dna, ensure_ascii=False)
    dna_no_shadow = bool(re.search(r"box-shadow\s*(0회|없음|none)", dna_blob))
    if dna_no_shadow and shadow_used:
        findings.append({
            "check": "elevation", "severity": "FAIL",
            "detail": f"DNA는 그림자 미사용인데 산출물 box-shadow {shadow_used}회",
        })

    # 3. motion — philosophy가 none이면 전환·애니메이션 금지
    motion_none = bool(re.search(r'"(?:philosophy|transition|motion)"?[^,}]*(?:none|0회|없음)', dna_blob))
    motion_used = len(re.findall(r"transition\s*:", code)) + len(re.findall(r"@keyframes|animation\s*:", code))
    if motion_none and motion_used:
        findings.append({
            "check": "motion", "severity": "FAIL",
            "detail": f"DNA motion=none인데 산출물 transition/animation {motion_used}회",
        })

    # 4. visual_effects — enabled:false 카테고리가 산출물에 나타나면 위반
    effects = dna.get("visual_effects") or {}
    for key, pattern in EFFECT_EVIDENCE.items():
        spec = effects.get(key)
        if not isinstance(spec, dict) or spec.get("enabled") is not False:
            continue
        hits = len(re.findall(pattern, code, re.I))
        if hits:
            findings.append({
                "check": f"visual_effects.{key}", "severity": "FAIL",
                "detail": f"enabled:false인데 산출물에 {hits}건 검출",
            })

    # 5. WCAG 대비
    contrast_rows = []
    for label, fg, bg in collect_pairs(dna):
        ratio = contrast(fg, bg)
        verdict = "PASS" if ratio >= AA_BODY else ("LARGE-ONLY" if ratio >= AA_LARGE else "FAIL")
        contrast_rows.append({"pair": label, "fg": fg, "bg": bg, "ratio": round(ratio, 2), "verdict": verdict})
        if verdict == "FAIL" and fg in used and bg in used:
            findings.append({
                "check": "wcag-contrast", "severity": "WARN", "detail": f"{label} {ratio:.2f}:1 (<{AA_BODY})",
                "hint": "원본 사이트의 접근성 결함이 DNA를 통해 전파된 경우가 있다. 접근성이 DNA 충실도보다 우선한다 — 더 진한 토큰으로 올리고 이탈을 기록할 것.",
            })

    report = {
        "dna": str(args.dna),
        "output": str(args.output),
        "palette_size": len(palette),
        "colors_used": len(used),
        "findings": findings,
        "contrast": contrast_rows,
        "limitations_ko": "자동 판정 가능한 항목만 본다. mood·composition·타이포 위계 같은 정성 항목과 실제 렌더링 결과는 사람이 확인한다.",
        "verdict": "FAIL" if any(f["severity"] == "FAIL" for f in findings) else ("WARN" if findings else "PASS"),
    }

    print(f"verdict: {report['verdict']}  (팔레트 {len(palette)}종 / 사용 {len(used)}종)")
    for f in findings:
        print(f"  [{f['severity']}] {f['check']}: {f['detail']}")
        if f.get("hint"):
            print(f"          → {f['hint']}")
    if not findings:
        print("  위반 없음 — 자동 검사 항목 전부 통과")
    fails = [r for r in contrast_rows if r["verdict"] == "FAIL"]
    print(f"  대비 쌍 {len(contrast_rows)}개 중 AA 미달 {len(fails)}개")

    if args.json_out:
        args.json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  JSON: {args.json_out}")

    return 1 if report["verdict"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
