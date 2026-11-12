# Sidra ERP — Buyer KYC and Title Transfer Tracker v0.1

**Version:** 0.1 (12 Nov 2026) · **Status:** implemented for review · **App version:** 0.1.10
**Scope:** P1 sales items from SRS v2.0 §3.2, §3.5 and §7: buyer KYC and the title transfer tracker.
**Requirements:** SAL-07, SAL-08, SAL-18.
**Not in scope:** receipts and payment allocation (P2), any late-title amount, refund or penalty, and any change of unit status or ownership (`CLAUDE.md` rule 3).

## 1. Sources for each rule

| Rule | Source |
| --- | --- |
| Record the buyer's ID or passport, phone, address, guarantor details and scanned copies | SAL-07 |
| Track documents required, land office submission, deed number and the date handed to the customer | SAL-08 |
| Count the title deadline from the final payment and alert before it passes | SAL-18 |
| KYC is restricted data; no public KYC files; no unrestricted reads | SRS v2.0 §3.5, §5, §8 |
| Approvals that move ownership need a second person; the General Manager approves title transfer | SRS v1.6 §2 |
| Title deadline days and the late-title term are frozen on each contract | INS-20; D4, D6 |
| The eight decisions below | G12 (Mohamoud, 12 Nov 2026) |

## 2. Buyer KYC (`Sidra Customer KYC`)

- **One restricted record per Customer**, separate from the Customer form (G12). Staff who can open a customer don't automatically see the ID data.
- **Content:** ID type (National ID or Passport), ID number, name on ID, ID expiry, phone, address, scanned ID, and guarantor details (name, phone, relationship, ID number, scanned ID).
- **Access (G12):**
  - Sidra Sales User: creates and edits;
  - Sidra Sales Manager: creates, edits, deletes and **verifies**;
  - Sidra General Manager: reads;
  - no other role has access, including Finance Reviewer, construction roles and System Manager.
- **Verification** (`verify_kyc`, Sales Manager only) needs the scanned ID uploaded to the record's own field as a private file. A guarantor scan, if present, must meet the same rule.
- **Scans** must be private files.
- **Changing** any detail of a verified record returns it to Draft until a Sales Manager verifies it again. The verification fields can't be set through an ordinary save.
- **Contract gate (G12):** a contract **generated from a profile** (including cash contracts) can't be submitted until the buyer has verified KYC. **Registered (external) contracts don't need it**, in line with D5.

## 3. Title transfer tracker (`Sidra Title Transfer`, STT-YYYY-)

One record per unit of a confirmed sale contract. It takes its customer, Company, title deadline days and late-title term from the contract.

**Record only (G12; `CLAUDE.md` rule 3)**
- The record never changes the unit's status, the contract or ownership.
- No late-title amount is calculated, applied or posted. The record shows **days past the deadline** and the contract's frozen late-title term as reference text.

**Final payment (until receipts exist in P2)**
- A Sales Manager enters the final payment date and uploads proof as a private file on the record.
- **A different Sales Manager confirms it** (`confirm_final_payment`). The person who entered it can't.
- The date can't be in the future or before the contract date.
- Once confirmed, the date and evidence are frozen and the record can't be deleted.

**Deadline and alert (SAL-18)**
- The deadline is the contract's title deadline days (20 in Profiles A and B) after the confirmed final payment date.
- Status:
  - *Awaiting Final Payment*: no confirmed final payment yet;
  - *No Deadline on Contract*: the contract records no title deadline days;
  - *In Progress*: more than 5 days left;
  - *Due Soon*: from **5 days before** the deadline, including the deadline day;
  - *Overdue*: after the deadline, with the number of days;
  - *Handed Over* or *Handed Over Late* (with the days late).
- A daily job keeps the status current. The list shows Due Soon in orange and Overdue in red.

**Documents, land office and deed (SAL-08)**
- Document rows: document name, received, received date, private file.
- Land office: submitted date and reference. Deed: number and issue date.

**Handover**
- A Sales Manager enters the deed number, handover date, recipient and the customer's signed receipt (private file on the record).
- **The General Manager confirms it** (`confirm_handover`), and can't be the person who entered it.
- It needs a confirmed final payment. The handover can't be dated before the final payment.
- After confirmation the whole record is locked.

## 4. Permissions

| DocType / action | Create / edit | Confirm | Read only |
| --- | --- | --- | --- |
| Customer KYC | Sales User, Sales Manager | Sales Manager verifies | General Manager |
| Title Transfer | Sales Manager | another Sales Manager confirms the final payment; General Manager confirms the handover | Sales User, General Manager, Finance Reviewer, System Manager |

Creating a KYC record needs read access to the Customer. Creating a title record needs read access to the contract.

## 5. Choices to confirm

These weren't asked in G12. They're built as described and are small to change:

1. A guarantor is optional. If any guarantor detail is entered, the name and phone are required.
2. An expired ID is stored but doesn't block verification.
3. The same Sales Manager who entered a KYC record may verify it.
4. A confirmed final payment or handover can't be undone in the system.
5. The alert is the status and list colour. No email or message is sent.

## 6. Changing these rules

The 5-day alert (`ALERT_DAYS`) is a constant in `sidra_realestate/services/title.py`. It changes only with an approved spec version (`CLAUDE.md` rule 2).
