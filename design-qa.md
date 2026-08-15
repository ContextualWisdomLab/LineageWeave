# Design QA

## Comparison target

- Figma visual truth:
  - [Semantic-search workspace · MU-02 · node 162:27](https://www.figma.com/design/SBpgot7uTvMxEaxUwvoc0S?node-id=162%3A27)
  - [Document-detail workspace · MU-14 · node 164:27](https://www.figma.com/design/SBpgot7uTvMxEaxUwvoc0S?node-id=164%3A27)
- Reference and implementation captures remain in the operator-local artifact
  store; source data and image bytes are not committed.
- Direct Figma metadata, design context, and screenshots are available for both
  target nodes. MU-02 is 2000 x 1368 and MU-14 is 2000 x 1148; both use a thin
  blue top rule, a pale neutral canvas, white rounded work surfaces, blue
  selection states, and a compact card hierarchy.

## Evidence status

The target-frame comparison is accepted as a structural visual QA reference,
not as a pixel-identical fixture: the live React product must render authorized
PostgreSQL data and the product contract intentionally adds evidence, KG,
Keyman, report, and access-control surfaces. The managed-browser run verifies
functional behavior of the rebuilt React product: reader home, customer master,
administrator policy and Lineage review, direct-PostgreSQL semantic search,
document detail, Korean summary, event evidence, R&R, inferred/predicted
relatedness, reports, and access controls. Browser console and page-error
collections were empty. Axe scans of the home, customer, administrator, and
detail-dialog states reported zero violations and zero incomplete results after
the landmark and selected-text contrast fixes. The production login remains
fail closed because a production Keyverse issuer and relying-party client are
not configured in this runtime.

## Documented divergence

- The product continues below the source frame's first visible fold with
  Keyman management, semantic KG, issue/calendar work, report drilldown, chat,
  and access controls required by the product contract. These additions retain
  the same panel, rail, spacing, typography, and action-token system.
- MU-02 is a tabular VOC search/list reference, while the live workspace keeps
  the same canvas/card/selection language but exposes a two-column document
  list plus evidence-bound Event Lineage. This is an intentional information
  architecture difference, not a static screenshot substitution.
- MU-14 is a source-summary/action-thread reference, while the live detail
  dialog keeps the same compact white-card hierarchy and extends it with the
  required Korean summary, events, R&R, Keyman, semantic KG, chat, issue,
  calendar, and source drawer surfaces.
- Production HTTPS Keyverse configuration is an operator deployment gate and
  is not represented as completed by the loopback ceremony.

## General-user surface

The authenticated default is now the reader-facing `업무 홈`, which is not a
developer diagnostic dashboard. Its paired local capture is
`/tmp/lineageweave-reader-e2e-2/reader-home.png` at a 1,440 x 1,000 CSS viewport
(the full-page PNG is 1,440 x 1,126 pixels, device scale factor 1): it shows recent work,
evidence-backed customer accounts, reports, and the reader's effective scope.
The reader capture had no browser console or page errors, exposed no
administrator navigation, and exposed no operational KPI/event-queue strip.
The customer screen remains a separate navigation target and links back to
authorized evidence documents.

This home surface is an intentional product addition outside the two supplied
Figma frames. It is covered by the reader role-boundary acceptance, not by a
pixel-parity claim.

## Acceptance

The supplied Figma target URLs and the functional interaction flow remain
documented. A paired same-width comparison of MU-02 and the isolated reader
workspace confirms the shared blue accent, pale canvas, and white work-surface
language. It does not establish browser parity: MU-02 is a table/filter
dashboard while LineageWeave deliberately presents a document rail and
evidence-bound Event Lineage. Configured production HTTPS Keyverse, a real
business-account browser flow, a Figma frame aligned with the current product
information architecture, and independent review remain separate operational
release gates.

Figma comparison result: the target is readable and the shared visual tokens
are verified; functional and pixel parity are not accepted because the target
fixture and the current product have different information architectures.

## Amendment: General-user product surface and Figma target evidence (2026-08-14)

The general-user requirement is a first-class product surface in addition to
the operator console. A verified reader actor enters `#userHome` and can move
to `업무공간` and `고객 화면`; the reader does not receive the administrator
navigation, operational KPI/event-queue strip, Keyverse account editor,
Lineage override controls, or LLM enrichment controls. The customer screen is
an actor-scoped customer-master view, not a debug payload: customer accounts
and affiliate edges are shown only when normalized account-to-document evidence
survives the same server-side corp/PU authorization predicate. Customer nodes
and affiliate/document links remain bound to `schema:Organization`,
`schema:subOrganization`, and `schema:about` in the persisted ontology and
semantic layer.

The Figma comparison target is now verifiable rather than cover-only. The
operator recorded metadata/design context and rendered screenshots for MU-02
node `162:27` (2000 x 1368) and MU-14 node `164:27` (2000 x 1148). The live
React implementation reuses their blue accent, pale canvas, rounded white
surfaces, compact filter/navigation language, selected-state treatment, and
detail-card hierarchy while preserving live API data and evidence access. The
browser captures remain local QA artifacts; no source rows, inline images, or
credentials are committed.

This amendment supersedes the earlier “target frames unreadable” wording but
does not convert structural QA into pixel-parity or production-identity
acceptance. Production HTTPS Keyverse, a real business-account browser run,
and independent release review remain external gates.

## Amendment: Isolated reader comparison and no-result search state (2026-08-14)

The paired MU-02 comparison used the target's 2,000-pixel width and the same
effective reader capture width from a historical test-only local-IdP capture.
That capture is audit context only, not a Keyverse or release-acceptance path.
The reference was cropped only to the browser-visible fold; no Figma image,
source row, inline asset, or credential is committed. The live search state
started with no qualifying semantic vector result and then presented the
explicit keyword-fallback notice plus authorized document matches. This
confirms the empty-result UX is no longer a blank rail.

The comparison also makes the remaining acceptance limit concrete: matching
accent, canvas, panel, and selected-state treatment is not equivalent to a
table-dashboard implementation. The legacy reference branding is intentionally
not reintroduced, consistent with the current product naming. A revised target
frame for the Lineage information architecture is still required before visual
parity can be accepted.

## Fidelity surface check

- Fonts and typography: the implementation keeps the compact sans-serif
  hierarchy, uppercase blue eyebrow labels, strong Korean section headings, and
  readable metadata scale; no P0/P1/P2 typography issue was observed in the
  captured reader state.
- Spacing and layout rhythm: the reader capture preserves the pale canvas,
  rounded white work surfaces, four-card summary rhythm, three-column content
  grouping, and selected navigation treatment; the longer live content is an
  intentional scroll extension.
- Colors and visual tokens: the thin blue rule, blue actions/selection state,
  neutral canvas, white cards, and muted metadata tokens are shared with the
  readable MU-02/MU-14 references; contrast was checked by the browser axe run.
- Image quality and asset fidelity: the compared business-home state has no
  decorative image asset; evidence images remain authorized document assets and
  are not replaced with CSS drawings or placeholders.
- Copy and content: the default labels describe business work, customer
  relationships, reports, and effective scope; operational rows, KG counts,
  queue counters, and administrator controls are intentionally absent for the
  reader role.

## Evidence paths

- Source visual truth: the MU-02 and MU-14 Figma node URLs listed above; source
  screenshots are retained in the operator-local artifact store and are not
  committed with source data.
- Implementation screenshot:
  `/tmp/lineageweave-reader-e2e-2/reader-home.png` (full-page PNG 1,440 x
  1,126; CSS viewport 1,440 x 1,000; device scale factor 1).
- Primary interactions tested: reader home navigation, customer screen,
  evidence-linked document selection, administrator visibility/Lineage review
  boundary, and no-result semantic-search fallback.
- Console/page errors: none in the recorded browser run.

## Final result

Structural design QA passes with no actionable P0/P1/P2 finding. Pixel parity,
production Keyverse, a revised Lineage-specific target frame, and independent
release review remain explicit external gates.

final result: partial — structural QA passed; release-level product/Figma parity
is blocked until a matching target frame and paired production browser evidence
exist.

## Amendment: refreshed Figma target status (2026-08-15)

The supplied MU-02 and MU-14 nodes were re-read directly from the current
Figma file. They remain usable structural references for semantic-search and
detail-card hierarchy, but retain legacy-brand marker text and do not describe
the current email-first, `글 자체의 Lineage` information architecture. No Figma
file was changed. The public product source scan remains clear of that legacy
brand.

Accordingly, the only accepted result is structural alignment of visual
language. A product-aligned Figma target plus a paired browser capture is still
required for release-level parity. Historical isolated-identity captures do
not count as production Keyverse or visual release acceptance.

## Amendment: current Figma-source availability and email-gate capture (2026-08-15)

### Comparison target

- Source visual truth: the supplied Figma design file currently exposes only
  its `00 Cover` page and a single 1,920 x 1,080 cover frame. The previously
  recorded workspace/detail node references are historical evidence, not
  currently readable target frames in this file.
- Implementation capture:
  `/Users/seonghobae/.codex/visualizations/2026/08/13/019ff930-ba40-7f53-9286-604c732345e2/lineageweave-login-gate-2026-08-15.png`
  (1,280 x 720 CSS viewport, device scale factor 1).
- State: the Figma artifact is a design-document cover; the implementation is
  the unauthenticated, email-first product gate. These are different screens,
  so a visual-parity judgment would be false precision.

### Evidence

The source and implementation were captured and placed side by side for this
review. The source image was used only in an ephemeral local comparison and
was not retained in this repository because it contains legacy private
reference content. The product capture contains no real account or source
data. Browser interaction verified the visible empty-email, malformed-email,
and unconfigured valid-email states; the final state is captured separately at
`/Users/seonghobae/.codex/visualizations/2026/08/13/019ff930-ba40-7f53-9286-604c732345e2/lineageweave-login-unavailable-2026-08-15.png`.

### Findings

- [P0] No product-aligned Figma frame is currently available.
  Location: supplied Figma file versus the unauthenticated LineageWeave gate.
  Evidence: the live Figma metadata contains a cover only, while the rendered
  product is an email-first authentication screen.
  Impact: typography, spacing, color, imagery, copy, and interaction parity
  cannot be assessed against the required product state.
  Fix: provide or select a Figma frame for the current email gate and, after
  real Keyverse is configured, the authenticated workspace/document-detail
  state; recapture both at the same viewport and rerun the comparison.

### Final result

final result: blocked

## Amendment: current Figma-page reinspection (2026-08-15)

The earlier cover-only conclusion is superseded. A fresh read-only page
inventory showed the supplied Figma file has current wireframe, mockup, and
prototype pages in addition to the cover. The target event-intelligence frame
describes a question-led flow from an evidence-sourced answer into a causal
timeline and follow-up watchlist. Its private source content remains outside
this repository.

This corrects source availability, not the acceptance result. There is still
no user-chosen-browser capture of the current LineageWeave event surface at
the same authentication and data state, so visual or interaction parity cannot
be claimed. Historical isolated-identity captures and structure-only Figma
inspection remain non-acceptance evidence.

## Amendment: latest Figma connector recheck (2026-08-15)

The most recent connector read exposed only the supplied design file's cover
page. This contradicts the earlier target-frame inventory, which therefore
cannot be used as current visual truth. No Figma artifact was changed and no
parity assertion is retained from the conflicting observations.

The current behavioral correction keeps shared-thread documents out of the
chronological event presentation and labels them as separate relatedness. A
browser-rendered capture at the same authenticated document-detail state and
a reproducibly readable Figma target are both still required before visual QA
can proceed.

final result: blocked

## Amendment: reader-role implementation capture in Figma (2026-08-15)

The current React product was captured into the supplied Figma file while the
server used a reader-only actor. The resulting implementation frame is
[LineageWeave reader home · node 304:2](https://www.figma.com/design/SBpgot7uTvMxEaxUwvoc0S?node-id=304%3A2).
Its metadata contains `업무 홈`, `업무공간`, `고객 화면`, and `내 업무공간`,
with the permission label `열람`; it contains no `관리자 모드` navigation or
diagnostic operator KPI. The frame also includes the evidence-backed customer
master and report entry points requested by the product brief.

This closes the earlier availability finding that no product-aligned Figma
frame existed and gives future visual QA a reproducible implementation
baseline. It is a reverse capture of the running product, not an independent
design target, so it does not by itself prove pixel parity or production
Keyverse acceptance. The separate production identity and independent design
review gates remain open.

Evidence: Figma metadata and screenshot for node `304:2`, the reader-only
direct-PostgreSQL server run, and the browser data-bearing acceptance that
confirmed administrator controls were absent from the reader surface.
