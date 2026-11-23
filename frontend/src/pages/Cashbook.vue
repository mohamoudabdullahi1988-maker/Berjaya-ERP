<script setup>
import { computed, ref, watch } from 'vue'

import { apiGet, apiPost, apiPostFile } from '../api'
import { company } from '../company'
import { dateText, deskLink } from '../format'
import CompanyPicker from '../components/CompanyPicker.vue'

const method = 'sidra_realestate.api.cashbook.'
const get = async (name, params) => (await apiGet('/api/method/' + method + name, params)).message
const account = ref('')
const accounts = ref([])
const today = new Date()
const localDate = (day) => [day.getFullYear(), day.getMonth() + 1, day.getDate()]
  .map((part) => String(part).padStart(2, '0')).join('-')
const fromDate = ref(localDate(new Date(today.getFullYear(), today.getMonth(), 1)))
const toDate = ref(localDate(today))
const observed = ref('')
const comparedBalance = ref('')
const comparisonLabel = computed(() => data.value?.account_type === 'Cash' ? 'Counted balance' : 'Statement closing balance')

const data = ref(null)
const accountError = ref('')
const loadError = ref('')
const busy = ref(false)
const actionBusy = ref(false)
const notice = ref('')
const actionError = ref('')
const ledgerOffset = ref(0)
const statementOffset = ref(0)
const activeTransaction = ref('')
const candidates = ref(null)
const statementFile = ref(null)
const evidenceFile = ref(null)
const manual = ref({ date: toDate.value, reference: '', deposit: '', withdrawal: '', description: '' })
const scope = computed(() => ({ company: company.value, account: account.value }))
const period = computed(() => ({ ...scope.value, from_date: fromDate.value, to_date: toDate.value }))

let companyRequest = 0
let ledgerRequest = 0
let matchRequest = 0

function displayMoney(value) {
  const precision = data.value.precision
  return new Intl.NumberFormat('en', {
    style: 'currency', currency: data.value.currency, currencyDisplay: 'code',
    minimumFractionDigits: precision, maximumFractionDigits: precision,
  }).format(value)
}

watch(company, async (selectedCompany) => {
  const request = ++companyRequest
  account.value = ''
  accounts.value = []
  accountError.value = ''
  if (!selectedCompany) return
  try {
    const result = await get('list_accounts', { company: selectedCompany })
    if (request === companyRequest) accounts.value = result
  } catch (error) {
    if (request === companyRequest) accountError.value = error.message
  }
}, { immediate: true })

async function load(balance) {
  const request = ++ledgerRequest
  const params = {
    ...period.value, observed_balance: balance ?? comparedBalance.value,
    ledger_offset: ledgerOffset.value, statement_offset: statementOffset.value,
  }
  loadError.value = ''
  busy.value = Boolean(params.company && params.account && params.from_date && params.to_date)
  if (!busy.value) return
  try {
    const result = await get('get_cashbook', params)
    if (request === ledgerRequest) {
      data.value = result
      comparedBalance.value = params.observed_balance
    }
  } catch (error) {
    if (request === ledgerRequest) {
      if (balance === undefined || error.kind === 'denied') data.value = null
      loadError.value = error.message
    }
  } finally {
    if (request === ledgerRequest) busy.value = false
  }
}

function clearMatches() {
  matchRequest++
  activeTransaction.value = ''
  candidates.value = null
}

watch(period, () => {
  data.value = null
  comparedBalance.value = observed.value = ''
  ledgerOffset.value = statementOffset.value = 0
  notice.value = actionError.value = ''
  statementFile.value = evidenceFile.value = null
  manual.value = { date: toDate.value, reference: '', deposit: '', withdrawal: '', description: '' }
  clearMatches()
  load()
})

function changePage(kind, direction) {
  const offset = kind === 'ledger' ? ledgerOffset : statementOffset
  offset.value += direction * 100
  clearMatches()
  load()
}

async function findMatches(transaction) {
  const request = ++matchRequest
  activeTransaction.value = transaction
  candidates.value = null
  actionError.value = ''
  try {
    const result = await get('matching_vouchers', { ...period.value, transaction })
    if (request === matchRequest) candidates.value = result
  } catch (error) {
    if (request === matchRequest) {
      actionError.value = error.message
      clearMatches()
    }
  }
}

async function update(operation) {
  const params = period.value
  actionBusy.value = true
  actionError.value = notice.value = ''
  try {
    const message = await operation()
    if (params !== period.value) return
    notice.value = message
    clearMatches()
    statementOffset.value = 0
    await load()
  } catch (error) {
    if (params === period.value) actionError.value = error.message
  } finally {
    actionBusy.value = false
  }
}

