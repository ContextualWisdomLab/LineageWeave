### Fixed

- Made Lineage DAG reconstruct-group ordering independent of browser/runtime locale so the same graph renders the same branch-figure order across environments, while keeping ungrouped figures last and preserving raw group identity as the deterministic tie-breaker.
- Fail closed when two visible lineage rows claim the same canonical node id instead of letting transport order choose group, label, event-time, or edge identity through last-write-wins map materialization.
- Fail closed when a visible lineage edge points a post to itself instead of rendering an impossible predecessor relationship as a zero-length interactive edge.
- Fail closed when visible same-group predecessor edges form a directed cycle instead of flattening the unrooted cycle into plausible disconnected DAG rows.
