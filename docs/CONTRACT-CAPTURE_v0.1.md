# Sidra ERP — Contract Capture: Reuse Assessment and Implementation Brief v0.1

6 Nov 2026 · prepared by Claude (analysis and review) for Codex (implementation), under the Sidra Handover of 6 Nov 2026. Decisions: issue #13.

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

D1 down payment in the schedule or separate · D2 fees · D3 rounding tolerance · D4 Profile B hold for already-signed contracts · D5 signing data for external contracts · D6 structured penalty, default and title terms · D7 confirmation = INS-19 approval · D8 paid-to-date for live contracts.

Phase A below uses the **interim rules** in issue #13. They are the conservative options: anything that depends on D1 or D2 can be saved but not confirmed.

## 6. Implementation brief for Codex — Phase A

**Branch:** `feature/sales-contract-capture` from `develop`, after PR #12 is merged. PR into `develop`; CI must pass. Keep every CLAUDE.md rule: no ERPNext or Frappe core edits; synthetic data only; no vouchers, payments, penalties, refunds or title transfer; no change to profile values, pricing rules or legal wording; Profile B stays on legal hold; the first-due-date rule is not changed (#1).

**Task 0:** record the role change in the repository's agent instructions (`CLAUDE.md`, and `AGENTS.md` if Codex uses one): "Codex implements code changes and runs tests; Claude analyses requirements and reviews; Mohamoud / Sidra approve." Keep all other rules.

### 6.1 Data model (DocType JSON in `sidra_realestate/sidra_sales` and `sidra_installments`)

| Change | Detail |
| --- | --- |
| `Sidra Sale Contract.source` | Select `External (registered)` / `Generated from profile`. Required, default `External (registered)`, `set_only_once`. |
| `Sidra Sale Contract.external_reference` | Data. Required for External at confirmation. Unique among confirmed External contracts per Company: use the transaction-safe pattern from `notary_reference_key` in PR #12 (hidden key with a unique index, set at submit). |
| `signed_copy` | Relabel "Original signed contract". The rules from PR #12 stay (private, attached to this contract's field, readable, not shared). |
| `contract_profile` | Mandatory only when `source = Generated from profile`. Optional for External, where it only pre-fills. |
| Captured terms (External) | Editable while draft: `down_payment` (Currency, editable for External; read-only and profile-derived for Generated), `installments`, `due_day` (1–28), `grace_months` (0–12) as optional entries that drive the helper, and `terms_summary` (Text, "captured summary; the attached document governs", D6 interim). Section title: "Captured terms (summary of the attached contract)". |
| `Sidra Installment Line` | Add `row_type` Select `Installment` / `Down payment` / `Fee` (default `Installment`) and `description` (Data). Editable while the parent is a draft External contract; read-only otherwise. |
| `terms_snapshot` | For External, built at **confirmation** from the captured fields (`source`, `external_reference`, down payment, terms summary and helper inputs) so INS-20 holds. For Generated, unchanged. |
| Schedule totals (read-only) | `schedule_total`, `amount_due`, `schedule_difference`: shown on the form and recomputed in `validate`. |

### 6.2 Behaviour

