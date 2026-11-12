# Sidra ERP — Construction Controls v0.1

**Version:** 0.1 (12 Nov 2026) · **Status:** implemented on `develop` for review · **App version:** 0.1.6
**Scope:** P1 construction items from SRS v2.0 §3.1 and §7 and handoff "Subsequent PRs" item 4: BOQ revisions, site inspections, variation orders and stage certification.
**Requirements:** CON-02 (revisions), CON-04, CON-05, CON-06. **Not in scope:** CON-03 quotation-to-contract, CON-07 milestone invoices, retention and costing. These wait for P2 finance approval (`CLAUDE.md` rule 3).

## 1. Sources for each rule

| Rule | Source |
| --- | --- |
| Project Manager approves stage completion and variation orders; Engineer / Inspector approves inspection reports | SRS v1.6 §2 role table |
| Approvals that move money need a second person | SRS v1.6 §2 |
| Variation orders change the contract value, with client approval recorded | CON-06 |
| Inspections record date, inspector, checklist results, photos, defects and next action | CON-05 |
| BOQ with revisions; approved variations reconcile to the contract total; progress sign-off is not revenue recognition | SRS v2.0 §3.1 |
| No public files for customer documents | SRS v2.0 §8 |

## 2. BOQ revisions (`Sidra BOQ Revision`, SBR-YYYY-)

- A draft copies the job's current BOQ and stores the approved revision it was based on.
- The Sidra Project Manager approves it by submitting. Approval is refused when:
  - another revision was approved after this draft was made (a stale draft);
  - the draft changes nothing;
  - the job is Closed or Cancelled.
- Approval numbers the revision (1, 2, …), stores the previous total and the difference, and copies the lines to the job.
- From the first approved revision on, the job's BOQ can't be edited directly. It changes only through a new revision.
- An approved revision is never cancelled. To change it, approve a new revision. History is kept.

## 3. Variation orders (`Sidra Variation Order`, SVO-YYYY-)

- **Type:** Addition (raises the value) or Omission (lowers it). The amount is entered as a positive number.
- **Client approval is required before submitting:**
  - who approved for the client, and the date (not in the future);
  - the client's signed approval, uploaded to this order's own field as a private file. The same rule as the sale contract's signed copy.
- **Second approver:** the person who raised the order can't submit it. A Sidra Project Manager or the Sidra General Manager approves.
- **Job conditions:** the job must be Contracted, In Progress, On Hold, Completed or Defects Period, and must have its **original contract value** entered.
- **Contract value:** the current contract value is the original contract value plus all approved orders, and can't go below zero. Cancelling an order is refused if it would push the value below zero.
- **On the job:**
  - *Approved Variations* and *Current Contract Value* are always recalculated from submitted orders.
  - The *Original Contract Value* is locked once any order is approved.
- **Optional link:** an approved BOQ revision of the same job.
- **Recorded only:** no Sales Order amendment, invoice or posting.

## 4. Inspection reports (`Sidra Inspection Report`, SIR-YYYY-)

- **Content:** date (not in the future), inspector, optional stage (must be one of the job's stages), checklist rows, overall result, defects, next action and due date, photos.
- **Consistency rules:**
  - A failed checklist row needs remarks.
  - A report with a failed row can't have the overall result Pass.
  - Pass with defects and Fail need a description of the defects and a next action.
  - The next action can't be due before the inspection date.
- **Photos** must be private files.
- **Approval:** the Sidra Inspector submits. The Project Manager can prepare drafts but can't submit.
- **Effect:** a submitted report changes nothing on the job and doesn't certify a stage.

## 5. Stage certification (on `Sidra Project Stage`)

- The Sidra Project Manager uses **Certify Stage** on the job (`certify_stage`). It needs a stage that is:
  - Completed;
  - 100 % complete;
  - with an actual end date that isn't in the future.
- Certification records who certified and when. The job must not be Closed or Cancelled.
- **After certification:**
  - the stage's dates, percentages, status and engineer can't be changed;
  - the row can't be removed;
  - the certification fields can't be set or cleared through an ordinary save.
- Certification is a record of completion. It creates no invoice and recognises no revenue (SRS v2.0 §3.1; CON-07 is P2).
- There is no un-certify action in this version.

## 6. Permissions

| DocType | Create / edit draft | Approve (submit) | Cancel | Read only |
| --- | --- | --- | --- | --- |
| BOQ Revision | Project Manager | Project Manager | never | General Manager, Finance Reviewer, Inspector, System Manager |
| Variation Order | Project Manager | Project Manager (not the person who raised it), General Manager | Project Manager, General Manager | Finance Reviewer, System Manager |
| Inspection Report | Inspector, Project Manager | Inspector | Inspector | General Manager, System Manager |

Each record takes its Company and customer from the job. Creating or editing a record needs access to the job, so a Company User Permission on the job also limits the new records.

## 7. Choices to confirm

These follow the sources above. They're listed so management can confirm or change them, in issue [#37](https://github.com/mohamoudabdullahi1988-maker/sidra-erp/issues/37) (`spec-question`):

1. Omissions are allowed and can't take the contract value below zero.
2. The second-person rule applies to variation orders. The General Manager can be the second approver.
3. The original contract value is entered on the job until CON-03 (quotation to contract) exists, and is locked after the first approved variation.
4. Certification doesn't require a passed inspection report, and there is no un-certify action.
5. BOQ revisions need no second approver and are never cancelled.
