# Sidra ERP — Decisions and Gates v0.1

7 Nov 2026 · decisions by Mohamoud Abdullahi Sheikh, recorded by Claude Code. This is the `DECISIONS-AND-GATES.md` that `docs/CLAUDE-CODE-HANDOFF_v2.0.md` lists as an input. Where it conflicts with `docs/SREMS-SRS_v2.0-DRAFT.md`, `docs/SREMS-SRS_v1.6.md` or `docs/HANDOVER_v1.0.md`, this document wins. A new decision gets a new version of this file.

## 1. Decisions

| ID | Date | Decision | Replaces / resolves |
| --- | --- | --- | --- |
| D1–D8 | 6 Nov 2026 | Contract capture decisions: down payment per contract, fees inside the price, $5.00 schedule tolerance, 20-day title deadline in Contract B, record only the signing data a contract has, structured penalty / default / title fields, Sales Manager confirmation as INS-19 approval, schedule only for live contracts | Issue #13; `docs/CONTRACT-CAPTURE_v0.3.md` |
| G1 | 7 Nov 2026 | **Installment terms are configurable**: any number of monthly installments, including 12, 24, 36 and every value in between. Schedules are generated from the terms or entered as the contract states them. The payment dates printed in the Contract B specimen are not a requirement. | Closes the "Contract B payment dates do not fit 24 months" open item (handover v1.0 §9) |
| G2 | 7 Nov 2026 | **Penalties are configurable** by two values: a **time period** before a penalty takes effect, and an **amount**. Each profile and each registered contract carries its own values. The existing profile fields cover this (`notice_days` or grace days, `penalty_per_day` / `penalty_fixed_amount`, optional `penalty_monthly_cap`). | Sets the penalty model for later phases; until penalties are switched on, penalty values are stored, not applied (`CLAUDE.md` rule 3) |
| G3 | 7 Nov 2026 | **No Murabaha.** No profit markup and no Murabaha formula; contracts are priced at the agreed price. `markup_rate` stays 0. | SRS v2.0 §9 item 3; acceptance case AT-05 is dropped |
| G4 | 7 Nov 2026 | **ERPNext is the only accounting ledger.** No second ledger or parallel accounting tables. | SRS v2.0 §9 item 4; handover v1.0 §9 "whether ERPNext is the main ledger" |
| G5 | 7 Nov 2026 | **Live-contract migration happens later.** The system needs an **import capability** (contracts, schedules and later payments from Excel / CSV); the migration itself is not done now. | SRS v2.0 §9 item 8 (timing); D8 |
| G6 | 7 Nov 2026 | **Merge rule:** a PR into `develop` is merged when its CI is green. No separate review wait. | `CLAUDE.md` rule 5 (CI must pass) unchanged |
| G7 | 7 Nov 2026 | **Implementers:** Claude Code implements. When Claude Code's usage limit is reached, **Codex continues the same work** under the same rules (`AGENTS.md`). | Contract capture brief roles (`CONTRACT-CAPTURE_v0.3.md`) |
| G8 | 7 Nov 2026 | `sidra-erp_v0.1.0.zip` was committed by mistake and is removed. | — |

## 2. Gates still open

These are not decided by an implementer. Open a `spec-question` issue when work reaches them.

| Gate | Blocks |
| --- | --- |
| Buyer late penalties: Sidra income or charity; legal / Sharia enforceability (SRS v2.0 §9 item 2) | Applying and posting penalties |
| Finance posting matrix and controls (handover v1.0 §5, Phase 5) | Posting vouchers, refunds |
| Unsigned draft locking a plot (SRS v2.0 §9 item 6) | Changes to reservation rules |
