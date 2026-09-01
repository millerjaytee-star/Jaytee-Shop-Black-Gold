# Data & Connections

Controlled-pilot ingestion supports customer-provided CSV/XLSX templates through the existing upload, mapping, validation, normalization and analysis architecture. Future POS, payroll, scheduling, inventory, purchasing and accounting integrations must use the same tenant-bound data-source and ingestion contracts.

Pipeline:
`UPLOAD → DETECT → MAP → VALIDATE → NORMALIZE → RECONCILE → STORE → CALCULATE → REVIEW → PUBLISH`

Each connection should retain provider/source, organization, status, freshness SLA, last successful sync, ingestion job state, validation errors and safe processing logs. Bad or stale data is never silently presented as current.
