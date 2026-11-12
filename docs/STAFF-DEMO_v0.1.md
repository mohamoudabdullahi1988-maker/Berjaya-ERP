# Staff and financial demo v0.1

12 November 2026. The request is to populate contracts, sales, payments,
construction and financial statements on the existing test site.

Update 12 Nov 2026 (decision G12): on the test site the sample data is loaded
under **Sidra Homes**, not a separate demo Company. Select Sidra Homes and the
original date range returned by the loader. The loader refuses if Sidra Homes
holds any GL entry its manifest does not own. **Sidra Demo Homes** and
**Sidra Finance Demo - Fictional** are left exactly as they are.

After deploying this app revision, run as the frappe bench operator:
`bash apps/sidra_realestate/deploy/populate-staff-demo.sh`.

The script backs up the site, enables the existing three staging finance flags,
calls the existing transactional loader, verifies native vouchers/GL, and prints
the actual staff API records plus native report links. Reruns verify the existing
manifest and retain original dates. It refuses changed or unrelated datasets.
No site defaults, user defaults or permissions are changed.

The fixed finance dataset contains 3 sales invoices, 2 purchase invoices,
4 payment entries and 1 capital journal: revenue USD 70,000, expenses 20,000,
receipts 35,000, bank 123,000, receivables 35,000, payables 8,000.
Debit and credit totals are both 237,000. Its separate operational records are
a USD 30,000 signed contract, three added fictional units, two leads, a three-row schedule,
and one active construction job with recorded 40% stage progress.
See FINANCE-DEMO_v0.2.md for the accounting basis, isolation and limits.

Staff Sales previously returned unavailable unconditionally. It now groups
permission-filtered Lead records by recorded status and creation period.
Qualified opportunities and conversion stay unknown: no lead-to-contract link
or qualification rules are invented. Status text is rendered as DOM text.
The other company/record boundaries remain in Frappe get_list.

Open /sidra-staff/ with an authorized management/accounting account, choose
Sidra Homes and Last 90 days. Contracts, Sales, Payments and Construction
read persisted records; do not use ?demo=1 to verify upload. If a prior dataset is
older than the supported staff period, some period measures can correctly be zero;
native report links keep the original range. Historical dates are not rewritten.

Expected acceptance: financial report Company/date filters match the manifest;
native GL contains the ten submitted vouchers; staff contracts/sales/payments/jobs
show their corresponding records. Permission-limited users may see unavailable
data rather than partial figures. No automatic permission grant is performed.
Anonymous and construction-only users must not gain Lead/accounting access.

Local checks cover status aggregation and syntax. Frappe CI covers actual
record insertion and permissions. Neither proves deployment to the VPS.
Rollback the code to restore the former Sales presentation; disabling the three
flags disables the demo adapter while native vouchers remain. Do not delete GL.
