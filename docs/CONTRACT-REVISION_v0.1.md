# Sidra ERP — Contract Draft Revision v0.1

6 Nov 2026 · implementation note for review finding 5 (ChatGPT review of `develop` @ `cbce4f3`). Business decisions open in issue #11.

Spec basis: SRS v2.0-DRAFT §1.5 (prototype prohibits overrides and snapshots profile terms at contract creation), §3.2 (freeze terms and clauses → issue contract → attach signed copy), §3.3 (overrides must be versioned, not edited in place); INS-20, INS-21.

## 1. What is frozen, and when

| Moment | Frozen on the contract | Can change afterwards? |
| --- | --- | --- |
| First save of a draft | Profile link, terms snapshot, clause wording (Somali, English, title) | No. Changes need a revised draft (section 3). |
| Submit (signed and notarised) | Everything above, plus the installment schedule, the notary reference key and each clause's approval | Never. The contract cannot be edited or cancelled in this version. |

## 2. Clause approval is checked at signing

When a draft is saved, it records whether each clause was approved at that moment. That flag is for information only. When the contract is submitted, every clause is checked against the clause library as it is now:

| Library clause now | Wording vs the draft | Result |
| --- | --- | --- |
| Approved | Same | Submit allowed; the contract records the clause as approved |
| Approved | Different | Submit refused: "use Revise Draft" |
| Not approved (never, or withdrawn) | Any | Submit refused: "approved wording for clause(s) …" |

So:

- a clause the General Manager approves after the draft was saved unblocks that draft, as long as its wording didn't change;
- withdrawing approval blocks every draft that uses the clause;
- a signed contract keeps the wording and approval it was signed with.

## 3. Revise Draft

**Revise Draft** is a button on a draft contract, backed by the server method `sidra_realestate.sidra_sales.doctype.sidra_sale_contract.sidra_sale_contract.revise_draft`. It is available to anyone who can edit the draft.

1. A new draft is created with the same contract type, customer, company, contract date, units and prices, buyer agent, parties and notary details.
2. The new draft takes the profile's **current** terms and clause wording, because it is a new first save.
3. The signed copy is **not** copied: the revised contract is printed and signed afresh.
4. The old draft is left exactly as it was. Comments on both drafts link them ("Superseded by …" / "Revision of …").
5. A submitted contract cannot be revised.

Nothing is edited in place. That keeps to SRS v2.0 §3.3 ("versioned, not edited in place") without adding per-contract overrides, which the prototype prohibits.

## 4. Open decisions (issue #11)

- (a) Should a revision be a new draft number (as implemented), or keep the original number with a version counter?
- (b) Should a revision pick up changed **profile terms** (as implemented), or keep the original terms and refresh only the clause wording?
- (c) Who may revise: anyone with write access to the draft (as implemented), or Sales Manager only?
- (d) Should superseded drafts be closed automatically?
