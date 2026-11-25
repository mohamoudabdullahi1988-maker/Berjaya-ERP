# AGENTS.md — Berjaya-ERP

Instructions for Codex and other coding agents in this repository. Start with [the 24 Nov 2026 delivery decision and work split](docs/DECISIONS-AND-GATES_v0.3.md). Codex owns the Berjaya dashboard, reports and transaction shortcuts. Claude Code owns Desk access and ERPNext Projects for Construction.

Follow [CLAUDE.md](CLAUDE.md) for the shared rules and commands. Read [v0.2](docs/DECISIONS-AND-GATES_v0.2.md) for existing decisions and financial gates.

Scoped user authorization (9 Nov 2026): populate fictional financial reports and dashboards. On an explicitly marked test site, the guarded finance demo loader targets the Company **Sidra Homes** (decision G14, 12 Nov 2026; `docs/FINANCE-DEMO_v0.2.md`). On that site the dataset is the twelve-month pilot set of `docs/PILOT-DEMO_v0.1.md` (decision G16, 13 Nov 2026), loaded by the same guards. It remains Administrator-only, requires the three staging flags, and refuses any Company holding GL entries its own manifest does not own. Production posting gates are unchanged; ERPNext remains the only ledger. This does not authorize production contract posting, refunds, penalties or a new accounting policy.

## Product and client names (decisions G17–G19, 13 Nov 2026)
Users see **Berjaya** as the software and **Sidra** as the company using it. Test for any string: does it name the software or the business?
- Software (application branding, navigation, login screens, page titles, help text, product documentation) → **Berjaya**. Take the name from `sidra_realestate/branding.py`; do not scatter the literal.
- Business (company records such as Company **Sidra Homes**, contracts, invoices, receipts, statements, letterheads) → **Sidra**. Never renamed, merged or rebranded.
- Internal identifier a user does not read as branding (app `sidra_realestate`, site `sidra.local`, `sidra_*` flags, DocType, field and role names, naming series such as `SSC-…`, routes, the repository) → unchanged.

Before starting, check open pull requests and branches from Claude Code, and continue the unfinished one instead of starting over. Merge into `develop` only when CI is green (decision G6).
