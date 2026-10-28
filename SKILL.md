---
name: design-dna
description: >-
  외부 참조 디자인(이미지·스크린샷·URL)을 3차원 구조화 JSON으로 추출하고 그 JSON으로
  디자인을 생성한다 — design system(측정 가능한 토큰), design style(정성적 인상),
  visual effects(Canvas·WebGL·3D·파티클·셰이더·스크롤 효과). 대상은 **남의 사이트·레퍼런스**다.
  자기 프로젝트의 반복 패턴을 디자인 시스템으로 승격하는 것은 /impeccable extract, 새 UI를
  처음부터 만드는 것은 /frontend-design이 맡는다. Triggers on "design DNA", "디자인 DNA",
  "참조 디자인 추출", "레퍼런스 사이트 분석", "이 사이트 스타일로", "design tokens from
  reference", "design system from screenshot", "generate design from JSON".
metadata:
  author: zanwei (upstream) + 로컬 트리거 조정·충실도 검사기
  version: 1.2.0
  category: design
license: MIT — zanwei/design-dna. 원문 허가문은 LICENSE.upstream 참조.
---

<!--
upstream: https://github.com/zanwei/design-dna @ 593e39bc9e3652734653bd75544a333d7d43615e
도입: 2026-08-16, audit AUD-20260812-113216-a988e657 (install-candidate)
재동기화: 2026-10-16, 9d9d7956 → 593e39bc (결정적 색 측정 measure-colors·verify·color-math·테스트, schema 선택 필드 2종)

**로컬 분기 — frontmatter description 교체와 「(로컬 추가)」로 표시한 줄·절만 다르다.** 그 밖의
"# Design DNA" 이하 본문과 references/ 2종, scripts/의 .mjs·package.json·test/는 upstream 원문
그대로이며, 향후 diff·재동기화를 위해 손대지 않는다.

분기 사유: upstream description의 트리거 11개 중 "analyze design", "design profile",
"visual effects analysis", "style guide JSON" 등이 지나치게 일반적이라, 이미 15개가 있는
디자인 스위트(frontend-design 앞문 · impeccable 엔진 · critique · design-review 등)와
원치 않는 발화 경합을 일으킨다. CLAUDE.md의 트리거 위험 기준을 적용해 **“외부 참조 대상”
이라는 이 스킬의 고유 책임이 드러나는 표현으로 좁히고**, 형제 스킬과의 경계를 명시했다.
한국어 트리거도 함께 넣었다(사용자 기본 언어).
-->

# Design DNA

A 3-phase workflow for extracting, structuring, and applying design identity across three dimensions:

1. **Design System** — measurable tokens (color, typography, spacing, layout, shape, elevation, motion, components)
2. **Design Style** — qualitative perception (mood, visual language, composition, imagery, interaction feel, brand voice)
3. **Visual Effects** — special rendering (Canvas, WebGL, 3D, particles, shaders, scroll effects, cursor effects, SVG animations, glassmorphism, etc.)

## Phases

### Phase 1: Structure — Output the Schema

When the user asks for the structural dimensions or schema:

1. Read [references/schema.md](references/schema.md)
2. Present the full schema with field descriptions
3. Explain the three dimensions and their roles:
   - **design_system**: What you can measure — exact hex values, pixel sizes, rem scales
   - **design_style**: What you can feel — mood, personality, composition strategy
   - **visual_effects**: What you can see but can't express in CSS alone — WebGL scenes, particle systems, shader distortions, scroll-driven animations
4. Ask if the user wants to customize or extend any dimensions

### Phase 2: Analyze — Extract DNA from References

When the user provides images, screenshots, or links representing a target design style:

1. Read [references/schema.md](references/schema.md) for the full field list
2. For each reference provided:
   - If image/screenshot: **first run the deterministic color measurement** (see below), then analyze the remaining visual properties directly
   - If URL: fetch and analyze the page's visual design
3. For every field in the schema, extract or infer a value from the references
4. When multiple references conflict, note the dominant pattern and mention variants
5. Output a complete Design DNA JSON — every field populated, no empty strings
6. After output, ask: "Want to adjust any values before using this for generation?"

**Analysis approach per dimension:**

