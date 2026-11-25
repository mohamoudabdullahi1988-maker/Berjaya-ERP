# Berjaya workspace decision and work split v0.5

25 Nov 2026 · Approved direction from Mohamoud Abdullahi Sheikh. The [delivery handover v0.3](DECISIONS-AND-GATES_v0.3.md), [Finance decision v0.4](DECISIONS-AND-GATES_v0.4.md), and existing business gates apply.

## G39 · Staff dashboards and transaction workflow

Executive, Construction, Real Estate, Finance and the other shared Berjaya workspaces show figures from their authorized live sources. A workspace without an implemented live source displays an unavailable state. Investment has a labelled fictional funding demonstration with its own figures. It is isolated from shared dashboard figures and from ERPNext records.

Berjaya provides an ERPNext Desk link in the shared header. Workflow opens in a window from an individual saved transaction, such as a sale contract, reservation, quotation or construction job. Lists, workspace dashboards and setup pages do not display the previous workflow drawer.

## Work split

| Owner | Branch | Scope |
| --- | --- | --- |
| Codex | `feature/berjaya-live-workspaces` | Berjaya Vue workspaces, workflow window, shared Desk entry and the fictional Investment presentation. |
| Claude Code | `feature/desk-native-data-audit` | Verify test-site Company and role visibility for native ERPNext Sales records, Assets, Projects and Tasks. Populate authorized fictional records through the existing test-site guards and adopt fictional Construction jobs through the existing ERPNext Project and Task mapping. [Native Desk handoff](https://github.com/mohamoudabdullahi1988-maker/Berjaya-ERP/issues/15) |

The existing construction bridge creates native Projects and Tasks when a Project Manager links a job. Deployment and migration add the link fields and availability of that action. Existing jobs need to be adopted before those native records are visible in Desk. [Construction mapping](CONSTRUCTION-PROJECTS_v0.1.md)
