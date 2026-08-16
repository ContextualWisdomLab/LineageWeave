# Storybook inventory

Repeating web objects that must stay tokenized and independently
composable. The Storybook runner itself lands with the approved
frontend toolchain PR; this inventory is the product list those
stories must cover.

| Object | Tokens | Next action the story must teach |
|---|---|---|
| Analysis-run digest disclosure | `--lw-opacity-meta`, `--lw-font-size-meta`, `--lw-space-digest-gap`, `--lw-font-family-mono`, `--lw-focus-ring`, `--lw-focus-offset` | Activate a prefix, then match the revealed digest to the API payload. |
| Analysis-run live-post warning | `--lw-opacity-meta`, `--lw-font-size-meta` | Compare the opened body with the run cutoff before treating it as reconstructed evidence. |
| Meta caption (`.post-meta`) | `--lw-opacity-meta`, `--lw-font-size-meta` | Read the clock or count, then take the control beside it. |

## References

World Wide Web Consortium. (2024). *Web content accessibility guidelines
(WCAG) 2.2* (W3C Recommendation). https://www.w3.org/TR/WCAG22/

World Wide Web Consortium. (n.d.). *Disclosure (show/hide) pattern*.
ARIA Authoring Practices Guide.
https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/