#### Dimension 1: design_system
- **color**: Do not estimate hex values by eye — perceived colors drift toward familiar palette defaults (often by a ΔE of 10+). When the reference is an image file, measure instead. Resolve `SKILL_ROOT` to the absolute directory containing this `SKILL.md`; never assume the current project directory contains the skill's `scripts/` folder. Use absolute paths for the reference and output, and keep one uniquely named measurement file per reference:
  ```bash
  npm install --prefix "$SKILL_ROOT/scripts" --silent
  node "$SKILL_ROOT/scripts/measure-colors.mjs" "$REFERENCE_IMAGE" > "$MEASUREMENT_JSON"
  ```
  Use the measured hexes verbatim in the DNA JSON: map the `background` role to `surface.background`; map `text` to the end of `neutral.scale` that contrasts with the measured background and document that foreground use in `neutral.usage`; and map `accent` to `accent.hex`. Keep both the measured palette and its `measurement` configuration in `design_system.color.measured_palette` and `design_system.color.measurement` so verification can reuse the same clustering configuration. Coverage values are fractions from `0` to `1`. Only fall back to visual sampling when measurement is impossible (for example, a URL-only reference that cannot be screenshotted). Choose primary and secondary colors by semantic role, use accent for CTA emphasis, and order the neutral scale from lightest to darkest regardless of theme.
  - **(로컬 추가)** `npm install`은 `sharp`(네이티브 바이너리)를 내려받아 스킬 폴더(이 저장소 안, junction)의 `scripts/node_modules/`에 설치한다. `scripts/node_modules/`가 아직 없으면 설치 전에 사용자에게 묻고, 거절되면 위의 visual sampling 대체 경로로 가되 산출 JSON에 《측정 아님》을 밝힌다.
- **typography**: Identify font families by visual characteristics (geometric, humanist, serif class). Estimate scale ratios from heading/body size relationships.
- **spacing**: Assess density by element proximity. Measure rhythm by section gap consistency.
- **layout**: Identify grid by content alignment patterns. Note max-width, column count, asymmetry.
- **shape**: Measure border-radius by comparing to element height. Note border and divider presence.
- **elevation**: Classify shadow softness, spread, and layering approach.
- **motion**: If observable (video/interactive), note easing curves and duration feel.

#### Dimension 2: design_style
- Synthesize holistic impressions — mood, personality, composition strategy
- Compare against genre archetypes (SaaS, editorial, brutalist, etc.)
- Note ornamentation level and whitespace philosophy

#### Dimension 3: visual_effects
- **From code**: Scan for `<canvas>`, WebGL contexts, Three.js/Pixi.js imports, GSAP/Lottie usage, custom shaders, IntersectionObserver scroll triggers, SVG `<animate>` elements
- **From screenshots**: Describe visible effects that go beyond standard CSS — glowing particles, 3D object renders, noise textures, gradient animations, parallax depth, cursor trails, text distortions, glassmorphic surfaces. Note these in `composite_notes` when exact implementation can't be determined.
- **From video/interaction demos**: Note scroll behaviors, hover distortions, transition choreography, loading sequences
- Set `enabled: false` for any effect category not present in the reference
- Rate `overview.effect_intensity` and `overview.performance_tier` based on what's observed

### Phase 3: Generate — Apply DNA to Content

When the user provides DNA JSON + content to design:

1. Read [references/generation-guide.md](references/generation-guide.md)
2. Parse the DNA JSON and extract all tokens across three dimensions
3. Build CSS custom properties from `design_system` values
4. Apply `design_style` qualitative fields to guide subjective design decisions
5. When the design needs assets or source materials, fetch them from the original source whenever possible. If the user provided a URL, retrieve the real asset from that URL instead of recreating, approximating, or substituting it.
6. Implement `visual_effects` using appropriate technologies:
   - Lightweight effects → CSS animations, SVG, vanilla JS
   - Medium effects → Canvas 2D, GSAP, Lottie
   - Heavy effects → Three.js, custom GLSL shaders, Pixi.js
7. Generate the design output (default: self-contained HTML with inline CSS/JS)
8. Run quality checks from the generation guide
9. **Verify (when the DNA contains a measured palette)**: save the current Design DNA JSON if it is not already a file, screenshot the generated output, then score it against that DNA file. Resolve `SKILL_ROOT` from this `SKILL.md` and use absolute paths; do not assume a temporary file named `measured-colors.json` exists:
   ```bash
   node "$SKILL_ROOT/scripts/verify.mjs" "$IMPLEMENTATION_SCREENSHOT" "$DESIGN_DNA_JSON"
   ```
   A standalone measurement JSON may be used instead of the DNA file when that is the only persisted artifact. For multiple image references, verify against each reference's measurement separately. The report gives per-color ΔE and coverage drift with PASS/FAIL thresholds. If it fails, fix the offending colors and re-verify instead of asking the user to judge fidelity by eye.
