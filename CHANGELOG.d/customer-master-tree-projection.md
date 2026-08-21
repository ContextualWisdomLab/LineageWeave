### Fixed

- Customer master now preserves authorized Group → Company → Plant hierarchy while promoting
  missing-parent, self-parent, and cyclic relations to visible `unresolved` roots instead of silently
  dropping those customers.

### Accessibility

- Added a reusable WAI-ARIA customer tree with roving focus, branch expansion, Arrow/Home/End keyboard
  navigation, exact level/position metadata, and independently loaded source-post evidence.