function importStatement() {
  update(async () => {
    const result = await apiPostFile(method + 'import_statement', statementFile.value, scope.value)
    return `Imported ${result.created} statement lines. Skipped ${result.duplicates} already recorded.`
  })
}

function enterLine() {
  update(async () => {
    const result = await apiPostFile(method + 'enter_statement_line', evidenceFile.value, { ...scope.value, ...manual.value })
    return `${result.created ? 'Recorded statement line' : 'Statement line already recorded'} ${result.name}. PDF evidence saved.`
  })
}

function matchVoucher(transaction, row) {
  update(async () => {
    const result = await apiPost(method + 'match_voucher', {
      ...period.value, transaction, voucher_type: row.doctype, voucher: row.name,
    })
    return result.status === 'Reconciled' ? 'Statement line reconciled.' : 'Voucher matched. A balance remains unmatched.'
  })
}

function compare() {
  load(observed.value)
}
</script>

<template>
  <section class="page">
    <header class="bj-head">
      <h1 class="page__title">Cashbook &amp; Reconciliation</h1>
      <CompanyPicker />
    </header>

    <div class="page__card cashbook-filters">
      <label><span id="cashbook-account-label">Account</span>
        <select v-model="account" aria-labelledby="cashbook-account-label" class="bj-select" :disabled="!accounts.length || actionBusy">
          <option value="">Choose a cash or bank account</option>
          <option v-for="row in accounts" :key="row.name" :value="row.name">
            {{ row.account_name }} ({{ row.account_currency }})
          </option>
        </select>
      </label>
      <label>From <input v-model="fromDate" class="bj-select" type="date" required /></label>
      <label>To <input v-model="toDate" class="bj-select" type="date" :min="fromDate" required /></label>
      <button type="button" class="bj-btn" :disabled="!account || busy || actionBusy" @click="load()">Refresh</button>
    </div>
    <p v-if="accountError || loadError" class="bj-note" role="alert">{{ accountError || loadError }}</p>
    <p v-else-if="busy" class="bj-note" role="status">Loading cashbook…</p>
    <p v-if="notice" class="bj-note" role="status">{{ notice }}</p>
    <p v-if="actionError" class="bj-note" role="alert">{{ actionError }}</p>

    <template v-if="data">
      <div class="bj-grid">
        <article v-for="(label, field) in { opening: 'Opening balance', receipts: 'Receipts', payments: 'Payments', closing: 'Closing balance' }" :key="field" class="bj-card">
          <h2>{{ label }}</h2>
          <p class="bj-figure">{{ displayMoney(data[field]) }}</p>
        </article>
      </div>

      <section class="bj-section">
        <h2>Balance comparison</h2>
        <form class="page__card cashbook-filters" @submit.prevent="compare">
          <label>{{ comparisonLabel }} ({{ data.currency }})
            <input v-model="observed" class="bj-select" inputmode="decimal" required />
          </label>
          <button type="submit" class="bj-btn" :disabled="actionBusy">Compare</button>
          <p v-if="data.difference !== null" role="status">
            Difference from ledger closing balance <strong>{{ displayMoney(data.difference) }}</strong>
          </p>
        </form>
      </section>

      <section class="bj-section">
        <h2>Ledger movements</h2>
        <div class="page__card">
          <p v-if="!data.movements.length" class="bj-note">No ledger movements in this period.</p>
          <div v-else class="bj-table-wrap">
            <table class="bj-table bj-table--stack">
              <thead><tr><th>Date</th><th>Source voucher</th><th>Receipt</th><th>Payment</th><th>Running balance</th></tr></thead>
              <tbody>
                <tr v-for="row in data.movements" :key="row.name">
                  <td data-label="Date">{{ dateText(row.date) }}</td>
                  <td data-label="Source voucher"><a class="bj-link" :href="deskLink(row.voucher_type, row.voucher_no)">{{ row.voucher_no }}</a></td>
                  <td data-label="Receipt">{{ displayMoney(row.receipt) }}</td>
                  <td data-label="Payment">{{ displayMoney(row.payment) }}</td>
                  <td data-label="Running balance">{{ displayMoney(row.balance) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <footer v-if="ledgerOffset || data.has_more" class="bj-foot">
            <button v-if="ledgerOffset" class="bj-btn" @click="changePage('ledger', -1)">Previous ledger page</button>
            <button v-if="data.has_more" class="bj-btn" @click="changePage('ledger', 1)">Next ledger page</button>
          </footer>
        </div>
      </section>

      <section v-if="data.statement" class="bj-section">
        <h2>Statement reconciliation</h2>
        <div v-if="data.statement.can_add" class="page__card cashbook-entry">
          <form class="cashbook-filters" @submit.prevent="importStatement">
            <label>Statement file (CSV or Excel)
              <input class="bj-select" type="file" accept=".csv,.xlsx" required @change="statementFile = $event.target.files[0]" />
            </label>
            <button type="submit" class="bj-btn" :disabled="!statementFile || actionBusy">Import statement</button>
            <a class="bj-link" href="/assets/sidra_realestate/cashbook-statement.csv" download>Download CSV template</a>
          </form>
          <details>
            <summary>Enter a statement line from PDF</summary>
            <form class="cashbook-filters" @submit.prevent="enterLine">
              <label>Date <input v-model="manual.date" class="bj-select" type="date" required /></label>
              <label>Transaction reference <input v-model.trim="manual.reference" class="bj-select" maxlength="140" required /></label>
              <label>Deposit <input v-model="manual.deposit" class="bj-select" inputmode="decimal" /></label>
              <label>Withdrawal <input v-model="manual.withdrawal" class="bj-select" inputmode="decimal" /></label>
              <label>Description <input v-model="manual.description" class="bj-select" /></label>
              <label>Original PDF <input class="bj-select" type="file" accept=".pdf" required @change="evidenceFile = $event.target.files[0]" /></label>
              <button type="submit" class="bj-btn" :disabled="!evidenceFile || actionBusy">Save statement line</button>
            </form>
          </details>
        </div>

        <h3>Unmatched statement lines</h3>
        <div class="page__card">
          <p v-if="!data.statement.lines.length" class="bj-note">No unmatched statement lines in this period.</p>
          <div v-else class="bj-table-wrap">
            <table class="bj-table bj-table--stack">
              <thead><tr><th>Date</th><th>Statement reference</th><th>Deposit</th><th>Withdrawal</th><th>Unmatched</th><th>Vouchers</th></tr></thead>
              <tbody>
                <tr v-for="line in data.statement.lines" :key="line.name">
                  <td data-label="Date">{{ dateText(line.date) }}</td>
                  <td data-label="Statement reference"><a class="bj-link" :href="deskLink('Bank Transaction', line.name)">{{ line.reference_number || line.name }}</a></td>
                  <td data-label="Deposit">{{ displayMoney(line.deposit) }}</td>
                  <td data-label="Withdrawal">{{ displayMoney(line.withdrawal) }}</td>
                  <td data-label="Unmatched">{{ displayMoney(line.unallocated_amount) }}</td>
                  <td data-label="Vouchers"><button class="bj-btn" :disabled="actionBusy" @click="findMatches(line.name)">Find vouchers</button></td>
                </tr>
              </tbody>
            </table>
          </div>
          <footer v-if="statementOffset || data.statement.has_more" class="bj-foot">
            <button v-if="statementOffset" class="bj-btn" @click="changePage('statement', -1)">Previous statement page</button>
            <button v-if="data.statement.has_more" class="bj-btn" @click="changePage('statement', 1)">Next statement page</button>
          </footer>
        </div>

        <div v-if="activeTransaction" class="page__card cashbook-entry">
          <h3>Existing vouchers for {{ activeTransaction }}</h3>
          <p v-if="!candidates" role="status">Looking for vouchers…</p>
          <p v-else-if="!candidates.length">No eligible vouchers in the selected period.</p>
          <ul v-else class="cashbook-candidates">
            <li v-for="row in candidates" :key="row.doctype + row.name">
              <a class="bj-link" :href="deskLink(row.doctype, row.name)">{{ row.name }}</a>
              <span>{{ dateText(row.date) }} · {{ displayMoney(row.amount) }}<template v-if="row.reference"> · {{ row.reference }}</template></span>
              <button v-if="row.can_match && data.statement.can_match" type="button" class="bj-btn" :disabled="actionBusy" @click="matchVoucher(activeTransaction, row)">Match voucher</button>
            </li>
          </ul>
        </div>
      </section>
      <p v-else-if="data.account_type === 'Bank'" class="bj-note">Statement tools require access to an active Bank Account linked to this ledger account.</p>
    </template>
  </section>
</template>

<style scoped>
.cashbook-filters { display: flex; flex-wrap: wrap; align-items: end; gap: .75rem; padding: 1rem; }
.cashbook-filters label { display: grid; gap: .25rem; max-width: 100%; }
.cashbook-filters input, .cashbook-filters select { max-width: 100%; }
.cashbook-entry { padding: 1rem; }
.cashbook-entry .cashbook-filters { padding: .75rem 0; }
.cashbook-candidates { display: grid; gap: .5rem; }
.cashbook-candidates li { display: flex; flex-wrap: wrap; align-items: center; gap: .75rem; }
</style>