10. **(로컬 추가) 기계 검사를 돌린다** — `py scripts/check_dna_fidelity.py <dna.json> <output.html>`. 색상 추적성·elevation·motion·visual_effects 준수·WCAG 대비를 자동 판정한다. 상세는 아래 「충실도 검사기」 절.

**If the user provides only content without DNA JSON**, ask whether to:
- Analyze a reference first (go to Phase 2)
- Use a described style (extract DNA from description, then generate)

## Phase Combinations

Users may invoke any combination:
- **Phase 1 only**: "Show me the design structure/schema"
- **Phase 2 only**: "Analyze this design" (with images/links)
- **Phase 2 → 3**: "Analyze this design and build me a landing page in the same style"
- **Phase 1 → 2 → 3**: Full pipeline
- **Phase 3 only**: User already has DNA JSON

Detect which phase(s) are needed from context and execute accordingly.

---

## 충실도 검사기 (로컬 추가 — upstream에 없음)

```bash
py scripts/check_dna_fidelity.py <dna.json> <output.html> [--json-out FILE]
```

종료 코드: `0` 위반 없음 · `1` 위반 있음 · `2` 입력 오류.

generation-guide의 Quality Checks 중 **자동 판정 가능한 것만** 본다 — 색상 추적성(산출물의 모든 색이 DNA 팔레트 안인가), elevation·motion 준수(DNA가 그림자·전환을 안 쓰면 산출물도 안 쓰는가), `visual_effects`의 `enabled:false` 카테고리가 실제로 비어 있는가, WCAG AA 대비. **mood·composition·타이포 위계 같은 정성 항목과 실제 렌더링은 사람이 본다** — PASS는 「DNA를 배신하지 않았다」이지 「좋은 디자인이다」가 아니다.

설계상 주의 3가지(전부 2026-08-16 실측으로 잡은 오탐):

- **주석을 지우고 검사한다.** 「이 효과를 쓰지 않는다」고 설명한 주석의 단어가 「그 효과를 썼다」는 증거로 잡혔다.
- **`*_ink`/`on-*` 계열은 짝 배경하고만 대비를 잰다.** `accent_ink`는 accent 버튼 위 글자이므로 ground·card와 조합하면 존재하지 않는 쌍이 만들어진다.
- **알파 포함 색(`#RRGGBBAA`)은 대비 계산에서 뺀다.** 합성 결과를 알 수 없다.

**색상 추적성 위반은 산출물이 아니라 DNA의 결함일 때가 많다.** Phase 3 시연에서 다크 색 8종이 「DNA 밖」으로 잡혔는데, 원인은 Phase 2가 이중 테마 중 라이트 값만 필드로 적고 다크는 산문으로만 언급한 것이었다. 위반이 뜨면 **산출물을 고치기 전에 DNA가 완전한지 먼저 본다.**

**접근성이 DNA 충실도보다 우선한다.** 원본 사이트의 대비 결함이 DNA를 통해 전파될 수 있다(실측: `--ink-3` on ground 2.93:1). 이때는 더 진한 토큰으로 올리고 그 이탈을 산출물 주석과 DNA의 `accessibility_note`에 함께 기록한다.

## 이 저장소에서의 위치 (로컬 추가)

디자인 스위트에서 이 스킬의 자리는 **외부 참조 → 구조화 JSON** 한 방향이다.

| 요청 | 담당 |
|---|---|
| 「이 사이트처럼 만들어줘」(외부 레퍼런스 제시) | **design-dna** Phase 2 → 3 |
| 「우리 프로젝트 패턴을 디자인 시스템으로」 | `/impeccable extract` (자기 프로젝트 대상) |
| 「새 UI를 만들어줘」(레퍼런스 없음) | `/frontend-design` (앞문) |
| 프로젝트 디자인 컨텍스트 수집 | `/impeccable teach` → `.impeccable.md` |
| 작성 후 개선·평가 | `/impeccable animate` → `/impeccable polish` → `/impeccable critique` → `/design-review` |

`.impeccable.md`의 **Recent Fingerprints**(최근 5건 레이아웃·타입 페어링·팔레트)는 이 스킬에도 적용된다 — 외부 참조를 따라가더라도 같은 프로젝트에서 연속 산출물이 한 형태로 수렴하지 않도록, 생성(Phase 3) 전에 회전을 선언한다.
