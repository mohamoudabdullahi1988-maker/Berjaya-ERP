# Construction jobs on ERPNext Projects v0.1

25 Nov 2026 · Implements decision G37 (`docs/DECISIONS-AND-GATES_v0.3.md`). Recorded by Claude Code.

## Mapping

| Sidra record | ERPNext record | Link |
| --- | --- | --- |
| Sidra Construction Job (one house or job) | **Project** | Job `project` ↔ Project `sidra_construction_job` |
| Each row of the job's Stages table | **Task** in that Project | Task `sidra_construction_job` and `sidra_job_stage` (the row id) |
| Signed terms: stage Billing % and milestone amount | Task `sidra_billing_pct`, `sidra_milestone_amount` (read-only copies) | from the job |
| Stage certification (Project Manager) | Task `sidra_certified`, `sidra_certified_by`, `sidra_certified_on` (read-only copies) | from the job |
| BOQ, BOQ revisions, variation orders, inspection reports, risks, quotations | unchanged; reached from the job | job name on the Task and Project |

Task fields copied from the stage: subject (`<n>. <stage name>`, as recorded; no labels are invented), expected start and end (planned dates), actual start and end, progress (completion %), and status (Planned → Open, In Progress → Working, Completed → Completed, removed stage → Cancelled). The Project's % complete uses **Task Progress**, the simple average of stage completion (G30). The Project's expected dates span the contract and stage dates and widen when a stage moves outside them, because ERPNext refuses Task dates outside its Project.

## Site store per house (G42, 25 Nov 2026)

Each job also gets its own ERPNext **Warehouse** (job field *Site store*; Warehouse field `sidra_construction_job`) under the Company's *Construction sites* group, made with its Project. Material Requests to it work now. Ledger-posting stock moves into or out of it are refused until Finance approves the stock accounts. Jobs that already have a Project: Create → Site store, or `bench --site <site> execute sidra_realestate.services.construction_stores.backfill_site_stores`.

## Rules

- **The job stays the record.** Contract terms, Billing % milestones, certification and their controls (G11) live on the job. Tasks mirror the job one way, on every save of the job. An edit made on a Task in Desk is overwritten at the job's next save.
- **Created on request only.** "Create → Project" on a job in Desk (`create_project`) builds the Project and Tasks. It needs write access to the job and permission to create Projects and Tasks (role profile *Sidra Project Staff*: Sidra Project Manager + Projects User). Closed or cancelled jobs, jobs without stages and jobs already linked are refused.
- **No live record is converted automatically.** A job that was already linked to a Project by hand keeps it, and that Project's Tasks are not touched (only Projects created by this app carry `sidra_construction_job`).
- **No money moves.** No invoice, payment, journal or ledger entry is created. Finance's review of a stage-dependent payment stays separate from certification (G37, G11).

## Finance review of a stage payment

Finance (Sidra Finance Reviewer) already reads the construction job. For a stage, the evidence is on the job: the signed quotation and contract dates, the stage's Billing % and milestone amount, its certification (who, when) and the inspection reports for the job (the site supervisor's evidence). The Project and its Tasks give the same milestone and certification values next to the schedule for those with Projects access. Finance roles are not given Project or Task access by this change.

## Adoption path for existing jobs

1. Deploy and migrate (adds the custom fields on Project and Task).
2. For each live job, the Project Manager checks the stages and planned dates on the job, then presses Create → Project. Jobs with a hand-made Project are reviewed case by case first.
3. Plan in the job; read the schedule in Projects (Gantt, Kanban, Project % complete).

## Open

- Standard stage labels (G37): stages keep the names recorded on each job.
- Investor-fund tracking and separate stores per house: not covered here.
- A Berjaya button for "Create Project" belongs to the Berjaya frontend (Codex); the server method is `sidra_realestate.services.construction_projects.create_project` (POST, `job`).
