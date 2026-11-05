# Sidra ERP — Environment v0.1

5 Nov 2026 · pinned versions for development, CI and staging (handoff v2.0, first PR checklist).

| Component | Version | Note |
| --- | --- | --- |
| Frappe Framework | v16.55.2 | Latest v16 patch release on 5 Nov 2026 |
| ERPNext | v16.53.0 | Latest v16 patch release on 5 Nov 2026; requires Frappe >= 16.50.0 |
| Python | 3.14 | Frappe v16 requires `>=3.14,<3.15` |
| Node.js | 24 | Frappe v16 `engines.node >= 24` |
| MariaDB | 11.8 | CI uses the `mariadb:11.8` image; local development may use 10.11 |
| Redis | 7 | Cache and queue |
| bench CLI | `frappe-bench` from PyPI | |

Change a pin only in a PR that records why and re-runs the bench tests.

## Server prerequisites (staging)

Ubuntu 24.04 VPS, 4 GB RAM minimum, MariaDB with `utf8mb4` / `utf8mb4_unicode_ci`, Redis, Node 24 with yarn, wkhtmltopdf 0.12.6 (patched Qt) for print formats, HTTPS. Staging and production are separate sites with separate credentials and backups (SRS v2.0 section 2.2).

## Local bench

```bash
bench init --frappe-branch v16.55.2 --python python3.14 frappe-bench
cd frappe-bench
bench get-app --branch v16.53.0 erpnext
bench get-app sidra_realestate <path or URL of this repository>
bench new-site sidra.local --mariadb-root-password <root password> --admin-password <admin password>
bench --site sidra.local install-app erpnext sidra_realestate
bench --site sidra.local set-config allow_tests true
bench --site sidra.local run-tests --app sidra_realestate
```
