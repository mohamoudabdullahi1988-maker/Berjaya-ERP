# Sidra front page (shell) v0.1

13 Nov 2026. Decision G15 (Mohamoud): staff found three front doors confusing (the apps screen, the Desk and `/sidra-staff/`), and the product names ERPNext and Frappe mean nothing to them. The system gets **one front page** with four doors: Executive Dashboard, Financials, Real Estate Sales and Construction. Built by Claude Code inside this app; no third-party tool.

## What staff see

- **Address:** `/sidra`. Staff land on it after signing in.
- **Four doors**, each shown only to people who can use it:

| Door | Opens | Shown when the user |
| --- | --- | --- |
| Executive Dashboard | `/sidra-staff/` (unchanged) | is Sidra staff |
| Financials | General Ledger, Trial Balance, Profit and Loss, Balance Sheet, Accounts Receivable, Accounts Payable | can read ledger entries |
| Real Estate Sales | the sales workflow below | can read at least one of its steps |
| Construction | the construction workflow below | can read construction jobs |

- **Real Estate Sales workflow:** open leads → quotations issued → active reservations → contracts in draft → confirmed contracts → title transfers open. Waiting for action: buyer KYC to verify, title transfers overdue.
- **Construction workflow:** enquiries → quoted → contracted → in progress (with on hold) → completed (with defects period). Waiting for action: quotations in draft, and BOQ revisions, variation orders and inspection reports to approve.
- Each step shows a count and opens the matching list, already filtered. "New" buttons appear only for record types the user may create.
- The words ERPNext and Frappe do not appear on the page.

## Rules

- **Read-only.** The page changes no record and posts nothing (`CLAUDE.md` rule 3).
- **Counts are the user's own.** They come from permission-filtered lists, so Company and record restrictions apply. A step the user cannot read is left out; it is never shown as zero.
- **No new HTTP API.** The page is rendered on the server (`www/sidra`, `api/shell.py`); nothing is whitelisted. It is not cached.
- **Who gets in:** guests go to the login page. A signed-in person who is not Sidra staff goes to the desk they already have.
- The staff dashboard (`clients/staff`, Codex) is not changed; the shell links to it.

## How signing in lands here

- The app's entry on the apps screen now points to `/sidra`, with `/desk/sidra-sale-contract` as its door back into the desk.
- System Settings **Default App** is set to this app on install and migrate, **only when it is blank**. An administrator's own choice, and each user's own default app, are left alone.
- The Sidra menus inside the desk (Real Estate and Construction sidebars) are unchanged and appear whenever a Sidra record is open.

## Not in v0.1

- Brokerage has no door (decision of 13 Nov: two services).
- Financials opens the native reports. On production they stay mostly empty until the posting decisions are made.
- No per-Company switch on the page; counts cover every Company the user may see.
- The ERPNext and Frappe icons still exist on the apps screen for people who open it; staff are no longer sent there.

## Verification status

Frappe integration tests (`api/test_shell.py`) cover: the page renders for staff, guest and non-staff redirects, doors by permission, live counts and their links, an unreadable step being left out, and the sign-in route. The layout was checked in a browser with sample data at desktop and phone widths, light and dark. **Not checked:** the page on a running site, and the Desk's app icon behaviour with the new route.

Rollback: revert the code; set Default App back to blank in System Settings if wanted. No data changes.
