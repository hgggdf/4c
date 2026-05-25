# Dedup SQL Tests

This folder contains the migration and verification scripts for the dedup-key
change.

Run from the project root:

```powershell
backend\.venv\Scripts\python.exe sqltest\run_dedup_tests.py
backend\.venv\Scripts\python.exe sqltest\run_db_integration_tests.py
backend\.venv\Scripts\python.exe sqltest\migrate_dedup_columns.py
```

`run_dedup_tests.py` does not write to the database.

`run_db_integration_tests.py` writes test-only rows to the real database, reads
them back, verifies dedup updates, then removes rows whose title starts with
`[DEDUP_TEST_OPENCLAW]` or whose `report_type` starts with `dedup_test`.

`migrate_dedup_columns.py` writes the following nullable columns, backfills
existing rows, and creates indexes when duplicate keys are not present:

- `dedup_key`
- `content_hash`
