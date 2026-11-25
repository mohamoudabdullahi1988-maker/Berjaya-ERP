# Berjaya — Client-side Rules Audit v0.1

**Document version:** v0.1 · **Date:** 13 Nov 2026 · **Prepared for:** Mohamoud Abdullahi Sheikh · recorded by Claude Code
**Decision:** G17 (`docs/DECISIONS-AND-GATES_v0.1.md`) · **Baseline:** `develop` @ `5508f13`, app v0.1.17
**Status:** document only. No rule is moved or changed in this PR.

## 1. Why this exists

The `/berjaya` interface will not run Desk form scripts. Any rule that lives only in a form script, a list script or a field condition disappears for a user of the new interface unless the server also enforces it. This lists every such rule found and whether the server has its own check.

**Read:** all 17 form, list and report scripts under `sidra_realestate/**/doctype` and `report`, `public/js/desk_forms.js`, and every `mandatory_depends_on` / `read_only_depends_on` in the DocType JSON (34 fields). Server checks were confirmed by reading the Python named in the last column. Nothing was run against a site, so behaviour is **read from code, not verified by test**.

**Not found in the repository:** Client Script records, Property Setter fixtures, Workflow records. One Custom Field (`sidra_location`) is created by `api/locations.py`. Customisations made by hand on the test site are not in the repository and are **not verified**.

## 2. Summary

| Result | Count |
| --- | --- |
| Rule also enforced on the server | 17 |
| Enforced on the server only in part | 2 |
| Client side only | 3 |
| Not verified | 2 |

The app is already server-first: every action button calls a whitelisted method that re-checks role, state and second-person rules. The gaps are in section 4.

## 3. Rules with a server-side equivalent

| DocType | Rule | Where it lives today | Server-side equivalent |
| --- | --- | --- | --- |
| Sidra Reservation | Cannot be saved directly; changes only through the actions | `sidra_reservation.js` `disable_save()` | Yes — `validate` refuses unless written by the service |
| Sidra Reservation / Sidra Unit | Reserve and Cancel only for Sales User / Sales Manager | Button shown by role in `sidra_unit.js`, `sidra_reservation.js` | Yes — `frappe.only_for` in `services/reservations.py` |
| Sidra Unit | Reserve only when Available; cancel only an Active reservation | Button conditions | Yes — status checked under row lock |
| Sidra Unit | Reservation lasts at least one day | Dialog check | Yes — `reserve_unit` |
| Sidra Unit | Price not editable after creation | `cash_price` `read_only_depends_on` | Yes — `validate_price_change` requires Price History |
| Sidra Construction Job | BOQ locked once a revision is approved | `set_df_property("boq", "read_only")` | Yes — `protect_boq` |
| Sidra Construction Job | Certify only a Completed, 100 % stage with an actual end date; Project Manager only | Button and prompt filter | Yes — `certify_stage` (also refuses future end dates and closed jobs) |
| Sidra Construction Quotation | Approve Contract: issued, client acceptance recorded and attached; General Manager only | Button conditions | Yes — `approve_contract` |
| Sidra Construction Quotation | Fixed fee required when pricing basis is Fixed Fee | `mandatory_depends_on` | Yes — quoted amount must be greater than zero |
| Sidra Customer KYC | Verify needs the scanned ID; Sales Manager only | Button conditions | Yes — `verify_kyc` |
| Sidra Sale Contract | Profile required for a generated installment contract | `mandatory_depends_on` | Yes — "Choose a contract profile" |
| Sidra Sale Contract | Terms and schedule read-only unless External (registered) (29 fields) | `read_only_depends_on` | Yes — terms are frozen in `terms_snapshot`; a generated schedule is rebuilt on submit |
| Sidra Sale Contract | Fill Schedule and Revise Draft only on a draft with write permission | Button conditions | Yes — `propose_schedule` and `revise_draft` check write permission and draft state |
| Sidra Sale Contract | Schedule difference above the tolerance blocks confirmation | Headline alert | Yes — `check_external_confirmation` against Contract Settings tolerance |
| Sidra Sale Quotation | Discount approval by level; preparer cannot approve | Button conditions | Yes — `approve_discount` / `approval_problem` |
| Sidra Sale Quotation | Profile must be active and not on legal hold; unit Available or Reserved | `set_query` filters | Yes — `set_installment_option`, `check_unit_quotable` |
| Sidra Title Transfer | Contract must be confirmed; second Sales Manager confirms final payment; General Manager confirms handover; evidence required | `set_query` and button conditions | Yes — `set_contract_fields`, `confirm_final_payment`, `confirm_handover` |

## 4. Gaps — rules the new interface would lose

| # | DocType | Rule | Where it lives today | Server side | Risk if `/berjaya` skips it |
| --- | --- | --- | --- | --- | --- |
| R1 | Sidra Sale Contract | **Acknowledge a schedule difference within the tolerance before confirming** (D3) | `before_submit` confirm dialog in `sidra_sale_contract.js` | **Client only.** The server enforces the limit and stores the difference, but nothing records that a person acknowledged it | A contract with a difference up to the tolerance is confirmed with no acknowledgement. Money-adjacent: needs a decision, not a guess |
| R2 | Sidra Contract Import | **Import only after a successful Validate** | Import button shown only when status is Validated | **Partial.** `run_import` checks write permission and re-validates every row, but does not require a prior Validate run | A caller can import without the dry run. Rows are still checked, so bad rows are refused |
| R3 | Sidra Unit | **Warning when reserving a unit with no positive price** | Confirm dialog in `sidra_unit.js` | **Client only** (a warning, not a block) | Unpriced units reserved with no prompt |
| R4 | Sidra Unit / Sidra Construction Job | Location map hidden until asked; failed map tiles do not leave a grey panel | `public/js/desk_forms.js` | **Client only** — presentation, not a business rule | None |
| R5 | Sidra Sale Contract | `source` required for an installment contract | `mandatory_depends_on` | **Partial** — the server defaults a blank source to External (registered) | A blank source is silently treated as External |
| R6 | Sidra Contract Profile | `legal_hold_reason` required when legal hold is ticked | `mandatory_depends_on` | **Not verified** — no check found in the profile's Python; whether Frappe v16 applies `mandatory_depends_on` to API saves was not tested | A hold could be saved without its reason |
| R7 | All DocTypes | Fields shown or hidden by `depends_on` (49 conditions) | DocType JSON | **Not verified** one by one — display only by design, but a hidden field is still writable through the API | Low; review per screen as each is rebuilt |

## 5. Proposals — not done in this PR

| # | Proposal |
| --- | --- |
| 1 | R1: decide whether the acknowledgement must be recorded (who, when) on the server. **Decided 14 Nov 2026 (G22): yes, for confirmation from `/berjaya`; implemented in v0.1.25.** |
| 2 | R2: have `run_import` refuse unless the status is Validated and the file is unchanged since. |
| 3 | R6: add a server check for the legal hold reason, or confirm by test that Frappe enforces it. |
| 4 | Every `/berjaya` screen that writes takes its rules from the whitelisted methods in section 3, never from a copy in the frontend. |
