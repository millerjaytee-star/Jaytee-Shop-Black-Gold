# Stabilis Operations Control Room

## Product wedge

Stabilis is an intervention and proof layer for 3–25 location restaurant, cafe, and service retail groups. It is not a POS, payroll system, purchasing suite, or general ledger. Operators enter a consistent aggregate period and receive a ranked, explainable control queue across sales, labor, inventory, cash, guest experience, facilities, and execution.

The differentiated workflow is: **evidence → decision → owned action → observed result → independent verification**. A modeled target gap is never displayed as recovered or verified value. It cannot be annualized or double-counted with overtime, waste, refunds, or revenue findings.

This complements systems of record such as Toast, Restaurant365, and Crunchtime rather than claiming to replace them. The initial wedge is valuable when a growing multi-unit operator has figures spread across those systems but lacks a shared intervention record, staffing-floor guardrail, and auditable proof of what changed.

## What the local release does

- Captures up to 100 aggregate location periods through an accessible form or validated CSV.
- Diagnoses incomplete inputs without treating blanks as zero.
- Calculates operating contribution, labor/COGS target gaps, inventory reconciliation, cash risk, service, task, downtime, and data-quality signals.
- Ranks the next operating action and shows the formula/reason beside it.
- Tests a directional scenario without mutating the baseline and blocks a plan below the stated minimum service-hours floor.
- Locks an intervention with owner, due date, baseline method, and evidence note.
- Records a comparable-period labor or COGS observation only with source evidence. It remains `observed_unverified`.
- Exports CSV, a printable decision brief, and a portable local backup.

## Data handling and limitations

Calculations run in the browser. Persistence is local to the browser unless the operator downloads a backup. Do not enter employee, guest, payment-card, bank-account, or other sensitive identifiers. This release does not provide live POS/payroll/vendor sync, shared accounts, financial certification, automated purchasing, payroll, regulatory compliance, or independently verified savings.

## Path to a connected production product

1. Restore or provision the tenant-isolated Stabilis database before collecting real customer data.
2. Add consented read-only connectors for POS, payroll, accounting, inventory, and task systems; preserve source timestamp, account scope, and raw-to-derived lineage.
3. Add organization-level roles, encrypted storage, retention policy, audit logs, and review workflow before offering team accounts.
4. Promote observations to verified value only after an independent source review records attribution and reviewer evidence.
5. Keep the Control Room as the cross-system decision and proof surface; do not duplicate the systems of record.

## Release checks

- Node unit tests cover gap calculations, staffing-floor protection, evidence-gated observations, CSV validation, and CSV formula escaping.
- Static checks validate browser modules.
- Browser acceptance path: enter/import a location → review queue → run a scenario → assign an intervention → log an observed result → export report.
