# Sidra Real Estate — ERPNext app (`sidra_realestate`)

Custom Frappe app that runs Sidra Homes' business on **ERPNext v16**: land and house sales, Murabaha / installment contracts with configurable contract profiles, title transfer tracking, construction projects (full build, design, inspection) and land brokerage.

Current version: **v0.1.0** (Phase 0 skeleton — no DocTypes yet).

## Documents

| File | What it is |
| --- | --- |
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

| Release | Phase | Scope |
| --- | --- | --- |
| v0.1.0 | 0 | Skeleton, roles, chart of accounts additions, Modes of Payment (Cash, Bank, ZAAD, eDahab) |
| v0.2.0 | 1 | Property units, sale contracts, contract profiles, installment schedules, Somali contract print format |
| v0.3.0 | 2 | Construction on Project / Task: inspections, variation orders, milestone billing, retention |
| v0.4.0 | 3 | Reports, workspace, dashboards |
| v0.5.0 | 4 | Customer portal, WhatsApp reminders and receipts |
| v1.0.0 | 5 | Import of live contracts from Excel, UAT, go-live |
