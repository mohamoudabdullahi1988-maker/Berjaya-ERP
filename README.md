<p align="center"><img src="sidra_realestate/public/images/berjaya-wordmark.png" alt="Berjaya" width="320"></p>

# Berjaya — ERPNext app (`sidra_realestate`)

Custom Frappe app that runs Sidra Homes' business on **ERPNext v16**: land and house sales, Murabaha / installment contracts with configurable contract profiles, title transfer tracking, construction projects (full build, design, inspection) and land brokerage.

Current version: **v0.1.1** (Phase 0 skeleton and handover — no DocTypes yet).

## Documents

| File | What it is |
| --- | --- |
| [CLAUDE.md](CLAUDE.md) | Standing instructions for Claude Code |
| [docs/HANDOVER_v1.0.md](docs/HANDOVER_v1.0.md) | Handover to Claude Code: roles, rules, decisions, plan, acceptance cases, first tasks |
| [docs/SREMS-SRS_v1.6.md](docs/SREMS-SRS_v1.6.md) | Requirements specification v1.6 (business rules, contract profiles, decisions) |
| [docs/ERPNEXT-MAPPING_v0.1.md](docs/ERPNEXT-MAPPING_v0.1.md) | Which ERPNext feature covers each requirement, and what this app adds |
| [CHANGELOG.md](CHANGELOG.md) | Release history |

## Requirements

| Item | Version |
| --- | --- |
| Frappe Framework / ERPNext | v16 (branch `version-16`) |
| Python | 3.14 |
| Node.js | 24 |
| MariaDB | 11.8 |
| Redis | 6+ |
| wkhtmltopdf | 0.12.6 (patched Qt) |

## Install on a bench

```bash
# 1. Bench with Frappe v16 and ERPNext
bench init frappe-bench --frappe-branch version-16 --python python3.14
cd frappe-bench
bench get-app --branch version-16 erpnext
bench new-site sidra.local
bench --site sidra.local install-app erpnext

# 2. This app (private repository: use an SSH key or a GitHub token)
bench get-app git@github.com:mohamoudabdullahi1988-maker/sidra-erp.git
bench --site sidra.local install-app sidra_realestate
bench --site sidra.local migrate
```

For development, turn on developer mode so new DocTypes are written into this app's folders:

```bash
bench --site sidra.local set-config developer_mode 1
bench --site sidra.local clear-cache
```

## Repository layout

```
sidra-erp/
├── sidra_realestate/
│   ├── hooks.py               App settings, fixtures, document events, scheduled jobs
│   ├── modules.txt            The five Sidra modules
│   ├── patches.txt            Data patches between versions
│   ├── sidra_property/        Schemes, property units, reservations, title transfer
│   ├── sidra_sales/           Sale contracts, contract parties, clause library
│   ├── sidra_installments/    Contract profiles, pricing, schedules, penalties
│   ├── sidra_construction/    Site inspections, variation orders, site diary
│   ├── sidra_brokerage/       Brokerage listings, land verification requests
│   ├── config/                Desk configuration
│   ├── public/                CSS / JS assets
│   ├── templates/             Jinja templates (print formats, portal pages)
│   └── www/                   Customer portal pages
├── docs/                      Specification and ERPNext mapping (versioned file names)
├── .github/workflows/ci.yml   Lint and syntax check on every push
├── pyproject.toml
├── CHANGELOG.md
└── license.txt
```

## Working rules

- Never edit ERPNext or Frappe core. Every change lives in this app: DocTypes, Custom Fields, Property Setters, hooks, fixtures.
- Branches: `main` = released, `develop` = integration, `feature/<module>-<item>` for each piece of work.
- Every release to `main` is tagged (`v0.1.0`, `v0.2.0` …) and listed in `CHANGELOG.md`.
- Documents in `docs/` carry their version in the file name; a revision adds a new file version and a changelog line.
- No secrets in the repository: site config, API keys and WhatsApp tokens stay on the server.

## Roadmap

Phase order agreed 5 Nov 2026 (see handover section 5).

| Release | Phase | Scope |
| --- | --- | --- |
| v0.1.x | 0. Foundation | Skeleton, environment, roles, accounts, Modes of Payment (Cash, Bank, ZAAD, eDahab) |
| v0.2.0 | 1. Property | Schemes, property units, reservations, price history |
| v0.3.0 | 2. Sales | Contract profiles A / B, sale contracts, clauses, terms snapshot, Somali / English print format |
| v0.4.0 | 3. Collections | Installment schedules, receipts, penalties, customer statements |
| v0.5.0 | 4. Construction | Projects, stages, BOQ, variations, project costs |
| v0.6.0 | 5. Finance | Approved ERPNext financial integrations |
| v1.0.0 | 6. Release | Gap assessment, fixes, deployment |

Roles: ChatGPT owns architecture, specifications and review; Claude Code owns implementation and tests; Mohamoud / Sidra management approve.
