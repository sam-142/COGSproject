# context

**Invented**, like everything in `sample-data/`. These are the lookup files the tests and
`pixi run demo` run on. They are not the Cogs' defaults: those are empty, so a run on real data
never uses invented vendors, codings or cardholders.

| File | Used by | Copied to |
|---|---|---|
| `vendors.yaml` | both | each Cog's `evaluation/fixtures/context/` |
| `known-recurring.yaml`, `coding-rules.yaml`, `chart-of-accounts.yaml` | auto-coder | its `evaluation/fixtures/context/` |
| `cards.yaml` | chase-list builder | its `evaluation/fixtures/context/` |

Each Cog's tests fail if a copy drifts from the file here.
