# Sidra ERP — Brokerage and Commission Specification v0.1

7 Nov 2026 · **Draft for approval** by Mohamoud. Builds on SRS v1.6 SAL-11, SAL-15, SAL-16 and SRS v2.0 §3.2 "Brokerage". Decisions given by Mohamoud on 7 Nov 2026 are marked **(M)**. Nothing here is built until this spec is approved (`CLAUDE.md` rule 1).

## 1. Decisions this spec rests on

| ID | Decision | Source |
| --- | --- | --- |
| B1 | Two journeys: Sidra as broker for an outside owner's plot, **and** outside agents earning commission on Sidra's own plot sales | (M) |
| B2 | Commission is **2.5 % of the total plot price** by default. It is a setting, editable per listing or per contract before confirmation | (M) "around 2.5 percent" |
| B3 | Commission is **due in full when the buyer's first payment is received**, whatever the size of that payment. If the first payment is smaller than the commission, the gap is still due and is settled separately | (M) |
| B4 | The simplest journey: few statuses, no approvals beyond those that already exist | (M) |
| B5 | Commission is **recorded, not posted**, until Finance approves the posting matrix (`CLAUDE.md` rule 3; DECISIONS G4: ERPNext is the only ledger) | Existing gate |

## 2. Journey A: Sidra sells an owner's plot (SAL-15, SAL-16)

1. **Mandate.** A land owner asks Sidra to sell a plot. Sales staff create a **Brokerage Listing** with the owner, the plot details and the asking price. Commission is pre-filled at 2.5 % (B2). The signed mandate is attached. Status: **Listed**.
2. **Buyer found.** Staff record the buyer, the agreed sale price and the expected date of the first payment. Status: **Sale agreed**. The commission amount is now fixed: 2.5 % × agreed sale price.
3. **First payment received.** Finance records the date and the receipt reference of the buyer's first payment. Status: **Commission due**.
   - The commission is due in full from this payment (B3).
   - The record shows the amount to pass to the owner: first payment − commission. If that would be negative, it shows **0** to pass on and **the gap still owed** by the owner.
4. **Commission collected.** Finance records the date and reference. Status: **Closed**.
5. **Withdrawn.** The owner can withdraw the listing at any time before step 3. No commission is due.

The listing is kept apart from Sidra's own plots. It never appears in Sidra's unit stock or sale revenue (SRS v2.0 §3.2).

## 3. Journey B: an agent brings a buyer for a Sidra plot (SAL-11)

1. **Agent.** Sales staff register the agent once as a **Sidra Agent**, with name, phone and ID number. The default rate is 2.5 % (B2).
2. **Contract.** On a Sale Contract (generated or registered), staff choose the agent. The rate is copied from the agent and can be edited while the contract is a draft. At confirmation, the commission is frozen: rate × agreed price. The rate and amount are stored in the contract snapshot (INS-20). Commission status: **Not due**.
3. **First payment received.** Finance records the date and receipt reference of the buyer's first payment. Commission status: **Due**. The full amount is due (B3).
4. **Paid to agent.** Finance records the date and payment reference. Status: **Paid**.

A contract without an agent has no commission. Cancelling a contract before step 3 means no commission is due.

## 4. Data model (proposed)

| DocType | Module | Key fields |
| --- | --- | --- |
| **Sidra Agent** (new) | Sidra Brokerage | `agent_name`, `phone`, `id_number`, `default_commission_rate` (Percent, default 2.5), `active` |
| **Sidra Brokerage Listing** (new) | Sidra Brokerage | Owner (`owner_name`, `owner_phone`, `owner_id_number`); plot (`location`, `district`, `dimensions`, `description`); `asking_price`; `commission_rate` (default from settings, 2.5); mandate attachment; `status` (Listed / Sale agreed / Commission due / Closed / Withdrawn); buyer (Link Customer); `sale_price`; `commission_amount` (read-only); first payment date, reference and amount; `amount_to_owner` and `commission_shortfall` (read-only); collection date and reference |
| **Sidra Sale Contract** (fields added) | Sidra Sales | `agent` (Link Sidra Agent), `commission_rate`, `commission_amount` (read-only, frozen at confirmation), `commission_status` (Not due / Due / Paid), first payment date and reference, commission paid date and reference |
| **Sidra Contract Settings** (field added) | Sidra Sales | `default_commission_rate` (Percent, 2.5) |

The commission base is the **agreed price** on a Sale Contract and the **agreed sale price** on a listing.

## 5. Roles

| Step | Who |
| --- | --- |
| Create a listing or agent; choose the agent on a contract | Sidra Sales User |
| Change a commission rate away from the default | Sidra Sales Manager |
| Record the first payment, commission collected or paid | Sidra Finance Reviewer |
| Withdraw a listing | Sidra Sales Manager |

## 6. Out of scope until Finance approval (B5)

Sales Invoices to owners, Purchase Invoices or Journal Entries for agent payouts, automatic detection of the first payment from ERPNext Payment Entries, tax on commission, and clawback of commission when a sale is cancelled after the first payment.

## 7. Acceptance tests

| ID | Case | Expected |
| --- | --- | --- |
| BR-01 | Listing, sale price $10,000, default rate | Commission $250.00 |
| BR-02 | Listing, first payment $2,000 | Commission due $250; $1,750 to the owner; shortfall $0 |
| BR-03 | Listing, first payment $200 | Commission due in full ($250); $0 to the owner; shortfall $50 owed by the owner |
| BR-04 | Listing withdrawn before the first payment | Status Withdrawn; no commission due |
| BR-05 | Contract $11,000 with agent at 2.5 %, confirmed | Commission $275.00, frozen in the snapshot; status Not due |
| BR-06 | Agent's default rate changed after confirmation | The confirmed contract keeps $275.00 |
| BR-07 | First payment recorded on BR-05 | Status Due, amount $275.00 |
| BR-08 | Commission paid recorded | Status Paid, date and reference stored; no GL Entry, invoice or payment created |
| BR-09 | Contract without an agent | No commission fields required; status blank |
| BR-10 | Sales User edits the commission rate | Refused; Sales Manager allowed |

## 8. Questions for approval

1. Is the commission base the **agreed price including fees** (D2 puts fees inside the price), or the plot price without fees? This draft uses the agreed price.
2. For journey A, does Sidra **receive the buyer's first payment itself** and pass the rest to the owner (as drafted), or does the owner collect and pay Sidra the commission?
3. Should a confirmed contract's commission rate ever change (for example by a Sales Manager with a reason), or stay frozen as drafted?
