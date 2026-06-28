# Output Layout

```text
data/
  raw/
    project_amber/
    dimbreath_textmap/
  processed/
    project_amber_readable_v2/
    search_v2/
      project_amber_search.sqlite3
      audit_report.json
      evaluation_report.json
  canonical/
    project_amber_v2/
      items.jsonl
      localizations.jsonl
      documents.jsonl
      sections.jsonl
      text_units.jsonl
      relations.jsonl
      entity_names.jsonl
      textmap_entries.jsonl
      build_report.json
  logs/
```

`data/raw/project_amber` is treated as immutable source data. The builder writes generated outputs under `data/processed` and `data/canonical`.
