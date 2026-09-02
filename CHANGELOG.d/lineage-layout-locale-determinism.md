### Fixed

- Made Lineage DAG reconstruct-group ordering independent of browser/runtime locale so the same graph renders the same branch-figure order across environments, while keeping ungrouped figures last and preserving raw group identity as the deterministic tie-breaker.
- Fail closed when a visible lineage edge points a post to itself instead of rendering an impossible predecessor relationship as a zero-length interactive edge.
