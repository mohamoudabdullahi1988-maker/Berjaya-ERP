# Sidra ERP — Contract Capture: Reuse Assessment and Implementation Brief v0.2

6 Nov 2026 · prepared by Claude (analysis and review) for Codex (implementation), under the Sidra Handover of 6 Nov 2026. Decisions: issue #13.

**v0.2:** D1–D4 decided by Mohamoud (issue #13); sections 5–7 updated. v0.1 used interim rules for them.

**Confirmed direction (handover):** the main purpose is to **register contracts prepared outside the system** and capture their variables, individual terms and installment schedules. Generating a contract is an optional extra and must not be a prerequisite for registration.

**Roles (handover):** Codex implements code and runs the tests. Claude analyses requirements and reviews diffs, tests and demonstrations. Mohamoud / Sidra management approve.

## 1. Baseline

| Item | Value |
| --- | --- |
| Sidra platform | Frappe v16.55.2, ERPNext v16.53.0, Python 3.14 (`docs/ENVIRONMENT_v0.1.md`). There is no staging or production site yet, so these are the versions used in development and CI. |
| Sidra code reviewed | `develop` @ `cbce4f3`, plus open PR #12 (`feature/sal-review-fixes` @ `97b3fbd`; CI passed: lint, pure tests, full bench install and 119 integration tests). **This brief assumes PR #12 is merged first.** |
| Candidates reviewed | PropMS `version-16-hotfix` @ `63eed74` (30 Oct 2026); LMS `main` @ `f5f615f` (1 Apr 2026); Real Estate ERPNext App `master` @ `1c31c0c` (25 Nov 2023); BuildSuite Core `develop` @ `def93cc` (5 Nov 2026); ERPNext v16.53.0 payment terms and schedule code |
| Method | Read the source code, DocType metadata, tests and git history. **Nothing was installed or run**, so installability and runtime behaviour are not verified. No claims rest on READMEs alone. |

## 2. Reuse assessment

Order of preference (handover): standard ERPNext, then an existing Frappe app, then custom code for what is left.

### 2.1 Standard ERPNext: payment terms and Payment Schedule

| Aspect | Finding (ERPNext v16.53.0 source) |
| --- | --- |
| Where it lives | A `Payment Schedule` child table on transactions (Quotation, Sales Order, Sales Invoice, and the purchase side). A transaction needs a Customer, Company and item lines (an Item per plot or unit). |
| Rows | `due_date`, `payment_amount`, `invoice_portion`, `description`, `mode_of_payment`, discounts, and paid and outstanding amounts. Rows can be edited on the transaction. |
| Templates | `Payment Terms Template` rows set a percentage and a due-date rule: days after the invoice date, or days or months after the end of the invoice month. There is **no rule for "day N of each month after M months' grace"** (INS-14), so Sidra's terms can't be modelled as a template. |
| Validation | `validate_payment_schedule_amount`: the schedule must equal the grand (rounded) total. `validate_payment_schedule_dates`: on a Sales Order or Quotation, no due date before the transaction date, and **no two rows on the same due date**, which rejects a down payment and a first installment due on the signing day. |
| Payments | A Payment Entry can be allocated per payment term (`allocate_payment_based_on_payment_terms`). |
| Contract data | None: no external reference, parties, notary, original document or contract-specific terms. |

**Verdict: adapt later, not now.** The ERPNext Payment Schedule is the right place for receivables once Finance approves the posting and billing policy (SRS v2.0 §3.4, P2). It can't be the registration record: it needs sales documents and items, has no contract data, and refuses some real schedules (same-day rows). In P2, copy a confirmed Sidra schedule into a Sales Order or Invoice Payment Schedule, and resolve same-day rows then, for example by merging them or separate documents.

### 2.2 Candidate apps

| Candidate | Licence, version, maintenance, tests | Coverage of contract capture | Problems | Recommendation |
| --- | --- | --- | --- | --- |
| **LMS** (LISACORNEL/lms) | Licence: MIT template text never filled in ("[year] [fullname]"). Targets **v15** (`frappe~=15.0.0` commented out). 21 commits, last on 1 Apr 2026. **9 test files with no test functions.** | Has `Plot Contract` with a schedule child (`Plot Contract Payment`). | `generate_payment_schedule()` **rebuilds the schedule on every save of a draft** from booking fee % and a payment window (two rows), overwriting entered rows (fails check 3). The exception is a contract created from a Sales Order, which copies the order's Payment Schedule. Built-in rules that conflict with Sidra: default 60% booking fee, government share withheld from every payment, payments to Customer Advances with revenue at delivery, forfeiture with no refunds, a Tanzanian bank (TCB) integration, plots as stock (Stock Entry). Money fields are `Float`. | **Reject.** Keep the idea of copying a schedule from a Sales Order for P2. |
| **PropMS** (Aakvatech-Limited/propms) | Licence **inconsistent**: `LICENSE` says GPL, `hooks.py` says MIT (to clarify before any reuse). `frappe >=15,<17`, has a v16 branch. Active (30 Oct 2026). 18 test files, 145 test functions. | Leases: `Lease`, `Lease Item`, `Lease Invoice Schedule` (recurring rows built from each item's frequency, then turned into Sales Invoices or Orders). | Rental model: no sale price for the schedule to add up to, no one-off sale or installment purchase. Generates billing documents. Leasing is out of scope (SRS v2.0 §1 item 7). | **Reject** for contract capture. Reassess only if Sidra adds leasing. |
| **Real Estate ERPNext App** (anwarpatelnoori) | MIT, v0.0.1, old `setup.py` packaging, 4 commits (Jun–Nov 2023), **no tests**. | Property listings, agents, website; property types for sale or rent. | No contracts, schedules or payments; looks abandoned. | **Reject.** |
| **BuildSuite Core** (construction, bounded) | MIT, `frappe >=16,<17`, Python ≥3.14 (matches Sidra). 1,263 commits, last on 5 Nov 2026. 618 test functions. Marked **beta**. Ships its own Vue front end. | Not about contracts. Construction: BOQ, estimate templates, stage planning, measurement book, task progress, subcontractor work orders and bills, cost-code reporting. | Beta; a large app with its own UI. Its retention applies to subcontractor bills, not client retention (CON-11). Overlaps Sidra's P0 Construction Job, Stage and BOQ. | **Pilot before Phase 4.** Don't extend Sidra's construction module beyond P0 until then. Not authorised for implementation now. |

### 2.3 Conclusion

No candidate supports registering an externally prepared sale contract with its own schedule. **Adapt Sidra's existing `Sidra Sale Contract`**: it already has the units, parties, notary details, private signed copy, Company currency and approval flow that capture needs. Its main gaps are terms and schedule entry (section 4). Don't adopt LMS or PropMS. Use the ERPNext Payment Schedule in P2. Pilot BuildSuite separately.

**Effect on existing Sidra records:** none from adopting another app, because none is adopted. The changes in section 6 extend the current DocTypes. Existing contracts become "Generated from profile" and keep their frozen terms and schedules.

## 3. Contract-capture requirements (clarified)

| ID | Requirement | Source |
| --- | --- | --- |
| CC-01 | Register a contract prepared outside the system: customer, Company, contract or signing date, unit(s) with allocated prices, agreed value, currency, **external reference** (the contract's own number), parties, notary details | Handover check 1; SAL-13, SAL-19 |
| CC-02 | Attach the **original signed document**, privately, as this contract's own file. It is the legal source; the structured fields are a captured summary. | Check 1, 2; PR #12 finding 1 |
| CC-03 | Capture the contract's **own terms** without a profile or generated template. A profile, if used, only pre-fills editable values. | Check 2; INS-19 |
| CC-04 | Keep the **captured structured values** visibly separate from the attached source document (labels, section, print). | Check 2 |
| CC-05 | Enter the **actual installment schedule**: any number of rows, any amounts and due dates, irregular schedules included, and same-day rows allowed. | Check 3; INS-02, INS-14 |
| CC-06 | A helper may **propose** rows from entered terms (count, due day, grace) using the existing generator. It never replaces rows that are already there without the user confirming, and never runs on save. | Check 3 |
| CC-07 | Show the **schedule total, amount due and difference** while drafting. Confirmation is refused if they don't reconcile under the agreed rules (D1–D3). | Check 4 |
| CC-08 | **Confirmation** (submit) freezes the captured terms, schedule and attachment. Unit status becomes Under Contract. No accounting documents are created. | Check 5; INS-20; SRS v2.0 §3.4 |
| CC-09 | Registration **never requires** generating or printing a contract document. Printing stays available. | Check 6 |
| CC-10 | The profile-based generated path keeps working as an optional path. | Handover ("optional bonus") |

## 4. Current implementation against the acceptance checks (PR #12)

| # | Check | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Capture an external contract with its source, reference, parties, unit, dates, currency and value | **Partial** | Present: `customer`, `company`, `currency`, `signed_on`, `units`, `agreed_price`, `parties`, `notary_name`, `notary_reference`, `signed_copy` (private, own file). Missing: an external reference separate from the notary reference; any record of whether the contract came from outside or was generated. |
| 2 | Own terms without a template | **Fails** | `contract_profile` is mandatory for Installment (`mandatory_depends_on`); `freeze_terms()` copies the profile into `terms_snapshot`; the plan fields are read-only; overrides are prohibited (SRS v2.0 §1.5). |
| 3 | Actual amounts and dates, including irregular | **Fails** | `schedule` is `read_only`; `validate()` empties it while `docstatus == 0`; `make_schedule()` generates it only at submit, from profile terms. |
| 4 | Check against the amount due; deposits, fees, rounding | **Partial** | Generated schedules add up by construction (`services/schedule.py`). There is no check on an entered schedule. The down payment comes only from the profile. Fee rules undefined. |
| 5 | Save and reopen intact | **Partial** | Attachment and terms survive; there's no schedule before submit. |
| 6 | No generated document required | **Mostly passes** | Printing is optional. But submit needs the full signing data (D5), and Profile B contracts are blocked (D4). |

## 5. Decisions (issue #13)

| # | Decision (Mohamoud, 6 Nov 2026) | Rule for Phase A |
| --- | --- | --- |
| D1 | **Both options, chosen per contract** | The down payment is either *included in the schedule* (one or more `Down payment` rows) or *recorded separately* (a down-payment amount with no `Down payment` rows). Either way, down payment + schedule must reconcile with the agreed price. |
| D2 | **Fees are part of the contract value** | `Fee` rows count toward the agreed price like any other row. |
| D3 | **Accept a small difference up to a set limit, and show it; limit $5.00** | Confirmation allowed when the absolute difference is ≤ the limit (setting, default $5.00). The difference stays visible on the record and in the snapshot. |
| D4 | **The 14-day title deadline in Contract B is a typo; the deadline is 20 days** | Profile B: title deadline 20 days, legal hold lifted. Contract B-type contracts register like any other. |
| D5 | Open | Interim: the PR #12 signing gate applies to External contracts |
| D6 | Open | Interim: free-text terms summary plus the attachment; no structured penalty, default or title fields |
| D7 | Open | Interim: confirmation = submit by Sidra Sales Manager |
| D8 | Open | Interim: schedule only; paid-to-date out of scope (P2 import) |

## 6. Implementation brief for Codex — Phase A

**Branch:** `feature/sales-contract-capture` from `develop`, after PR #12 is merged. PR into `develop`; CI must pass. Keep every CLAUDE.md rule: no ERPNext or Frappe core edits; synthetic data only; no vouchers, payments, penalties, refunds or title transfer; no change to pricing rules or legal wording; the first-due-date rule is not changed (#1). The only profile change allowed is D4 (section 6.3).

**Task 0:** record the role change in the repository's agent instructions (`CLAUDE.md`, and `AGENTS.md` if Codex uses one): "Codex implements code changes and runs tests; Claude analyses requirements and reviews; Mohamoud / Sidra approve." Keep all other rules, except replace "never clear Profile B's legal hold" with "Profile B's hold was resolved by decision D4 (issue #13)".

### 6.1 Data model (DocType JSON in `sidra_realestate/sidra_sales` and `sidra_installments`)

| Change | Detail |
| --- | --- |
| `Sidra Sale Contract.source` | Select `External (registered)` / `Generated from profile`. Required, default `External (registered)`, `set_only_once`. |
| `Sidra Sale Contract.external_reference` | Data. Required for External at confirmation. Unique among confirmed External contracts per Company: use the transaction-safe pattern from `notary_reference_key` in PR #12 (hidden key with a unique index, set at submit). |
| `signed_copy` | Relabel "Original signed contract". The rules from PR #12 stay (private, attached to this contract's field, readable, not shared). |
| `contract_profile` | Mandatory only when `source = Generated from profile`. Optional for External, where it only pre-fills. |
| Captured terms (External) | Editable while draft: `down_payment_mode` (Select `None` / `Included in schedule` / `Recorded separately`, D1); `down_payment` (Currency: entered when Recorded separately, read-only sum of `Down payment` rows when Included, 0 when None; read-only and profile-derived for Generated); `installments`, `due_day` (1–28) and `grace_months` (0–12) as optional entries that drive the helper; and `terms_summary` (Text, "captured summary; the attached document governs", D6 interim). Section title: "Captured terms (summary of the attached contract)". |
| `Sidra Installment Line` | Add `row_type` Select `Installment` / `Down payment` / `Fee` (default `Installment`) and `description` (Data). Editable while the parent is a draft External contract; read-only otherwise. |
| `terms_snapshot` | For External, built at **confirmation** from the captured fields (`source`, `external_reference`, down payment, terms summary and helper inputs) so INS-20 holds. For Generated, unchanged. |
| Schedule totals (read-only) | `schedule_total` (all rows), `amount_due`, `schedule_difference`: shown on the form and recomputed in `validate`. |
| `Sidra Contract Settings` (new Single, Sidra Sales) | `schedule_tolerance` (Currency, default 5.00, ≥ 0; D3). Write: Sidra General Manager and System Manager; read: Sidra sales roles. Changing it never affects confirmed contracts, because the tolerance used is stored in their snapshot. |

### 6.2 Behaviour

1. **Generated path (unchanged):** every current rule and test stays as it is when `source = Generated from profile`. That covers profile snapshot, plan fields, schedule generated at submit, clause gate, legal hold, signing gate and revision (PR #12).
2. **External draft:** `validate` must **not** clear or regenerate the schedule. It renumbers `seq` by row order and checks each row: due date set, amount > 0 (exact cents), `row_type` set. Duplicate due dates are **allowed**. Dates may be in the past (historical contracts). Rows don't need to be in date order, but the form sorts on request.
3. **Fill schedule (helper):** a form button and whitelisted POST method, `propose_schedule(contract)`. It uses `services/schedule.generate_installments` with the captured agreed price, down payment, installments, due day and grace. If rows exist, the client asks "Replace the N existing rows?", and the server refuses to replace unless `replace=1` is passed. It never runs during `validate` or `submit`, and the rows stay editable afterwards. With `Included in schedule`, it asks for the down-payment amount and adds a `Down payment` row dated on the signing date, then installments for the rest. With `Recorded separately`, it builds installments for agreed price minus down payment and adds no down-payment row.
4. **Reconciliation on save** (D1, D2):
   - `schedule_total` = sum of all rows (installments, down-payment rows and fee rows).
   - `amount_due` = `agreed_price` when `down_payment_mode` is `None` or `Included in schedule`, and `agreed_price − down_payment` when it is `Recorded separately`.
   - `schedule_difference` = `amount_due − schedule_total`.
   - Row rules: `Recorded separately` refuses `Down payment` rows; `Included in schedule` needs at least one; `None` refuses them.
   - If the difference isn't zero, add a form indicator and a non-blocking `msgprint` on save, saying whether it is within the limit.
5. **Confirmation (submit) for External**, in this order:
   - (a) legal hold if a held profile is linked (no seeded profile is held after D4, but the mechanism stays for future holds);
   - (b) signing gate from PR #12 (D5 interim);
   - (c) `external_reference` set and unique, using the transaction-safe key;
   - (d) down-payment rules from step 4;
   - (e) refuse if `abs(schedule_difference) > schedule_tolerance` (D3). Within the limit, require the confirming user to acknowledge it (a confirm dialog on the client; on the server, store the difference and the tolerance in the snapshot);
   - (f) at least one row;
   - (g) lock the units in name order and mark them Under Contract, converting a matching reservation (PR #12 lock order);
   - (h) build `terms_snapshot`, including `down_payment_mode`, `down_payment`, `schedule_difference` and the `schedule_tolerance` used.
   
   No generated document, print, invoice, Sales Order or payment is created.
6. **After confirmation:** the schedule, captured terms, attachment and snapshot are immutable (submitted document). Cancellation stays refused (P0).
7. **Permissions:** unchanged roles. Sidra Sales User drafts; Sidra Sales Manager confirms (D7 interim). `propose_schedule` needs write permission on the contract.
8. **Print:** stays optional. For External, show "Registered copy of an external contract — the attached original governs" and the external reference. The schedule section prints entered rows with their type.

### 6.3 Migration

- Patch `v0_3.set_contract_source`: every existing contract becomes `source = Generated from profile`, and its schedule rows become `row_type = Installment`. Existing contracts get `down_payment_mode` = `Recorded separately` when `down_payment > 0`, otherwise `None`. No amounts or dates change.
- **D4, Profile B:** update the seed in `install.py` for new sites (`title_deadline_days` 20, `legal_hold` 0, `legal_hold_reason` cleared, note "Title deadline 20 days; the 14 in Contract B is a typo (D4, issue #13)"). Add patch `v0_3.resolve_profile_b_title_deadline`. It changes Profile B **only if it still has the seeded hold values** (`legal_hold` 1 and `title_deadline_days` 0), sets 20 days, lifts the hold, and adds a Comment on the profile citing issue #13. Otherwise it leaves the profile alone and logs that management has already changed it. Contracts already saved keep their own frozen terms (INS-20).
- Create `Sidra Contract Settings` with `schedule_tolerance` 5.00 if it isn't set.
- Back-fill `schedule_total`, `amount_due` and `schedule_difference` for existing contracts.
- Run `migrate` at least twice in a row (the role-profile lesson from PR #12).

### 6.4 Tests (Frappe integration unless noted)

- **Acceptance scenario, test name `test_register_external_contract_irregular_schedule`:**
  - Contract EXT-DEMO-0001, $10,000, zero down payment, two units.
  - Irregular schedule: $2,500 on the signing date, $2,500 the same day, then $1,000 on each of five irregular dates.
  - Upload the original PDF, save, then reopen with `frappe.get_doc` (rows, amounts, dates, types, attachment and external reference all preserved).
  - Confirm as Sales Manager.
  - Assert no Print Format output, Sales Order, Sales Invoice, Payment Entry, Journal Entry or GL Entry was created; units Under Contract; snapshot contains the captured values.
- `propose_schedule` on an empty table, on a filled table without `replace` (refused), and with `replace=1`. Proposed rows stay editable, and saving doesn't change them.
- Difference above the limit: saving works and shows the difference; confirmation is refused.
- D1: `Included in schedule` with a $3,000 `Down payment` row plus 24 × $250, against $9,000, confirms; `Recorded separately` with $3,000 and 24 × $250 rows confirms; mixing the modes (a down-payment row while `Recorded separately`) is refused.
- D2: a `Fee` row counts toward the total, so a contract only reconciles when the fee is included in the agreed price.
- D3: a difference of $4.00 confirms after acknowledgement and is stored in the snapshot; $5.00 confirms; $5.01 is refused; changing the setting afterwards doesn't change the confirmed snapshot.
- D4: on a fresh install, Profile B has 20 days and no hold. The patch changes a seeded held Profile B, leaves a manually edited one alone, and is safe to run twice. A Contract B-type registration ($9,000, $3,000 down, 24 × $250 from the 10th, 3 months' grace) confirms.
- External reference: required at confirmation; normalised; duplicate refused, including a two-connection concurrent test (pattern in `tests/test_concurrency.py`); drafts may share one.
- Profile optional for External; a test profile created on legal hold still blocks confirmation (the mechanism remains).
- Existing tests that relied on Profile B being on hold must switch to a test-created held profile. Their intent is kept, not deleted.
- Generated path regression: the whole existing contract suite passes unchanged.
- Rows read-only after confirmation; editing via `save` raises.
- Migration patch: existing contracts become Generated, with rows typed `Installment`.
- Pure test (if helper logic is added to `services/schedule.py`): any new function, with `test_engine_*` naming.

### 6.5 Demonstration (required for review)

On a fresh site, following `docs/DEPLOYMENT_v0.1.md`, with fictional data (company "Sidra Demo Homes", buyer "Demo Buyer …", reference "EXT-DEMO-…"):

1. Register an external contract with the original PDF attached and an **irregular** schedule, including two rows on the same date. Save.
2. Reopen it: screenshot of the captured terms, schedule (types, amounts, dates), totals and attachment.
3. Show a contract where the schedule doesn't reconcile: a difference over $5 is refused, and one within $5 is shown and confirmed after acknowledgement.
4. Register a Contract B-type contract with the down payment recorded separately, and another with the down payment included in the schedule.
5. Confirm the reconciling contract as Sales Manager: screenshot of the submitted record. **Don't open Print** before or during confirmation.
6. Query output (or a report screenshot) showing no Sales Order, Sales Invoice, Payment Entry, Journal Entry or GL Entry for the contract.

### 6.6 Out of scope for Phase A

Paid-to-date import (D8); structured penalty, default or title terms (D6); copying the schedule into an ERPNext Sales Order or Invoice Payment Schedule (P2, Finance gate); relaxing the signing gate (D5); any accounting; BuildSuite; a snapshot of unit details on the printed contract (known limitation from PR #12).

### 6.7 What Codex returns for review

The PR diff, with requirement IDs (CC-01 to CC-10 plus spec IDs), migration notes and the decisions it relied on. The output of `ruff check`, the pure tests, `bench run-tests --app sidra_realestate`, `migrate` twice and `bench build`. The demonstration screenshots and the saved record (`frappe.get_doc(...).as_dict()` of the demo contract, without file contents). Any gap reported explicitly.

## 7. Phase B (after D5–D8 are answered)

Apply D5 to the signing gate for External contracts, D6 to structured terms, D7 to approval wording and audit, and D8 to the import design. D1–D4 are in Phase A. Claude will turn the answers into a short Phase B brief.

## 8. Review checklist (Claude)

- Does every acceptance check 1–6 pass on the **saved and reopened** record, not only in code?
- Do the schedule rows survive save, reopen, propose without replace, and confirm unchanged?
- Is there no implicit regeneration anywhere (`validate`, `before_submit`, client scripts)?
- Do both down-payment modes reconcile correctly, and is mixing them refused? Do fee rows count?
- Is the $5.00 limit applied as an absolute value, stored in the snapshot, and unaffected by later setting changes?
- Did the Profile B patch change only the seeded held profile? Are existing contracts' frozen terms untouched?
- Does the Generated path still pass its whole suite?
- Do the external-reference uniqueness and lock order hold under two connections?
- Is nothing created in Accounts? Is there no print or generation on the registration path?
- Is the migration idempotent? Are existing contracts unchanged apart from the new fields?
