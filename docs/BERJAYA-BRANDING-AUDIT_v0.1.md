# Berjaya — Branding Audit v0.1

**Document version:** v0.1 · **Date:** 13 Nov 2026 · **Prepared for:** Mohamoud Abdullahi Sheikh · recorded by Claude Code
**Decisions:** G17–G19 (`docs/DECISIONS-AND-GATES_v0.1.md`) · **Branch:** `feature/berjaya-rebrand` · **Baseline:** `develop` @ `5508f13`, app v0.1.17
**Status:** awaiting approval. No branding has been changed. Only rows approved as PRODUCT are edited.

## 1. Method

`git grep -i -I sidra` over the whole repository: **2,128 lines in 244 files** (binary files excluded; 244 file paths also contain "sidra"). Each line was classified by the rule of G19: does it name the software, or the business?

| Classification | Meaning | Action | Lines |
| --- | --- | --- | --- |
| PRODUCT | Shown to users as the software's name | Change to Berjaya | 11 |
| CLIENT | Names the actual company | Keep | 176 |
| INTERNAL | Identifier a user does not read as branding | Keep | 1,883 |
| UNSURE | Cannot classify with confidence | Keep, listed for review | 58 |
| **Total** | | | **2,128** |

PRODUCT and UNSURE lines were read one by one. CLIENT and INTERNAL were separated by pattern, so the split between those two is approximate; both are "keep", so the split changes no action. The classifier is not committed; its rules are the rows below.

## 2. PRODUCT — proposed changes to Berjaya

| # | File | Line / context | What users see | Action |
| --- | --- | --- | --- | --- |
| P1 | `sidra_realestate/hooks.py` | 2 `app_title = "Sidra Homes"`; 29 apps-screen `"title": "Sidra Homes"`; 23 comment | App name on the apps screen and app switcher | Berjaya, read from the single constant |
| P2 | `sidra_realestate/branding.py` | 16 `BRAND_NAME = "Sidra Homes"`; 1, 4 docstring | System Settings app name (browser tab titles, login "Login to …"), Website Settings app name, website footer "powered by" | `BRAND_NAME = "Berjaya"`. This becomes the single source of the product name |
| P3 | `sidra_realestate/www/sidra/index.html` | 7 `<title>`; 15 header `<span>` | Front page tab title and header wordmark | Berjaya, from the constant. The route `/sidra` is unchanged |
| P4 | `clients/staff/web/index.html` | 1 `<title>Sidra Homes · Staff</title>`; 2 sidebar brand "SIDRA / HOMES / STAFF" | Staff dashboard tab title and sidebar brand | "Berjaya · Staff" and "BERJAYA / STAFF". The route `/sidra-staff/` is unchanged |
| P5 | `README.md` | 3 `# Sidra Real Estate — ERPNext app` | Product documentation title | "Berjaya — ERPNext app (`sidra_realestate`)"; line 5 keeps "runs Sidra Homes' business" |

Tests follow the constant: `tests/test_branding.py` already asserts against `BRAND_NAME`. New tests are added in Step 6.

## 3. UNSURE — your decision needed

