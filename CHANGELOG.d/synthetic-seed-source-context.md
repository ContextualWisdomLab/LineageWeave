# Synthetic seed cleanup source context

- Require every `source_*` field, including lifecycle markers, system and record
  identity, order metadata, and inspection metadata, to be empty before a
  Demo-scoped post can be considered synthetic cleanup material.
- Preserve imported rows that carry metadata without author or customer names.
