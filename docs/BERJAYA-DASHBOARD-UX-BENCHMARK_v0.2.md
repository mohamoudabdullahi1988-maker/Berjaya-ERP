# Berjaya Dashboard UI/UX Benchmark — v0.2

| Item | Detail |
| --- | --- |
| Document | `docs/BERJAYA-DASHBOARD-UX-BENCHMARK_v0.2.md` |
| Version | v0.2 (28 Nov 2026) — moved from the retired `sidra-erp` repository |
| Status | Findings and work items for implementation; scores are review input, not acceptance |
| Reviewed | Live instance `http://5.253.233.218/berjaya`, signed in as Administrator, Company **Sidra Homes** |
| Screens | `/berjaya/` (front page), `/berjaya/executive` (Executive overview), `/berjaya/dashboard` (Live dashboard, General Manager view), `/berjaya/?view=overdue`, login |
| Benchmarks | Odoo 18/19 Dashboards, NetSuite role dashboards, Dynamics 365 Business Central Role Centers, Frappe CRM / Helpdesk |
| Shared doc | Berjaya ERP Dashboard UI/UX Benchmark v0.1 (Claude Docs) — full narrative and chart |
| Approver | Mohamoud Abdullahi Sheikh |

## 1. Score

Berjaya scores **49.5 / 100**. The benchmarks score 70.5–78.5 (indicative, from vendor documentation).

| # | Criterion | Weight | Berjaya | Benchmark avg |
| --- | --- | --- | --- | --- |
| 1 | Information architecture and entry point | 10 | 4 | 8.0 |
| 2 | KPI selection and hierarchy | 15 | 5 | 7.25 |
| 3 | Data consistency and trust | 15 | 3 | 8.0 |
| 4 | Actionability and drill-down | 10 | 6 | 8.0 |
| 5 | Visual design and brand consistency | 10 | 5 | 7.5 |
| 6 | Data visualisation quality | 10 | 5 | 6.75 |
| 7 | Copy and microcopy | 5 | 3 | 7.5 |
| 8 | Filters, period and context | 5 | 6 | 7.5 |
| 9 | Accessibility | 10 | 5 | 6.75 |
| 10 | Performance and responsiveness | 10 | 8 | 7.75 |

Overall = Σ(score × weight) / 10. Projected after Phase 1: 59.0; Phase 2: 70.0; Phase 3: 76.0.

Decision recorded 28 Nov 2026 (Mohamoud): **General Manager is the first role home page.**

## 2. Before you start

- **Where each screen lives** (`frontend/src/router.js` on `develop`): `/` → `pages/DeliveryDashboard.vue` (report cards + transaction buttons); `/executive` → `pages/Showcase.vue` fed by `showcase/live.js`; `/dashboard` → `pages/Dashboard.vue` (Live dashboard, data from `api/staff_dashboard.py`).
- Follow `CLAUDE.md`, `AGENTS.md`, `docs/DECISIONS-AND-GATES_v0.5.md` (G39 and the work split) and `docs/DECISIONS-AND-GATES_v0.2.md` (financial gates). Where an item below conflicts with an approved decision, the decision wins and the item is marked **Needs decision**. One `feature/berjaya-ux-<item>` branch per work item from `develop`, PR into `develop`, CI green. Keep version and `CHANGELOG.md` in step.
- Do not change money logic, posting, penalties or the meaning of any figure. Where a fix needs a definition (for example which jobs count as "active"), open a `spec-question` issue and propose labels instead of guessing.
- Financially restricted users must still see **"unavailable"**, never zero or a partial sum.

## 3. Ownership (parallel-safe)

The v0.5 work split gives Codex the Berjaya dashboard, report queries and transaction shortcuts. On 28 Nov 2026 Mohamoud asked for this list to be worked by both Claude Code and Codex, so it is split into two lanes that touch different files. If Mohamoud reassigns, change this table.

| Lane | Owner | Files |
| --- | --- | --- |
| A — dashboard data (server) | Codex | `sidra_realestate/api/staff_dashboard.py`, `executive_dashboard.py`, `construction_live.py`, `realestate_live.py`, `finance_live.py`, `crm_live.py`, `live_period.py` and their tests |
| B — dashboard UI (client) | Claude Code | `frontend/src/pages/DeliveryDashboard.vue`, `frontend/src/pages/Dashboard.vue`, `frontend/src/showcase/**`, `frontend/src/router.js`, `frontend/src/tokens.css`, `frontend/src/components/**`, `frontend/tests/**` |

A lane that needs a change in the other lane's files opens an issue and links it; it does not edit them.

## 4. Work items

