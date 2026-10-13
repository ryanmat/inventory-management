// Description: Budget-constrained restock recommendation engine over demand forecasts.
// Description: Pure functions, no Vue imports; consumed by views/Restocking.vue.

/**
 * Build restock recommendations that fit within a budget.
 *
 * Candidates are non-decreasing forecast items, recommended at full
 * forecasted_demand quantity. Ranking: increasing trend first, then largest
 * projected shortfall, then largest relative change. Allocation is first-fit
 * greedy with no partial fills: items whose full line cost does not fit are
 * skipped and cheaper items further down may still be selected.
 */
export function buildRecommendations(forecasts, budget) {
  const candidates = forecasts
    .filter(f => f.trend !== 'decreasing')
    .map(f => ({
      ...f,
      shortfall: Math.max(f.forecasted_demand - f.current_demand, 0),
      quantity: f.forecasted_demand,
      lineCost: f.forecasted_demand * f.unit_cost
    }))
    .sort((a, b) =>
      (a.trend === 'increasing' ? 0 : 1) - (b.trend === 'increasing' ? 0 : 1) ||
      b.shortfall - a.shortfall ||
      (b.shortfall / b.current_demand) - (a.shortfall / a.current_demand)
    )

  let remaining = budget
  const items = []
  for (const candidate of candidates) {
    if (candidate.lineCost <= remaining) {
      items.push(candidate)
      remaining -= candidate.lineCost
    }
  }

  return {
    items,
    totalCost: budget - remaining,
    remainingBudget: remaining,
    maxLeadTime: items.reduce((max, item) => Math.max(max, item.lead_time_days), 0)
  }
}
