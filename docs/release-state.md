# Release State

The authoritative real-financial-data release decision is maintained in [`security-release-gate.md`](security-release-gate.md). The current decision permits controlled pilots only in the dedicated Stabilis environment and under the controls documented there.

All new work must use a feature branch and pass CI, deploy-preview review, applicable Supabase security review, and production smoke gates before release. Repository migrations are not currently sufficient to reproduce a fresh Supabase environment; see [`database-migration-ledger.md`](database-migration-ledger.md) for the separately reviewed remediation requirement.
