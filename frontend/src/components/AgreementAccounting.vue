<script setup>
import { ref } from 'vue'

import { apiPost } from '../api'
import { dateText, deskLink, money } from '../format'

const props = defineProps({
  company: { type: String, required: true },
  statement: { type: Object, required: true },
})
const emit = defineEmits(['verified'])
const invoice = ref('')
const busy = ref(false)
const error = ref('')

async function verify() {
  busy.value = true
  error.value = ''
  try {
    await apiPost('sidra_realestate.api.delivery_dashboard.verify_agreement_invoice', {
      company: props.company,
      agreement_type: props.statement.agreement_type,
      agreement: props.statement.contract,
      sales_invoice: invoice.value,
    })
    invoice.value = ''
    emit('verified')
  } catch (err) {
    error.value = err.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section class="bj-section" aria-labelledby="posted-invoices">
    <h3 id="posted-invoices">ERPNext invoices and receipts</h3>
    <form v-if="statement.accounting.can_verify" class="bj-toolbar verify" @submit.prevent="verify">
      <label for="invoice-reference">Submitted sales invoice reference</label>
      <input id="invoice-reference" v-model.trim="invoice" class="bj-input" type="text" maxlength="140" required />
      <button class="bj-btn" :disabled="busy || !invoice">Verify invoice link</button>
      <p class="bj-muted">Check the posted invoice against the signed agreement before linking it.</p>
    </form>
    <p v-if="error" role="alert">{{ error }}</p>
    <p v-if="!statement.accounting.can_read_invoices">Your role needs sales invoice access to view posted balances.</p>
    <p v-else-if="!statement.accounting.invoices.length">The posted balance is unavailable until a verified invoice is accessible.</p>
    <template v-else>
      <p v-for="balance in statement.accounting.balances" :key="balance.currency">
        Outstanding on visible invoices <strong>{{ money(balance.amount, balance.currency) }}</strong>
      </p>
      <div class="bj-table-wrap">
        <table class="bj-table">
          <thead><tr><th scope="col">Invoice</th><th scope="col">Posted</th><th scope="col" class="bj-right">Outstanding</th></tr></thead>
          <tbody>
            <tr v-for="row in statement.accounting.invoices" :key="row.name">
              <td><a class="bj-link" :href="deskLink('Sales Invoice', row.name)">{{ row.name }}</a></td>
              <td>{{ dateText(row.posting_date) }}</td>
              <td class="bj-right">{{ money(row.outstanding_amount, row.party_account_currency) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="bj-muted">To record a receipt, open its invoice in Desk and use the payment term specified by the customer.</p>
      <h4>Posted receipt allocations</h4>
      <p v-if="!statement.accounting.can_read_receipts">Your role needs Payment Entry access to view receipt allocations.</p>
      <p v-else-if="!statement.accounting.receipts.length">No submitted receipts are allocated to these invoices.</p>
      <div v-else class="bj-table-wrap">
        <table class="bj-table">
          <thead><tr><th scope="col">Receipt</th><th scope="col">Posted</th><th scope="col">Invoice</th><th scope="col">Payment term</th><th scope="col" class="bj-right">Allocated</th></tr></thead>
          <tbody>
            <tr v-for="row in statement.accounting.receipts" :key="row.id">
              <td><a class="bj-link" :href="deskLink('Payment Entry', row.receipt)">{{ row.receipt }}</a></td>
              <td>{{ dateText(row.posting_date) }}</td><td>{{ row.invoice }}</td><td>{{ row.term || '—' }}</td>
              <td class="bj-right">{{ money(row.amount, row.currency) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </section>
</template>

<style scoped>
.verify label, .verify p { flex-basis: 100%; }
h3, h4, p { margin: 12px 0; }
h3, h4 { font-weight: 650; }
</style>
