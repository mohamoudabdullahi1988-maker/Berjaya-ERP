# Sidra ERP — Staging Deployment v0.1

6 Nov 2026 · private staging from `develop`. Pinned versions: `docs/ENVIRONMENT_v0.1.md`.

Status: **no staging server exists yet** (handover §8, open item owned by Mohamoud). Every step below was rehearsed end to end in a disposable container. That covered a fresh site, install, migrate, build, regional settings, demo data, real PDFs from the Chrome generator, and staff screens for each role, but it is not a hosted staging site. Section 6 lists what is still needed.

Boundaries on staging (CLAUDE.md, SRS v2.0 §3.4, §9):
- synthetic data only;
- Profile B stays on legal hold;
- no vouchers, payments, penalties, refunds or title transfer;
- the first-due-date rule stays as built until Mohamoud decides (issue #1).

## 1. Server

| Item | Requirement |
| --- | --- |
| Host | Ubuntu 24.04 VPS, 2 vCPU / 4 GB RAM / 40 GB disk minimum, reachable only by Sidra staff (VPN or IP allow-list) |
| Runtime | Python 3.14, Node 24 + yarn, MariaDB 11.8 (`utf8mb4` / `utf8mb4_unicode_ci`), Redis 7, `cron` |
| PDF | Chromium or Google Chrome, for the contract print format's `chrome` generator. Set `chromium_path`, or let Frappe download Chromium into the bench on first use. wkhtmltopdf is not needed for Sidra's print format. |
| Web | nginx + supervisor from `bench setup production`, HTTPS (Let's Encrypt) on a temporary subdomain until Sidra chooses a web address |
| Users | A non-root Linux user (for example `frappe`); `bench` refuses to initialise as root |
| Backups | `bench backup --with-files` daily, encrypted, with an off-server copy; a restore rehearsed before UAT (SRS v2.0 §2.2) |

## 2. Install

```bash
pip install frappe-bench
bench init --frappe-branch v16.55.2 --python python3.14 frappe-bench
cd frappe-bench
bench get-app --branch v16.53.0 https://github.com/frappe/erpnext
bench get-app --branch develop git@github.com:mohamoudabdullahi1988-maker/sidra-erp.git   # deploy key, read-only
bench set-config -g chromium_path "$(command -v chromium || command -v google-chrome)"
bench new-site <staging-site> --mariadb-root-password <from the server's secret store> --admin-password <generated>
bench --site <staging-site> install-app erpnext
bench --site <staging-site> install-app sidra_realestate
bench --site <staging-site> migrate
bench build --app sidra_realestate
bench --site <staging-site> execute sidra_realestate.site_setup.apply_regional_settings
bench --site <staging-site> enable-scheduler
sudo bench setup production <linux-user>
```

Install the app **after** ERPNext, as the rehearsal did. A fresh install also needs ERPNext's setup wizard (company, chart of accounts) before real use; the demo data below creates its own synthetic company instead.

Notes:
- `bench get-app` resolves short names through the GitHub API; use full URLs behind proxies.
- `install-app` and `migrate` create the Sidra roles (fixture), the Sidra role profiles, Profile A and Profile B (B on legal hold), and the five clause records (no wording). They also run the patches below.

| Patch | Effect |
| --- | --- |
| `v0_2.create_initial_unit_prices` | First price history entry for units priced before price history existed |
| `v0_2.set_notary_reference_keys` | Fills the unique notary key for signed contracts. Stops with a message if two signed contracts share a reference. |
| `v0_2.set_document_currency` | Sets `currency` on contracts and construction jobs from their Company |

## 3. Staff accounts

Give each person one Sidra **role profile** (created by install / migrate when missing; editable by an administrator afterwards), not bare roles. Each profile pairs a Sidra role with the ERPNext role its screens need, for example to look up a Customer:

| Role profile | Roles | Use |
| --- | --- | --- |
| Sidra Sales Staff | Sidra Sales User, Sales User | Reserve, draft contracts |
| Sidra Sales Management | Sidra Sales Manager, Sales User | Plus submit contracts, set prices, block units |
| Sidra General Management | Sidra General Manager, Sales User | Profiles, legal hold, clause approval |
| Sidra Project Staff | Sidra Project Manager, Projects User | Construction jobs |
| Sidra Inspection | Sidra Inspector, Projects User | Read construction jobs |
| Sidra Finance Review | Sidra Finance Reviewer | Read only; Finance assigns ERPNext accounting roles itself (SRS v2.0 §5) |

Restrict each user to their Company with a User Permission (Company) where Sidra runs more than one company.

## 4. Demonstration data (staging only)

```bash
bench --site <staging-site> set-config sidra_allow_demo_data 1
bench --site <staging-site> execute sidra_realestate.demo.create_demo_data
bench --site <staging-site> execute sidra_realestate.demo.export_pdfs --kwargs "{'folder': '/tmp/sidra-pdfs'}"
for u in demo.sales demo.manager demo.gm demo.pm demo.finance demo.outsider; do
  bench --site <staging-site> set-password "$u@example.com" "<per-user password from the secret store>"
done
```

The demo data is synthetic and safe to run more than once. It never runs unless `sidra_allow_demo_data` is set, so never set that on production. It creates:
- the company "Sidra Demo Homes", with thirteen half plots in scheme DEMO-HAGBAD and a future price change;
- a reservation;
- a signed Profile A contract for two plots at $11,000 (13 × $786 + $782);
- a signed contract on a demo profile with one clause marked **DEMO PLACEHOLDER** (not legal wording);
- a Profile B draft without a signed copy (Profile B has no legal hold since decision D4);
- six registered (External) contracts EXT-DEMO-0001 to 0006 on plots DEMO-H-007 to 013 for the contract capture demonstration (`docs/CONTRACT-CAPTURE_v0.3.md` §6.5), five confirmed by demo.manager and EXT-DEMO-0003 left as a draft because its schedule is $10 short;
- a construction job with BOQ lines and the full-construction stages;
- the users listed in the walkthrough below.

## 5. Demonstration checklist

| # | Who | Action | Expected |
| --- | --- | --- | --- |
| 1 | demo.sales | Sidra Unit DEMO-H-006 → **Reserve Unit** → customer, 7 days | Status Reserved; **Cancel Reservation** button; message shows the expiry date in DD/MM/YYYY |
| 2 | demo.sales | Reserve the same unit again | "Unit … is Reserved and cannot be reserved" |
| 3 | demo.sales | **Cancel Reservation** | Unit Available again |
| 4 | demo.manager | Open SSC for DEMO-HAGBAD-FULL | Signed; 14-line schedule, 13 × $786 and 1 × $782, due on the 5th |
| 5 | demo.manager | Submit the Profile B draft | Refused until the signed copy is uploaded (no legal hold since D4) |
| 6 | demo.manager | Print / PDF the clause contract | PDF in USD and DD/MM/YYYY; units with boundaries; schedule; parties with signature lines; the demo clause in both languages; notary reference |
| 7 | demo.manager | New draft → submit without uploading a signed copy, or with another contract's file URL | Refused |
| 8 | demo.pm | Construction job | Nine stages; BOQ total $3,309.00 |
| 9 | demo.outsider | Open a unit, call reserve via API | Not permitted (HTTP 403) |
| 10 | demo.gm | Approve a draft-only clause, then submit a draft that uses it | Submit allowed once the wording matches (docs/CONTRACT-REVISION_v0.1.md) |
| 11 | demo.manager | Open EXT-DEMO-0001 | Registered copy; 7 rows including two on 01/03/2025; total = amount due = $10,000; original attached; approved by demo.manager with date and time |
| 12 | demo.manager | Open EXT-DEMO-0002 | Confirmed with a $4.00 difference, stored in the frozen terms with the $5.00 tolerance |
| 13 | demo.manager | Submit EXT-DEMO-0003 | Refused: differs by $10.00, more than the limit of $5.00 |
| 14 | demo.manager | Open EXT-DEMO-0004 and EXT-DEMO-0005 | Contract B terms: $3,000 down recorded separately vs a Down payment row; 24 × $250 from 10/04/2026; penalty $100 after 15 days; title 20 days, $220 a month; nothing calculated |
| 15 | demo.manager | Open EXT-DEMO-0006 | Confirmed with no witnesses or notary (D5) |
| 16 | demo.sales | New Sidra Sale Contract (Source External): units, price, reference, months / due day / grace → save → **Fill Schedule** → edit a row → save | Rows kept as edited; totals and difference update; Fill Schedule again asks before replacing |
| 17 | demo.finance | Accounting reports for Sidra Demo Homes | No Sales Order, invoice, payment, journal or GL entry from any contract |

Rehearsal result (6 Nov 2026, container, Frappe v16.55.2 / ERPNext v16.53.0, MariaDB 10.11): items 1, 2, 4, 5, 6, 8 and 9 passed through the browser as the named users. Items 3, 7 and 10 are covered by the automated tests (`test_cancel_releases_unit`, `test_*signed_copy*`, `test_approving_clause_later_unblocks_existing_draft`).

## 6. Still needed for real staging (owner: Mohamoud / Sidra)

| Need | Why |
| --- | --- |
| A VPS or managed Frappe hosting account that Sidra already owns or authorises (nothing is purchased by the developer) | There is no staging host yet |
| A DNS name (temporary subdomain) and who controls DNS | HTTPS and staff access |
| A read-only deploy key for `mohamoudabdullahi1988-maker/sidra-erp` on the server | `bench get-app` of the private repo |
| Secret storage for the MariaDB root, Administrator and demo-user passwords | Nothing secret goes in Git or in chat |
| Off-server backup target (S3-compatible bucket or similar) | NFR-05 and SRS v2.0 §2.2 |
| Who may access staging (IP list or VPN) | Private staging |
| SSH access for whoever deploys | To run the steps above |

## 7. Update and rollback

```bash
cd frappe-bench
bench --site <staging-site> backup --with-files
bench update --pull --apps sidra_realestate --no-backup   # or: cd apps/sidra_realestate && git pull
bench --site <staging-site> migrate
bench build --app sidra_realestate
bench restart
```

To roll back, check out the previous commit of `sidra_realestate`, then `bench --site <staging-site> restore <backup>` if a patch changed data, then migrate and restart. The current patches only add data (history rows, keys, currency); none removes or rewrites business amounts.