Status values: `Open`, `In progress`, `In review`, `Done`. Update this table in each PR.

| ID | Phase | Lane | Title | Status |
| --- | --- | --- | --- | --- |
| UX-01 | 1 | A | One source per measure across Executive and Live | Open |
| UX-02 | 1 | A | Collection rate obeys the period and hides on zero receipts | Open |
| UX-03 | 1 | A | Latest contracts sorted by signed date | Open |
| UX-04 | 1 | A | One attention row per job | Open |
| UX-05 | 1 | A+B | Remove staging/developer wording from user text | Open |
| UX-06 | 1 | B | Contrast and colour fixes (tiles, Leads donut) | Open |
| UX-07 | 2 | B | `/berjaya` = General Manager role home with figures | Needs decision |
| UX-08 | 2 | B | One visual style for tiles and charts | Open |
| UX-09 | 2 | A+B | One period control for the whole page | Open |
| UX-10 | 2 | A+B | KPI targets and RAG state | Open |
| UX-11 | 2 | B | Lighter Desk entry on phones | Needs decision |
| UX-12 | 3 | A+B | Needs attention → My work with owner and actions | Open |
| UX-13 | 3 | A | Overdue installments: fill or drop empty columns; add days overdue | Open |
| UX-14 | 3 | B | Sales vs receipts as paired monthly bars | Open |
| UX-15 | 3 | B | Remove nested scroll areas; 44 px touch targets | Open |

### Phase 1 — trust and wording (land before the Sidra demo)

**UX-01 — One source per measure.**
Evidence (28 Nov 2026):

| Measure | Executive `/berjaya/executive` | Live `/berjaya/dashboard` |
| --- | --- | --- |
| Construction jobs | Active construction jobs 18 (table: 25 jobs) | Open construction jobs 25; Contracted or in progress 18 |
| Overdue stages | Overdue construction stages 57 | Overdue construction milestones 41 |
| Attention items | 35 recorded attention items | 41 recorded exceptions |
| Leads | Leads 30 (period Last 12 months) | New leads, this month 30 |

Acceptance: each measure is computed by one server function and both screens call it; where two figures differ on purpose, labels say how ("Open jobs (all)" / "Jobs on site"); an integration test asserts Executive and Live return equal values for the same company and period.

**UX-02 — Collection rate.** Live shows Collection rate 40.4% next to Received this month USD 0.00 and Posted receipts USD 0.00. Acceptance: the rate uses the selected period or states its own window in the label; when receipts in the window are zero the tile shows "No receipts in period" instead of a percentage; test covers the zero case.

**UX-03 — Latest contracts.** `staff_dashboard.py` orders the contract list by `modified desc`, so SSC-2026-00064 (signed 13 Feb 2026) shows above SSC-2026-00057 (signed 13 Sep 2026). Acceptance: order by `signed_on desc, name desc`; unsigned drafts excluded or listed after signed contracts; test asserts the order.

**UX-04 — One attention row per job.** Live "Needs attention" repeats SCJ-2026-00014 three times and SCJ-2026-00011/00012 twice (one row per overdue month). Acceptance: one row per job with the count of overdue stages and the oldest planned date; total count matches UX-01's overdue figure.

**UX-05 — User-facing wording.** Remove from rendered text: "Fictional", "staging", "fully permitted", "native Receive Payment Entries", "readable source contracts … inaccessible/inconsistent unit allocations", "An approved project baseline is not inferred". Move needed caveats into an (i) tooltip of at most 15 words. Show snapshot time as "As at 28 Nov 2026, 12:04" (Executive currently prints `2026-11-28T12:04:22+03:00`). Acceptance: a browser test fails if any of those strings appears on `/berjaya/executive` or `/berjaya/dashboard`. Demo names "SHP … Pilot" are replaced before the client demo (data task; coordinate with `docs/PILOT-DEMO_v0.1.md` owner). Lane split: most of these strings come from the server (`api/executive_dashboard.py`, `api/finance_demo_snapshot.py`), so Lane A changes the returned text and Lane B the tooltip, date format and browser test.

**UX-06 — Contrast and colour.** White 12 px labels on `--bj-c-green` #2a8f57 (4.07:1), `--bj-c-teal` #0e8a80 (4.23:1), `--bj-c-sky` #2381bd (4.25:1), `--bj-c-rose` #d64561 (4.30:1) fail WCAG AA 4.5:1 (`frontend/src/tokens.css`). The Leads donut sets `tone: 'blue'` on every segment (`frontend/src/showcase/live.js`, Leads by status). Acceptance: every text/background pair on tiles ≥ 4.5:1 (add a unit test over the token pairs); donut segments use distinct tones and show labels or a legend, so colour is not the only signal.

