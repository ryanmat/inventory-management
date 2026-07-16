---
name: vue-optimizer
description: Analyze Vue 3 component structure and suggest optimizations for rendering performance and code reuse. Use this skill whenever working with .vue files (components or views) -- reviewing, refactoring, optimizing, or before adding a new one -- and whenever the user mentions Vue performance, reactivity, re-renders, computed vs methods, v-for keys, extracting composables, duplicated component logic, or cleaning up Vue code. Trigger even when the user only says "review this component", "why is this slow", or "is there a cleaner way to do this" about a .vue file.
---

# Vue Component Optimizer

Analyze Vue 3 (Composition API) components for two classes of problem that compound as an app grows: **rendering performance** (work the framework repeats unnecessarily) and **code reuse** (logic and markup copied instead of shared). The goal is a concrete, ranked report the developer can act on, not a vague "looks good."

This project is Vue 3 + Composition API + Vite. Its own `client/CLAUDE.md` documents the intended conventions; this skill checks components *against* those conventions and against general Vue 3 performance principles.

## How to run an analysis

1. **Scope it.** If the user named a component, analyze that file. If they asked about the app broadly, analyze `client/src/views/` and `client/src/components/` together, because the highest-value reuse findings only appear when you compare files against each other.

2. **Run the first-pass scanner** to surface the mechanical, greppable smells fast:
   ```bash
   bash .claude/skills/vue-optimizer/scripts/scan.sh client/src
   ```
   Treat its output as *candidates*, not verdicts. It finds `v-for` index keys and helper names defined in more than one file. You still have to open the files and reason about everything it cannot see (methods that should be computed, toggle patterns, watcher debouncing, duplicated markup).

3. **Read the components** and evaluate each against the two checklists below. Always open the file and confirm a finding in context before reporting it -- a name that appears in two files is only a reuse finding if the two definitions actually do the same thing.

4. **Write the report** in the format at the bottom. Rank by impact, and make every finding actionable: point at `file:line`, say why it matters, and show the fix.

## Performance checklist

Vue re-runs a component's render function whenever its reactive dependencies change. Most performance problems are work placed where it gets repeated on every render instead of cached or avoided.

- **`v-for` keys must be stable unique IDs, never the array index.** With an index key, Vue reuses the wrong DOM nodes when the list reorders or an item is inserted/removed, causing visual glitches and, with form inputs, wrong-row state. Use `item.id`, `item.sku`, or another stable field. This is the single most common correctness-and-performance bug in this codebase's style guide.

- **Derived data belongs in `computed`, not in methods or inline template expressions.** A `computed` caches its result until its dependencies change; a method or inline expression (`{{ items.filter(...) }}`) re-runs on *every* render. If a value is a pure function of reactive state and is read in the template, make it computed.

- **Use `v-show` for frequently toggled elements, `v-if` for rarely shown ones.** `v-if` adds and removes DOM nodes (and re-runs child setup); `v-show` just flips a CSS `display`. A chart or panel the user toggles repeatedly should be `v-show`.

- **Debounce watchers that trigger expensive work.** A `watch` on a search box or slider that fires an API call or heavy recompute on every keystroke/drag should be debounced. If a value can change rapidly and drives a network call, flag it.

- **Watch for reactivity footguns that force needless work or break silently:** destructuring props in `setup` (loses reactivity), holding derived state in a `ref` that a `watch` keeps in sync (should be `computed` -- one source of truth), and unvalidated `new Date(x).getMonth()` on external data (throws or yields `NaN`).

## Code-reuse checklist

Duplication is cheap to create and expensive to maintain: the second copy is where the bug fix gets forgotten. Look across files, not just within one.

- **Helper functions defined in more than one component** (e.g. a `formatDate`, a currency formatter, a status-to-class map) should move to `client/src/utils/` if pure, or a composable if they touch reactive state. The scanner flags cross-file name collisions; verify the bodies match before recommending extraction.

- **Stateful logic shared across components** (filters, auth, i18n, anything with refs several views read) belongs in a composable under `client/src/composables/`, following the existing `useFilters` pattern. If two components keep the same refs in sync by hand, that is a composable waiting to happen.

- **Repeated template blocks** (a table row layout, a modal shell, an expandable items dropdown copied between views) should become a child component. Repetition in markup is as costly as repetition in logic.

- **Repeated API call shapes** should live in the central `client/src/api.js` client, not be re-implemented per component.

- **Distinguish real duplication from expected repetition.** Local `loading` / `error` / `data` refs recurring in every view is the *correct* pattern, not a finding. Focus on logic and markup that is genuinely the same thing copied, where a single source would prevent drift.

## Report structure

Use this exact template so the output is scannable and the developer can triage by impact:

```
# Vue Optimization Report -- <scope>

## Summary
<1-3 sentences: how many findings, where the biggest wins are>

## Performance
### [High|Medium|Low] <short title>
- Location: <file:line>
- Issue: <what is happening>
- Why it matters: <the concrete cost -- wrong DOM reuse, render-loop recompute, etc.>
- Fix: <the specific change, with a code sketch if it helps>

## Code Reuse
### [High|Medium|Low] <short title>
- Location: <file:line> (and the duplicate at <file:line>)
- Issue: <what is duplicated>
- Why it matters: <maintenance cost / drift risk>
- Fix: <where the shared version should live and what it looks like>
```

Order findings within each section by severity, highest first. If a section has no findings, say so briefly rather than padding it. Prefer a handful of high-signal findings over an exhaustive list of nitpicks -- a report the developer will actually act on beats one they will skim and close.
