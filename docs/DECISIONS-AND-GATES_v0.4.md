# Berjaya ERP decision v0.4

25 Nov 2026 · Approved by Mohamoud Abdullahi Sheikh. Follow the [delivery handover v0.3](DECISIONS-AND-GATES_v0.3.md) and [existing gates v0.2](DECISIONS-AND-GATES_v0.2.md) alongside this decision.

## G38 · Verified ERPNext invoice links

Finance reviews the signed agreement and verifies the link to each submitted ERPNext Sales Invoice for the same company and customer. An agreement can have several invoices. Each invoice belongs to a single individual sale or construction agreement. Finance adds historical links after reviewing the invoice and signed agreement. Existing customer identity alone is insufficient to match an invoice or receipt.

Finance records payments in ERPNext. A partial receipt on a linked multi-term invoice uses the ERPNext payment term the customer specifies. Finance uses distinct named payment terms with native term-based allocation enabled for these invoices. Existing approval, reconciliation and posting controls apply.

Berjaya shows the submitted invoices, their current outstanding amounts in receivable account currency, and their readable submitted Payment Entry allocations. Only allocations to the linked invoices appear. Unallocated receipts and balances on other agreements remain outside the statement. Finance can review the underlying vouchers in Desk. A posted balance is unavailable when there are no readable verified invoices. Approval and timing for broader production posting follow the existing financial gates.

Decision recorded for [GitHub issue #8](https://github.com/mohamoudabdullahi1988-maker/Berjaya-ERP/issues/8).
