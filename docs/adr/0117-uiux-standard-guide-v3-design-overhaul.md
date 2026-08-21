# ADR 0117: UI·UX Standard Guide Ver.3.0 Design Overhaul

**Status:** Accepted
**Date:** 2026-08-21
**Figma:** File ID `1Su3lDRmiZdcUs47t1QwIX`

**Context:** LineageWeave's frontend was built from textual specifications with basic design tokens (ADR 0099), responsive breakpoints, and a buyer GNB (ADR 0037). A comprehensive Korean corporate UI·UX Standard Guide Ver.3.0 requires systematic alignment of layout, typography, colors, navigation, page types, and component patterns.

**Decision:**
1. Container max-width is widened to 1920px for the outer shell, while the content area uses 1280px recommended width. The 1024px minimum is the responsive fold point.
2. Responsive CSS breakpoints are consolidated to three standard tiers: PC (≥1024px), Tablet (768px–1024px), Phone (<768px). The prior 640px breakpoint is eliminated.
3. Noto Sans KR web font is loaded from Google Fonts CDN with latin and korean-ext subsets, maintaining system fallbacks per the existing `--sans` stack.
4. Header layout separates into: Logo area (left) containing CI/BI logo + system name, and Top menu area (right) containing user profile badge, logout button, language switcher, and optional search/utilities. Header remains sticky.
5. Footer layout separates into: Logo area (left) containing brand identity, and Copyright area (right) following the pattern `Copyright © {year} {BRAND}. All rights reserved.` with gothic-style lowercase English and gray color.
6. Mobile (phone) layout uses a drawer menu (hamburger button) instead of the full GNB bar, matching the guide's phone layout specifications.
7. Table content alignment follows the standard: left for text (titles, content, notes), right for numbers (amounts, quantities, totals), center for code-type data (IDs, names, dates, lot numbers).
8. Required form fields are marked with a bold `*` prefix on the label.
9. Button naming follows the standard Korean UI vocabulary (§4.3.2) and ordering follows: ① Screen inquiry → ② Content input → ③ Content save → ④ Content modify → ⑤ Screen output → ⑥ Screen navigation.
10. Modal popup backdrops use exactly 50% opacity (already compliant).
11. All new design tokens include both light and dark mode values (per ADR 0099).

**Consequences:**
- Frontend CSS is refactored to use three-tier responsive breakpoints consistently.
- Noto Sans KR web font dependency is added to `index.html`.
- Header and footer components gain new DOM structure matching the guide.
- Mobile users see a hamburger-triggered drawer for navigation.
- Table and form utilities adopt standard alignment rules.
- All changes are covered by existing and new Vitest tests.

**References:**
- 웹 시스템 UI·UX 표준 가이드 Ver.3.0
- ADR 0002 (Figma boundary)
- ADR 0037 (Buyer GNB surface)
- ADR 0099 (Design tokens)
- W3C WCAG 2.2 AA
- Google Fonts: Noto Sans KR
