<!-- Description: Restocking view: budget slider drives live restock recommendations from demand forecasts. -->
<!-- Description: Place Order submits via POST /api/orders/restock; recommendation math lives in utils/restocking.js. -->
<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.budgetLabel') }}</h3>
        </div>
        <div class="budget-panel">
          <input
            type="range"
            class="budget-slider"
            v-model.number="budget"
            :min="5000"
            :max="250000"
            :step="5000"
          />
          <div class="budget-scale">
            <span>{{ formatCurrency(5000, currentCurrency) }}</span>
            <span class="budget-value">{{ formatCurrency(budget, currentCurrency) }}</span>
            <span>{{ formatCurrency(250000, currentCurrency) }}</span>
          </div>
        </div>
        <div class="stats-grid">
          <div class="stat-card info">
            <div class="stat-label">{{ t('restocking.budgetLabel') }}</div>
            <div class="stat-value">{{ formatCurrency(budget, currentCurrency) }}</div>
          </div>
          <div class="stat-card warning">
            <div class="stat-label">{{ t('restocking.recommendedCost') }}</div>
            <div class="stat-value">{{ formatCurrency(recommendation.totalCost, currentCurrency) }}</div>
          </div>
          <div class="stat-card success">
            <div class="stat-label">{{ t('restocking.remainingBudget') }}</div>
            <div class="stat-value">{{ formatCurrency(recommendation.remainingBudget, currentCurrency) }}</div>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommendedItems') }} ({{ recommendation.items.length }})</h3>
        </div>
        <div v-if="recommendation.items.length" class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.itemName') }}</th>
                <th>{{ t('restocking.table.trend') }}</th>
                <th>{{ t('restocking.table.shortfall') }}</th>
                <th>{{ t('restocking.table.quantity') }}</th>
                <th>{{ t('restocking.table.unitCost') }}</th>
                <th>{{ t('restocking.table.lineCost') }}</th>
                <th>{{ t('restocking.table.leadTime') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in recommendation.items" :key="item.item_sku">
                <td><strong>{{ item.item_sku }}</strong></td>
                <td>{{ item.item_name }}</td>
                <td>
                  <span :class="['badge', item.trend]">{{ t(`trends.${item.trend}`) }}</span>
                </td>
                <td>{{ item.shortfall.toLocaleString() }}</td>
                <td>{{ item.quantity.toLocaleString() }}</td>
                <td>{{ formatCurrencyWithDecimals(item.unit_cost, currentCurrency, 2) }}</td>
                <td><strong>{{ formatCurrency(item.lineCost, currentCurrency) }}</strong></td>
                <td>{{ item.lead_time_days }} {{ t('restocking.days') }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="no-recommendations">{{ t('restocking.noRecommendations') }}</div>

        <div class="order-footer">
          <div v-if="submittedOrder" class="success-banner">
            {{ t('restocking.orderSuccess', {
              orderNumber: submittedOrder.order_number,
              date: formatDate(submittedOrder.expected_delivery)
            }) }}
          </div>
          <div v-if="submitError" class="error">{{ submitError }}</div>
          <button
            class="place-order-btn"
            :disabled="submitting || !recommendation.items.length"
            @click="placeOrder"
          >
            {{ submitting ? t('restocking.placingOrder') : t('restocking.placeOrder') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import { api } from '../api'
import { useFilters } from '../composables/useFilters'
import { useI18n } from '../composables/useI18n'
import { formatCurrency, formatCurrencyWithDecimals } from '../utils/currency'
import { buildRecommendations } from '../utils/restocking'

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency, currentLocale } = useI18n()
    const { getCurrentFilters } = useFilters()

    const loading = ref(true)
    const error = ref(null)
    const allForecasts = ref([])
    const budget = ref(50000)
    const submitting = ref(false)
    const submitError = ref(null)
    const submittedOrder = ref(null)

    // Recommendations re-rank locally on every slider change; no network calls
    const recommendation = computed(() => buildRecommendations(allForecasts.value, budget.value))

    const loadForecasts = async () => {
      try {
        loading.value = true
        allForecasts.value = await api.getDemandForecasts()
      } catch (err) {
        error.value = 'Failed to load demand forecasts: ' + err.message
      } finally {
        loading.value = false
      }
    }

    const placeOrder = async () => {
      if (submitting.value || !recommendation.value.items.length) return
      try {
        submitting.value = true
        submitError.value = null
        submittedOrder.value = null

        const filters = getCurrentFilters()
        const payload = {
          budget: budget.value,
          items: recommendation.value.items.map(item => ({
            sku: item.item_sku,
            quantity: item.quantity
          }))
        }
        if (filters.warehouse && filters.warehouse !== 'all') payload.warehouse = filters.warehouse
        if (filters.category && filters.category !== 'all') payload.category = filters.category

        submittedOrder.value = await api.createRestockOrder(payload)
      } catch (err) {
        const detail = err.response?.data?.detail || err.message
        submitError.value = t('restocking.orderError') + ': ' + detail
      } finally {
        submitting.value = false
      }
    }

    const formatDate = (dateString) => {
      const locale = currentLocale.value === 'ja' ? 'ja-JP' : 'en-US'
      return new Date(dateString).toLocaleDateString(locale, {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      })
    }

    onMounted(loadForecasts)

    return {
      t,
      currentCurrency,
      loading,
      error,
      budget,
      recommendation,
      submitting,
      submitError,
      submittedOrder,
      placeOrder,
      formatDate,
      formatCurrency,
      formatCurrencyWithDecimals
    }
  }
}
</script>

<style scoped>
.budget-panel {
  padding: 0 1.5rem 1rem;
}

.budget-slider {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 6px;
  border-radius: 3px;
  background: #e2e8f0;
  accent-color: #2563eb;
  cursor: pointer;
}

.budget-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #2563eb;
  border: 2px solid #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.budget-slider::-moz-range-thumb {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #2563eb;
  border: 2px solid #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.budget-scale {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-top: 0.5rem;
  color: #64748b;
  font-size: 0.813rem;
}

.budget-value {
  color: #0f172a;
  font-size: 1.25rem;
  font-weight: 700;
}

.no-recommendations {
  padding: 2rem 1.5rem;
  color: #64748b;
  text-align: center;
}

.order-footer {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.5rem;
  border-top: 1px solid #e2e8f0;
}

.success-banner {
  color: #16a34a;
  background: #dcfce7;
  border-radius: 6px;
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  font-weight: 500;
}

.place-order-btn {
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 0.625rem 1.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
}

.place-order-btn:hover:not(:disabled) {
  background: #1d4ed8;
}

.place-order-btn:disabled {
  background: #94a3b8;
  cursor: not-allowed;
}
</style>