1. **Generated path (unchanged):** every current rule and test stays as it is when `source = Generated from profile`. That covers profile snapshot, plan fields, schedule generated at submit, clause gate, legal hold, signing gate and revision (PR #12).
2. **External draft:** `validate` must **not** clear or regenerate the schedule. It renumbers `seq` by row order and checks each row: due date set, amount > 0 (exact cents), `row_type` set. Duplicate due dates are **allowed**. Dates may be in the past (historical contracts). Rows don't need to be in date order, but the form sorts on request.
3. **Fill schedule (helper):** a form button and whitelisted POST method, `propose_schedule(contract)`. It uses `services/schedule.generate_installments` with the captured agreed price, down payment, installments, due day and grace. If rows exist, the client asks "Replace the N existing rows?", and the server refuses to replace unless `replace=1` is passed. It never runs during `validate` or `submit`, and the rows stay editable afterwards. If the contract has a down payment, the helper adds a `Down payment` row dated on the signing date (the D1 interim still blocks confirmation).
4. **Reconciliation on save:** `schedule_total` = sum of rows; `amount_due` = `agreed_price` (D1 and D2 interim); `schedule_difference` = `amount_due − schedule_total`. If the difference isn't zero, add a form indicator and a non-blocking `msgprint` on save.
5. **Confirmation (submit) for External**, in this order:
   - (a) legal hold if a held profile is linked (D4 interim);
   - (b) signing gate from PR #12 (D5 interim);
   - (c) `external_reference` set and unique, using the transaction-safe key;
   - (d) **D1/D2 interim:** refuse if `down_payment > 0` or any `Down payment` / `Fee` row exists, saying "awaiting decision D1/D2 (issue #13)";
   - (e) refuse unless `schedule_difference == 0` exactly (D3 interim);
   - (f) at least one row;
   - (g) lock the units in name order and mark them Under Contract, converting a matching reservation (PR #12 lock order);
   - (h) build `terms_snapshot`.
   
   No generated document, print, invoice, Sales Order or payment is created.
6. **After confirmation:** the schedule, captured terms, attachment and snapshot are immutable (submitted document). Cancellation stays refused (P0).
7. **Permissions:** unchanged roles. Sidra Sales User drafts; Sidra Sales Manager confirms (D7 interim). `propose_schedule` needs write permission on the contract.
8. **Print:** stays optional. For External, show "Registered copy of an external contract — the attached original governs" and the external reference. The schedule section prints entered rows with their type.

### 6.3 Migration

- Patch `v0_3.set_contract_source`: every existing contract becomes `source = Generated from profile`, and its schedule rows become `row_type = Installment`. No amounts or dates change.
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
- Difference ≠ 0: saving works and shows the difference; confirmation is refused. Exact cents (`0.01` off is refused).
- Down payment > 0, or a `Fee` row: saves; confirmation refused with the D1/D2 message.
- External reference: required at confirmation; normalised; duplicate refused, including a two-connection concurrent test (pattern in `tests/test_concurrency.py`); drafts may share one.
- Profile optional for External; Profile B linked → legal hold message.
- Generated path regression: the whole existing contract suite passes unchanged.
- Rows read-only after confirmation; editing via `save` raises.
- Migration patch: existing contracts become Generated, with rows typed `Installment`.
- Pure test (if helper logic is added to `services/schedule.py`): any new function, with `test_engine_*` naming.

### 6.5 Demonstration (required for review)

On a fresh site, following `docs/DEPLOYMENT_v0.1.md`, with fictional data (company "Sidra Demo Homes", buyer "Demo Buyer …", reference "EXT-DEMO-…"):

1. Register an external contract with the original PDF attached and an **irregular** schedule, including two rows on the same date. Save.
2. Reopen it: screenshot of the captured terms, schedule (types, amounts, dates), totals and attachment.
3. Show a contract where the schedule doesn't reconcile: the difference is shown and confirmation is refused.
4. Confirm the reconciling contract as Sales Manager: screenshot of the submitted record. **Don't open Print** before or during confirmation.
5. Query output (or a report screenshot) showing no Sales Order, Sales Invoice, Payment Entry, Journal Entry or GL Entry for the contract.

### 6.6 Out of scope for Phase A

Paid-to-date import (D8); structured penalty, default or title terms (D6); copying the schedule into an ERPNext Sales Order or Invoice Payment Schedule (P2, Finance gate); Profile B registration (D4); relaxing the signing gate (D5); any accounting; BuildSuite; a snapshot of unit details on the printed contract (known limitation from PR #12).

### 6.7 What Codex returns for review

The PR diff, with requirement IDs (CC-01 to CC-10 plus spec IDs), migration notes and the decisions it relied on. The output of `ruff check`, the pure tests, `bench run-tests --app sidra_realestate`, `migrate` twice and `bench build`. The demonstration screenshots and the saved record (`frappe.get_doc(...).as_dict()` of the demo contract, without file contents). Any gap reported explicitly.

## 7. Phase B (after issue #13 is answered)

Apply D1–D3 to `amount_due` and to the rules for down-payment and fee rows. Apply D4 to registering B-type contracts, D5 to the signing gate for External contracts, D6 to structured terms, D7 to approval wording and audit, and D8 to the import design. Claude will turn the answers into a short Phase B brief.

## 8. Review checklist (Claude)

- Does every acceptance check 1–6 pass on the **saved and reopened** record, not only in code?
- Do the schedule rows survive save, reopen, propose without replace, and confirm unchanged?
- Is there no implicit regeneration anywhere (`validate`, `before_submit`, client scripts)?
- Can D1/D2 contracts be saved but not confirmed? Is the difference shown?
- Does the Generated path still pass its whole suite?
- Do the external-reference uniqueness and lock order hold under two connections?
- Is nothing created in Accounts? Is there no print or generation on the registration path?
- Is the migration idempotent? Are existing contracts unchanged apart from the new fields?
