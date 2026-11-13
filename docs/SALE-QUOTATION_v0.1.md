# Sidra ERP — Sale Quotation v0.1

**Version:** 0.1 (12 Nov 2026) · **Status:** implemented for review · **App version:** 0.1.12
**Scope:** P1 sales item from SRS v2.0 §3.2 and §7: a sale quotation showing the cash and installment options side by side.
**Requirement:** SAL-05.
**Not in scope:** turning a quotation into a contract, reserving the plot, receipts, and any posting (`CLAUDE.md` rule 3).

## 1. Sources for each rule

| Rule | Source |
| --- | --- |
| A sale quotation for cash or installment, showing both options side by side | SAL-05 |
| The Sales Officer prepares sale quotations | SRS v1.6 §2 |
| Discounts need a second person: Sales Manager within a limit, General Manager above | SRS v1.6 §2 |
| The installment price varies by deal; the cash price is always recorded beside it | SRS v1.6 §13 |
| No markup formula; contracts are priced at the agreed price | G3 |
| Installment terms are configurable, including 12 to 36 months | G1 |
| The six decisions below | G13 (Mohamoud, 12 Nov 2026) |

## 2. The quotation (`Sidra Sale Quotation`, SSQ-YYYY-)

**What it is**
- An offer for one or more units of one Company, for one customer.
- It reserves nothing, changes no unit, creates no contract and posts nothing.

**Units**
- A unit can be quoted when it is Available, or Reserved for the same customer.
- Each unit must have a listed price. The listed price is the unit's price in force. It is re-read on every draft save and frozen when the quotation is issued.

**Cash option**
- The cash price is the listed price by default.
- It can be lower, which is a discount (see §3). It can't be above the listed price.

**Installment option (G13)**
- **Price:** entered per unit on each quotation. It can't be below the listed price.
- **Terms:** from the chosen contract profile, which must be active and not on legal hold. Down payment, due day and grace months come from the profile unchanged.
- **Months:** start from the profile and can be set from 12 to 36.
- **Schedule:** indicative. It assumes the contract is signed on the quotation date, and uses the same rules as contract schedules (whole-dollar installments, the last one takes the remainder).

**Validity (G13)**
- Valid for 7 days from the quotation date unless the officer changes it.
- The quotation date can't be in the future. It can't be issued after its valid-until date.
- A daily job marks issued quotations Expired after that date.

**Print**
- The *Sidra Sale Quotation* print format shows the Sidra Homes letterhead, the units, the two options side by side and the indicative schedule.
- It states that the quotation doesn't reserve the unit and isn't a contract or a receipt.

## 3. Discounts (G13)

- The discount is measured **per unit against its listed price**.
- **Up to 5 %:** a Sales Manager approves. **Above 5 %:** only the General Manager. The General Manager may approve any discount.
- The person who prepared the quotation can't approve its discount.
- A quotation with a discount can't be issued until the discount is approved (`approve_discount`).
- Changing a unit, a cash price or a listed price clears the approval. Other changes, such as notes, keep it.
- The approval fields can't be set through an ordinary save.

## 4. Permissions

| Action | Who |
| --- | --- |
| Prepare and issue | Sales User, Sales Manager |
| Approve a discount | Sales Manager (up to 5 %), General Manager (any); never the preparer |
| Cancel an issued quotation | Sales Manager |
| Read | General Manager, Finance Reviewer, System Manager |

Preparing a quotation needs read access to the Customer and to each unit.

## 5. Limits to know

1. A quotation doesn't become a contract automatically. The contract is drafted separately.
2. A contract generated from a profile uses the profile's own number of months. A quotation with a different number of months can become a generated contract only once contract overrides exist (handoff "Subsequent PRs" item 3, not built yet). It can be registered as an external contract today.

## 6. Changing these rules

The 5 % limit (`SM_DISCOUNT_LIMIT_PCT`), the 12 to 36 month range and the 7 valid days are constants in `sidra_realestate/services/quotation.py`. They change only with an approved spec version (`CLAUDE.md` rule 2).
