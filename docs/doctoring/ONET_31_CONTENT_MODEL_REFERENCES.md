# O*NET 31.0 Content Model Reference evidence

This supporting note records the source governed by ADR 0250. It introduces
no architecture decision.

## Source and reproduction

- Official O*NET 31.0 JSON: `content_model_reference.json`
- Source SHA-256: `db59c30e4240931edce59310f2747f5476f058984b55f58f72c6f29faa30186f`
- Rows: 3,006
- Generated Turtle SHA-256: `d4f0e8bff1710dd360106c7325d4fb588951dbc28471f97ca71535749d8f3819`
- Parent contract: the O*NET data dictionary defines the period-delimited
  element identifier as the content-model hierarchy; generation removes only
  its final segment and fails when that parent is absent.

Reproduce with:

```bash
uv run python scripts/render_onet_31_content_model.py \
  docs/ontology/data/onet-31-content-model-reference.json \
  docs/ontology/onet-31-content-model.ttl
```

## APA 7 reference

National Center for O*NET Development. (2026). *O*NET 31.0 database: Content
model reference* [Data set]. https://www.onetcenter.org/dictionary/31.0/json/content_model_reference.html