### Phase 2 — one role home page

**UX-07 — General Manager role home at `/berjaya`.** **Needs decision:** G39 keeps Executive as a live workspace, so merging it away needs Mohamoud's approval; open a `spec-question` with this proposal first. Proposal: `DeliveryDashboard.vue` (`/`) shows 4–6 headline KPIs above its report cards for General Management users: Units available, Contracts signed (period), Collections received (period) vs due, Overdue balance, Jobs overdue. The Live dashboard (`/dashboard`) is folded into Executive so there is one figures page, not two. Acceptance once approved: first load at `/berjaya/` shows figures for GM users; `/berjaya/dashboard` redirects to Executive; other roles keep their current landing.

**UX-08 — One visual style.** Executive uses eight saturated tile colours; Live uses white cards with uppercase labels. Acceptance: one tile component; neutral cards with charcoal text; colour only for status (completed / current / blocked / pending tokens) and the terracotta brand accent; charts use brand tokens.

**UX-09 — One period control.** Executive offers This month / Last 3 months / This year / Last 12 months / Custom but its totals cap at 90 days; Live offers This month / Last 30 days / Last 90 days. Acceptance: one control drives every period-based figure via `live_period.py`; figures that are point-in-time (inventory) say "Current" in the label.

**UX-10 — Targets and RAG.** Acceptance: each headline KPI can carry a target and thresholds (settings DocType or app settings; values supplied by Sidra management — open a `spec-question` for the numbers); tile shows value, target and green/amber/red state; prior-period change shown where a period applies.

**UX-11 — Desk entry on phones.** **Needs decision:** G39 places the ERPNext Desk link in the shared header, and "Construction projects" (`DeliveryDashboard.vue`, shown when `boot.can_open_projects`) deliberately opens native Projects in Desk. Keep both. Proposal only: on phone widths, show Desk as an icon button so it is no longer the largest top-bar control, and keep the Berjaya wordmark visible. Acceptance once approved: header at 375 px shows wordmark, search, notifications, Desk icon and sign-out without wrapping.

### Phase 3 — act on exceptions

**UX-12 — My work.** Every Live exception reads "Owner not assigned" and offers only "Review record". Acceptance: attention items resolve an owner (assigned user or responsible engineer); actions Assign, Snooze (with date) and Resolve use native assignments/ToDo; opening an item goes to the saved record, where its workflow window is available (G39: dashboards do not show the workflow drawer).

**UX-13 — Overdue installments view.** Agreement and Term columns are "—" on every row. Acceptance: link invoices to their agreement and payment term where the data exists, otherwise drop the columns; add Days overdue and sort by it descending.

**UX-14 — Sales vs receipts.** Live "Last six months" is a text list. Acceptance: paired monthly bars (signed sales, received) with the current month marked partial.

**UX-15 — Scroll and touch.** Units by project, the map plot list and Needs attention scroll inside the page; on a 375 px phone 53 links/buttons are under 32 px tall. Acceptance: no nested vertical scroll areas on the home page (use "Show all" links); interactive targets ≥ 44 px on phone widths; browser test at 375×812.

## 5. Measurements (28 Nov 2026)

| Measurement | Value |
| --- | --- |
| Executive load / DOM ready | 0.88 s / 0.60 s |
| Requests / transferred | 15 / ~40 KB |
| API calls | get_dashboard 404 ms, get_construction_live 258 ms, get_realestate_live 309 ms |
| Console errors | 0 |
| Live dashboard length | 4,032 px (4.5 screens), 977 words |
| Phone (375 px) | No horizontal scroll; 53 targets < 32 px |

Keep load under 2 s after these changes.

## 6. Benchmark patterns to reuse

- Dynamics 365 Business Central — Role Center: one home per role; Cues (counts) and Headlines.
- NetSuite — KPI meters with thresholds; one dashboard-wide date setting; Reminders portlet.
- Odoo 18 — global filters per dashboard; access by user group; live drill-down from chart points.
- Frappe CRM — Frappe UI / Espresso components for a single consistent style.

## Change log

| Version | Date | Change |
| --- | --- | --- |
| v0.2 | 28 Nov 2026 | Moved to Berjaya-ERP (sidra-erp retired). File references re-checked against `develop` 0.1.76; deployed-build note resolved (`/` is `DeliveryDashboard.vue`); UX-07, UX-11 and UX-12 aligned with G39; ownership note added; UX-05 is A+B (its wording comes from server files) |
| v0.1 | 28 Nov 2026 | First issue in sidra-erp (PR #110, closed): scores, findings, work items UX-01 to UX-15 |
