# Sidra ERP — Construction Controls v0.2

**Version:** 0.2 (12 Nov 2026) · **Status:** implemented for review (PR #38) · **App version:** 0.1.9
**Scope:** P1 construction items from SRS v2.0 §3.1 and §7 and handoff "Subsequent PRs" item 4:
- quotation to contract;
- BOQ revisions;
- site inspections;
- variation orders;
- stage certification.

**Requirements:** CON-02, CON-03, CON-04, CON-05, CON-06.
**Not in scope:** CON-07 milestone invoices, retention release (CON-11) and costing (CON-08). These wait for P2 finance approval (`CLAUDE.md` rule 3).
**Changes from v0.1:** Mohamoud's answers to issue #37 (decision G11 in `docs/DECISIONS-AND-GATES_v0.1.md`):
- variation orders are additions only;
- the General Manager approves orders above $1,000;
- contract terms come only from an approved quotation (CON-03, added);
- the General Manager approves every contract;
- payment milestones are the stages' Billing %;
- retention is 0–10 %.

## 1. Sources for each rule

| Rule | Source |
| --- | --- |
| Project Manager approves stage completion and variation orders; Engineer / Inspector approves inspection reports | SRS v1.6 §2 role table |
| Approvals that move money need a second person | SRS v1.6 §2 |
| Quotation from a BOQ or a fixed fee, printed on Sidra letterhead | CON-02 |
| Approved quotation becomes a contract with value, start, duration, payment milestones and retention % | CON-03 |
| Variations change the contract value, with client approval recorded | CON-06 |
| Inspections record date, inspector, checklist results, photos, defects and next action | CON-05 |
| Additions only; above $1,000 the GM approves; the GM approves contracts; milestones are stage Billing % totalling 100; retention 0–10 % | G11 (issue #37) |
| Approved variations reconcile to the contract total; progress sign-off is not revenue recognition | SRS v2.0 §3.1 |
| No public files for customer documents | SRS v2.0 §8 |

## 2. BOQ revisions (`Sidra BOQ Revision`, SBR-YYYY-)

- A draft copies the job's current BOQ and stores the approved revision it was based on.
- The Sidra Project Manager approves it alone, by submitting (G11). Approval is refused when:
  - another revision was approved after this draft was made (a stale draft);
  - the draft changes nothing;
  - the job is Closed or Cancelled.
- Approval numbers the revision (1, 2, …), stores the previous total and the difference, and copies the lines to the job.
- From the first approved revision on, the job's BOQ can't be edited directly. It changes only through a new revision.
- An approved revision is never cancelled. To change it, approve a new revision. History is kept.
- A BOQ revision doesn't change the contract value. Only variation orders do.

## 3. Quotation and contract (`Sidra Construction Quotation`, SCQ-YYYY-)

**Draft and issue (Project Manager)**
- **Pricing basis:**
  - *BOQ*: a frozen copy of the job's current BOQ. The quoted amount is the BOQ total.
  - *Fixed Fee*: for design or inspection work. The quoted amount is the fee.
- **Proposed terms:** scope, valid-until date, start date, duration in days (the end date is start + duration − 1), retention % (0–10) and retention period in whole months (0 allowed).
- **Issuing** (submit) is refused when:
  - the job's BOQ changed since the draft (BOQ basis);
  - the quotation has expired;
  - the job is Closed or Cancelled;
  - the job already has a contract.
- Issuing moves the job from Enquiry to Quoted.
- **Print:** the *Sidra Construction Quotation* print format shows the Sidra Homes letterhead, scope, BOQ or fee, terms, the job's billed stages and acceptance lines.

**Client acceptance (Project Manager, on the issued quotation)**
- The PM records who accepted for the client and the date. The date can't be in the future or after Valid Until.
- The signed quotation must be uploaded to the quotation's own field as a private file.

**Contract approval (General Manager only, G11) — Approve Contract (`approve_contract`)**
- **Requires:**
  - the client's acceptance;
  - the signed file, own and private;
  - a job that isn't Closed or Cancelled and has no contract yet;
  - stage **Billing %** that add up to exactly 100. These are the payment milestones.
- **Sets on the job:**
  - contract quotation and original contract value;
  - start, duration and end;
  - retention % and period;
  - who approved and when;
  - status Contracted (from Enquiry or Quoted).
- **Limits:** one contract per job. A contracted quotation can't be cancelled, and its acceptance can't be changed.

**On the job afterwards**
- The contract fields can't be typed or changed. An ordinary save restores them.
- Stage Billing % can't change. A new stage can be added with 0 %.
- Each stage's **Milestone Amount** is the current contract value × Billing %, in cents. The last billed stage takes the rounding, so the milestones add up to the contract value exactly. It's recalculated when variations are approved or cancelled.
- Milestone amounts and retention are recorded only. No invoice is created and no retention is held in the ledger.

## 4. Variation orders (`Sidra Variation Order`, SVO-YYYY-)

- **Additions only (G11).** The amount is positive and raises the contract value.
- **Client approval is required before submitting:**
  - who approved for the client, and the date (not in the future);
  - the client's signed approval, uploaded to this order's own field as a private file.
- **Approval (G11):**
  - the person who raised the order can't approve it;
  - up to **$1,000**, another Sidra Project Manager or the Sidra General Manager approves;
  - **above $1,000**, only the General Manager.
  - Cancelling an approved order follows the same rule.
- **Job conditions:** the job must have a contract approved from its quotation (§3) and be Contracted, In Progress, On Hold, Completed or Defects Period.
- **On the job:** Approved Variations, Current Contract Value and the milestone amounts are recalculated from submitted orders.
- **Optional link:** an approved BOQ revision of the same job.
- **Recorded only:** no Sales Order amendment, invoice or posting.

## 5. Inspection reports (`Sidra Inspection Report`, SIR-YYYY-)

- **Content:** date (not in the future), inspector, optional stage (must be one of the job's stages), checklist rows, overall result, defects, next action and due date, photos.
- **Consistency rules:**
  - A failed checklist row needs remarks.
  - A report with a failed row can't have the overall result Pass.
  - Pass with defects and Fail need a description of the defects and a next action.
  - The next action can't be due before the inspection date.
- **Photos** must be private files.
- **Approval:** the Sidra Inspector submits. The Project Manager can prepare drafts but can't submit.
- **Effect:** a submitted report changes nothing on the job and doesn't certify a stage.

## 6. Stage certification (on `Sidra Project Stage`)

- The Sidra Project Manager uses **Certify Stage** on the job (`certify_stage`). It needs a stage that is:
  - Completed;
  - 100 % complete;
  - with an actual end date that isn't in the future.
- No inspection report is required (G11).
- Certification records who certified and when. The job must not be Closed or Cancelled.
- **After certification:**
  - the stage's dates, percentages, status and engineer can't be changed;
  - the row can't be removed;
  - the certification fields can't be set or cleared through an ordinary save.
- There is no un-certify action (G11).
- Certification is a record of completion. It creates no invoice and recognises no revenue (SRS v2.0 §3.1; CON-07 is P2).

## 7. Permissions

| DocType / action | Create / edit draft | Approve (submit) | Cancel | Read only |
| --- | --- | --- | --- | --- |
| Construction Quotation | Project Manager | Project Manager (issue); **General Manager** approves the contract | Project Manager (not once contracted) | General Manager, Finance Reviewer, System Manager |
| BOQ Revision | Project Manager | Project Manager | never | General Manager, Finance Reviewer, Inspector, System Manager |
| Variation Order | Project Manager | another PM up to $1,000; General Manager any amount | same rule | Finance Reviewer, System Manager |
| Inspection Report | Inspector, Project Manager | Inspector | Inspector | General Manager, System Manager |
| Certify Stage | — | Project Manager | — | — |

Each record takes its Company and customer from the job. Creating or editing a record needs access to the job, so a Company User Permission on the job also limits the new records.

## 8. Changing these rules

The $1,000 limit (`VARIATION_GM_LIMIT`) and the 10 % retention ceiling (`RETENTION_MAX_PCT`) are constants in `sidra_realestate/services/construction.py`. They change only with an approved spec version (`CLAUDE.md` rule 2).