| # | What | Where | Why it is unsure | Recommendation |
| --- | --- | --- | --- | --- |
| U1 | Logo and icon artwork | `images/sidra-logo.png`, `sidra-icon.png`, `favicon.png`; referenced by `hooks.py` 3, 28, 42, `branding.py` 17, `www/sidra/index.html` 14, staff `index.html`, `README.md` 1 (15 lines) | The artwork is the **Sidra Homes company logo**. It is used both as the software's navbar / login / splash logo **and** as the letterhead on the three print formats. The prompt asks for a plain text wordmark | Keep the files and the print formats untouched (company identity). Add a new text-only "Berjaya" wordmark image and point only the software logo, splash and favicon at it |
| U2 | Existing sites keep the old name | `branding.py` `_replaceable()` | It only overwrites blank or Frappe / ERPNext default values. The test site already holds "Sidra Homes", so changing the constant alone would **not** rebrand it | Treat the exact previous value "Sidra Homes" (and the old logo path) as replaceable in System, Website and Navbar Settings only. No Company record is read or written |
| U3 | Desk sidebar titles | `sidebar/sidra_real_estate/*.json` 284, `sidebar/sidra_construction/*.json` 138: `"title": "Sidra Real Estate"`, `"Sidra Construction"` | The `name` is an identifier (tests and links depend on it). The `title` is shown in navigation, where G18 says Berjaya; but "Sidra Real Estate" is also the company's name | Change the titles only to "Real Estate" and "Construction" (the Dock already uses these). Names unchanged. Not verified that Frappe v16 shows `title` separately from `name`; if it does not, leave both |
| U4 | Document titles | 23 files: "Sidra ERP — …" in `docs/`, `clients/staff/README.md`, `clients/staff/AGENTS.md` | Product documentation → Berjaya under G18, but most are dated specs and records, and rule 7 ties each doc to a version | Rename nothing now. Retitle living documents (`DEPLOYMENT`, `ENVIRONMENT`, `DECISIONS-AND-GATES`) at their next version; leave dated specs, handovers and briefs as records |
| U5 | App description | `hooks.py` 6, `pyproject.toml` 6: "Sidra Real Estate on ERPNext: …" | Seen only by administrators in the installed-apps list and by package tooling | "Berjaya: real estate on ERPNext for Sidra Homes — …" in `hooks.py`; `pyproject.toml` is outside this chat's files, so leave it |
| U6 | Native Android / macOS app names | `clients/staff/native/**`, `.github/workflows/staff-client.yml` 41 (10 lines): app label "Sidra Homes", "SIDRA HOMES" status bar, "Connect to Sidra", window title, `Sidra Homes.app` | They name the software, but they only wrap `/sidra-staff/`, which G20 drops, and a rename needs the apps rebuilt and reinstalled | Leave unchanged in this PR |
| U7 | Insights workbook title | `integrations/insights/build_workbook.py` 131, 173, 176 and its example (6 lines): "Sidra Owner Overview" | Reads as the company's owner report, not the software | Keep (treat as CLIENT) |

## 4. CLIENT — kept (176 lines, 60 files)

| Group | Examples |
| --- | --- |
| Company **Sidra Homes** and the two historical demo Companies | `finance_demo.py`, `pilot_demo.py`, `demo.py`, tests, `deploy/`, G14 and G16 text |
| Company identity on prints | The three print formats' letterhead block and `alt="Sidra Homes"` (sale contract, sale quotation, construction quotation) |
| The company in user messages | "The staff app is for Sidra staff", "Sign in with a permitted Sidra staff account", "Sidra must supply both Somali and English text", clause "Sidra's first right to design and build", field labels "Sidra Approval" and "Sidra Title Delay Penalty" |
| The company in specs and rules | "Mohamoud / Sidra management", brokerage journeys, clause wording ownership |

## 5. INTERNAL — kept (1,883 lines, 238 files)

| Group | Examples |
| --- | --- |
| App, module and package | `sidra_realestate`, `sidra_property`, `sidra_sales`, `sidra_installments`, `sidra_construction`, `sidra_brokerage`, Python paths and classes |
| Site, flags, repository, deploy | `sidra.local`, `sidra_*` flags, `SIDRA_CONFIG`, `SIDRA_INSIGHTS_DISPOSABLE_SITE`, `sidra-erp`, `/home/frappe/sidra/…`, `co.sidrahomes.staff` |
| DocType, report, role, role profile and module names | "Sidra Sale Contract", "Sidra Unit", "Sidra Executive Detail", "Sidra Sales Manager", Module Profile "Sidra Staff" |
| Routes and assets | `/sidra`, `/sidra-staff/`, `/desk/sidra-sale-contract`, CSS classes `sidra-contract`, field `sidra_location` |
| History | `CHANGELOG.md` entries and earlier decisions are not rewritten |

**Note for later, no action here.** DocType, role and module names stay under G19 and the prompt's MUST NOT CHANGE list, but Desk shows them to users: list and form titles read "Sidra Sale Contract", and role pickers read "Sidra Sales Manager". The sidebar and Dock labels already drop the prefix. The `/berjaya` interface shows its own labels, so this fades as staff move over.

## 6. Conflicts and observations reported

| # | Observation |
| --- | --- |
| 1 | The product was branded "**Sidra Homes**", the same string as the Company. Every "Sidra Homes" was therefore read in context, not replaced by pattern. |
| 2 | The decisions file says a new decision gets a new version of the file, but G9–G16 were added to v0.1 in place. G17–G20 follow that practice. |
| 3 | The prompt asks for D-A, D-B and D-C. The evening's rollout decisions (route `/berjaya`, colours, rebrand first) are recorded as **G20** so other chats read them in the repository; remove G20 if you want it recorded elsewhere. |
| 4 | Colours are approved (G20) but this PR leaves existing colours as they are, as the prompt says. |
| 5 | No product branding was found in system email templates or notifications: the app ships none. The website footer value is covered by P2. |
