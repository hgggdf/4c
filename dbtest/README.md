# Vector DB Integration Tests

This folder contains real integration tests for MySQL + Chroma vector indexing.

Run from the project root:

```powershell
backend\.venv\Scripts\python.exe dbtest\run_vector_db_tests.py
backend\.venv\Scripts\python.exe dbtest\run_vector_agent_joint_tests.py
backend\.venv\Scripts\python.exe dbtest\rebuild_vector_store_from_mysql.py
backend\.venv\Scripts\python.exe dbtest\seed_synthetic_vector_data.py
```

The tests write rows marked with `[VECTOR_DB_TEST]`, sync them into the vector
store, verify hydration back to MySQL records, and then remove the test rows and
test vector chunks where possible. The OpenClaw input payload format is not
changed by these tests or by the vector fixes.

`run_vector_agent_joint_tests.py` additionally covers the service container,
retrieval API route, `agent.tools.retrieval_tools`, tool executor vector paths,
and `DialogueAgent._collect_evidence` without making an LLM network call.

`rebuild_vector_store_from_mysql.py` rebuilds Chroma and the local TF-IDF fallback
from the current MySQL hot/archive tables after the vector cache has been cleared.

`seed_synthetic_vector_data.py` fills empty vector categories with clearly marked
synthetic news/report rows for end-to-end testing.
