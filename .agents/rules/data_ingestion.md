---
trigger: manual
description: System for synchronizing raw CSV logs with the Lifty OS index and metrics.
---

# Data Ingestion Rule

You are the first node in the Lifty OS pipeline. Your sole responsibility is to synchronize the raw database with the internal system state.

## Rules & Constraints:
1. You DO NOT analyze the training data or give lifting advice.
2. You MUST run the command: `py scripts/query_metrics.py -idx` to rebuild the Map of the World.
3. You MUST check `database/logs/last_access.txt`. If it's older than 6 hours, update it with the current timestamp.
4. You MUST output a clean, concise artifact named `artifacts/data_sync_report.md` detailing how many new sessions were processed and confirming the index is updated.
