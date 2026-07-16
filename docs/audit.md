# Inventory App Audit and Prioritized Action Plan

A three-lens audit (security, performance, UX) of the Factory Inventory Management System, conducted by three independent reviewers who investigated in parallel and then challenged each other's severity ratings. This document is the reconciled result. It is a read-only assessment: no application code was changed producing it.

Everything is calibrated to the app's actual context, a local, single-user demo with in-memory data. Severity (how bad) and urgency (when to act) are kept separate on purpose: several genuinely High-severity items are deploy-blockers that are invisible today, which is not the same as fix-this-now.

## What the cross-challenge round settled

- **One shared blast radius, not three findings.** SEC-3 (unbounded restock writes), PERF-5 (unpaginated reads), and PERF-1 (refetch on every filter change) are distinct defects with one root cause: the orders collection has no bound and no pagination. A client inflating it through the write path degrades every other client's read and re-render. They share a fix and should be read together.
- **A confirmation dialog is not a security control.** A client-side confirm before Place Order (UX-5) does nothing against a client calling the endpoint directly. UX-5 and SEC-3 are complementary, not substitutes.
- **The `/api/tasks` and `/api/purchase-orders` 404s are a single functional gap.** Those endpoints were never implemented server-side; the client calls them anyway. That one fact explains the silent task-write failures (UX-4) and the console 404. Implementing or removing those calls closes both.
- **Accessibility consolidated.** UX-1 and UX-2 merge into a single High "keyboard and screen-reader lockout" line rather than splitting to two Mediums. UX-3 (untranslated detail modals) holds firmly at High as a majority-path internationalization break.
- **PERF-1 is real today, but the harm is UX jank, not bandwidth.** On localhost the fetch is sub-100ms; the cost is the `v-if="loading"` swap blanking the whole view on every filter toggle. Performance and UX co-signed it at Medium with a shared fix.

## Plan

Ordered by when to act, highest-leverage first within each tier. "Closes" names the findings each action resolves.

### Tier A: fix now (real today, user-facing, or cheap and high-value)

| # | Action | Severity | Effort | Closes |
|---|--------|----------|--------|--------|
| A1 | Route the four detail modals (Inventory, Product, Cost, Backlog) and the Logout string through `t()` plus locale keys, matching the Reports internationalization fix already shipped | High | M | UX-3, part of UX-10 |
| A2 | Make detail-row triggers real focusable buttons with keyboard handlers; give modals `role="dialog"` / `aria-modal` / labelledby, focus move-trap-restore, Escape-to-close, and an `aria-label` on the close button | High | L | UX-1 + UX-2 (merged) |
| A3 | Hoist `useI18n()` out of per-row helpers (`formatDate`, `translatePeriod`) into `setup()` once | Medium | S | PERF-2 |
| A4 | Load-lifecycle pass: on refetch keep prior data plus a subtle inline spinner instead of the full-view "Loading" swap; add empty states to Inventory, Orders, Demand; hoist the filterless `getBacklog` out of the filter watcher | Medium | M | PERF-1, UX-7 |
| A5 | Resolve the missing endpoints: implement or remove the client calls to `/api/tasks` and `/api/purchase-orders`; surface write errors inline instead of `console.error` only | Medium | S-M | UX-4, console 404 |

### Tier B: before it leaves localhost (deploy-blockers; B1 and B2 are cheap enough to do now defensively)

| # | Action | Severity | Effort | Closes |
|---|--------|----------|--------|--------|
| B1 | Set `allow_credentials=False`, or pin origins to `http://localhost:3000`. One line, correct even for the demo | Medium (High once auth lands) | S | SEC-2 |
| B2 | Bound restock input: `max_length` on `items`, an `le=` cap on `quantity`, a sane `budget` cap; add rate limiting | Medium | S-M | SEC-3 (write side) |
| B3 | Add an auth dependency on write routes; keep binding to `127.0.0.1` for the demo rather than `0.0.0.0` | High (deploy-blocker) | M | SEC-1 |
| B4 | Add a security-headers middleware; keep error messages generic | Low | S | SEC-4 |

CSRF is explicitly not live today (no cookies or session), but it becomes real the moment auth lands, given B1's credentials-plus-wildcard combination and the state-changing POST. Address it alongside B3.

### Tier C: at scale or larger effort (pattern smells, invisible at 250 orders)

