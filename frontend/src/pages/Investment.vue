<script setup>
import { dateText, money } from '../format'

const investments = [
  { reference: 'DEMO-INV-01', investor: 'Cedar Demo Partners', project: 'North Courtyard Villas', funding: 'Lump sum', committed: 80000, received: 80000 },
  { reference: 'DEMO-INV-02', investor: 'Harbor Demo Capital', project: 'Juniper House', funding: 'Installments', committed: 60000, received: 30000, nextDue: '2026-12-15' },
  { reference: 'DEMO-INV-03', investor: 'Maple Demo Holdings', project: 'West Orchard Plots', funding: 'Installments', committed: 45000, received: 15000, nextDue: '2026-12-20' },
]
const committed = investments.reduce((sum, row) => sum + row.committed, 0)
const received = investments.reduce((sum, row) => sum + row.received, 0)
const figures = [
  { label: 'Committed funding', amount: committed },
  { label: 'Funding received', amount: received },
  { label: 'Remaining commitments', amount: committed - received },
]
</script>

<template>
  <section class="page">
    <header class="bj-head">
      <div>
        <h1 class="page__title">Investment</h1>
        <p class="bj-sub">Fictional demonstration data</p>
      </div>
    </header>

    <div class="bj-grid">
      <article v-for="figure in figures" :key="figure.label" class="bj-card">
        <h2>{{ figure.label }}</h2>
        <p class="bj-figure">{{ money(figure.amount, 'USD') }}</p>
      </article>
    </div>

    <section class="bj-section" aria-labelledby="investment-funding">
      <h2 id="investment-funding">Funding by investment</h2>
      <div class="page__card bj-table-wrap">
        <table class="bj-table bj-table--stack">
          <thead>
            <tr>
              <th scope="col">Investor</th>
              <th scope="col">Funded project</th>
              <th scope="col">Funding</th>
              <th scope="col" class="bj-right">Committed</th>
              <th scope="col" class="bj-right">Received</th>
              <th scope="col" class="bj-right">Remaining</th>
              <th scope="col">Next due date</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in investments" :key="row.reference">
              <td data-label="Investor"><span>{{ row.investor }}<span class="bj-small">{{ row.reference }}</span></span></td>
              <td data-label="Funded project">{{ row.project }}</td>
              <td data-label="Funding">{{ row.funding }}</td>
              <td data-label="Committed" class="bj-right">{{ money(row.committed, 'USD') }}</td>
              <td data-label="Received" class="bj-right">{{ money(row.received, 'USD') }}</td>
              <td data-label="Remaining" class="bj-right">{{ money(row.committed - row.received, 'USD') }}</td>
              <td data-label="Next due date">{{ row.nextDue ? dateText(row.nextDue) : '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </section>
</template>
