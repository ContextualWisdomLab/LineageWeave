# Unreleased — Dialog focus and evidence text remain readable

## Fixed

- Post and evidence dialogs now exclude collapsed, hidden, inert, transparent,
  and CSS-invisible controls from keyboard focus; related-post navigation keeps
  focus inside the active dialog, and evidence fields retain visible
  separators. OIDC login also preserves its validated deep-link return context.
