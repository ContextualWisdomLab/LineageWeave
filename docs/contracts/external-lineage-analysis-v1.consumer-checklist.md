# External lineage analysis v1 consumer checklist

- Validate the published JSON Schema before sending or accepting payloads.
- Submit only evidence the calling principal is authorized to disclose for the declared purpose.
- Use opaque caller-owned references; never send provider credentials or database locators.
- Bind historical work to a knowledge cutoff and preserve each record's availability time.
- Keep RFC/provider thread observations separate from inferred semantic/project lineage.
- Treat project projections as proposals until the caller's own policy or reviewer accepts them.
- Preserve the returned artifact digest, LineageWeave version, limitations, and channel evidence.
- Fail closed on incompatible contract versions.
- Keep normal caller operation available when LineageWeave is unavailable.