| # | Action | Severity | Effort | Closes |
|---|--------|----------|--------|--------|
| C1 | Build a `Map(sku -> inventoryItem)` for `topProducts` instead of a nested linear `.find` | Medium at scale | S | PERF-3 |
| C2 | Paginate `GET /api/orders` and virtualize the table (read side of the SEC-3 chain) | Low at scale | M | PERF-5 |
| C3 | Responsive layout: `flex-wrap` on nav and filters, a mobile breakpoint, and stop hard-coding the sticky offset | Medium | M | UX-6 |
| C4 | `aria-label` on icon-only buttons, `aria-hidden` on decorative SVGs, and replace blur-timeout dropdowns with click-outside plus Escape | Medium | S-M | UX-8 |
| C5 | Confirm or review step before Place Order; confirm-or-undo on task delete (a UX safeguard, complementary to B2) | Medium | S | UX-5 |
| C6 | Move derived template data to `computed` (`getOrdersByStatus` runs four times per render, etc.), parse dates once server-side, fix `:key="idx"` at Orders.vue:57 and :104, pre-index purchase orders | Low | S | PERF-4, PERF-6, PERF-7, PERF-8 |

### Tier D: polish

Contrast fixes (`#94a3b8` fails WCAG AA at roughly 2.8:1), clear the stale Restocking success banner when the slider changes, add a label to the budget slider, replace the Logout `alert()` with a translated no-op, and optional public-repo toolchain hygiene. Closes UX-9, the rest of UX-10, and SEC-5.

## Recommendation

If only one tier gets done, do Tier A. It is the intersection of "users feel it today" and "moderate effort," and A1 is the same defect class as the Reports internationalization bug already fixed. Tier B's cheap items (B1 one-liner, B2 input caps) are worth doing now as defensive hygiene even on localhost.

## Appendix: full findings by lens

### Security (5)

- SEC-1 (High, deploy-blocker): no authentication or authorization on any route; the new `POST /api/orders/restock` lets any reachable client mutate the shared in-memory orders list. Demo-acceptable on localhost.
- SEC-2 (Medium): `allow_origins=["*"]` combined with `allow_credentials=True` is an invalid and dangerous CORS combination; becomes High the moment cookie or session auth lands.
- SEC-3 (Medium): restock input is unbounded (no cap on item count or quantity, no rate limit); the server-side budget check bounds dollars but not payload size, so it is not full input validation. Memory-growth path if exposed off-host.
- SEC-4 (Low): no security response headers; error messages echo client input, though the Vue client has no HTML-rendering sink so this is not an XSS vector today.
- SEC-5 (Low): public-repo toolchain hygiene. No secrets found in the tree or git history; the MCP config uses the correct env-var interpolation pattern.

No injection found. CSRF not live today; gated on auth landing.

### Performance (8)

- PERF-1 (Medium): every filter change refetches the whole API; Dashboard also refetches the filterless `getBacklog`. Real redundant work today; harm is the loading-flash render lifecycle.
- PERF-2 (Medium): `formatDate` and `translatePeriod` re-instantiate the entire `useI18n()` composable on every call, roughly 500 setups per Orders render.
- PERF-3 (Medium at scale): `topProducts` runs an O(line-items x inventory) nested loop with a linear `.find` on every filter change.
- PERF-4 (Low): derived template data computed via methods, re-run every render (`getOrdersByStatus` four times per render).
- PERF-5 (Low at scale): `GET /api/orders` returns all 250 orders unpaginated and the table renders every row.
- PERF-6 (Low): backend re-scans the full orders list per request with chained list copies and substring date matching.
- PERF-7 (Low): `v-for` index keys at Orders.vue:57 and :104.
- PERF-8 (Low): minor backend nested scans (backlog purchase-order check, restock id minting).

Confirmed good patterns: Spending.vue fetches once and filters client-side; Restocking's slider re-ranks locally with no I/O; modals use `v-if` so they unmount when closed.

### UX (10)

- UX-1 + UX-2 (High, merged): detail views are unreachable by keyboard and screen-reader users (non-focusable div/td/tr click handlers, zero tabindex/role/keydown), and the modals they would open have no dialog semantics, focus management, or Escape-to-close. WCAG 2.1.1 Level A failure spanning three views.
- UX-3 (High): the four detail modals are hardcoded English and never translate; the Japanese experience is half-broken on the majority detail path.
- UX-4 (Medium): task writes fail silently (console.error only), including the `/api/tasks` 404.
- UX-5 (Medium): Place Order and task delete fire with no confirmation.
- UX-6 (Medium): no responsive design; the nav and FilterBar overflow below roughly 1000px. Data tables themselves scroll fine.
- UX-7 (Medium): missing empty states on Inventory, Orders, and Demand when a filter returns zero rows.
- UX-8 (Medium): icon-only controls lack accessible names; blur-timeout dropdowns are fragile.
- UX-9 (Low): muted-text contrast below AA, a stale Restocking success banner, and an unlabeled budget slider.
- UX-10 (Low): Logout is a dead control firing a native English `alert()` that performs no session action and does not translate.

Confirmed good pattern: loading and error states are present and consistent across all seven routed views.
