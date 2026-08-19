# Tied organization names do not create catalog rows

A tied top organization similarity score now stays unbound. Even with live
name resolution, hierarchy inference, and verification, the ingestion path
does not insert an `AUTO-` catalog row. Only a genuine below-threshold miss
may enter the corroborated creation path (ADR 0026).
