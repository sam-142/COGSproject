# app

A small web page for the accounting team, over both Cogs. Drop in this month's Brex statement
(and earlier months), press **Run**, and get back:

- **the updated statement**: the Brex CSV with subscription memos filled in, ready to upload to
  QuickBooks (from the recurring subscription auto-coder);
- **the review report**: every subscription charge, why it counts as one, and what to check;
- **a Slack draft for every other charge without a memo** (from the chase-list builder), each with
  its channel and a Copy button. Nothing is sent.

## Starting it

From the repo root:

```bash
pixi run --manifest-path app/pixi.toml ui --context private/context --log private/chase-log.json
```

The page opens at `http://127.0.0.1:8765/`. Both options are optional:

| Option | What it does |
|---|---|
| `--context DIR` | the folder of real context files (vendor list, cards and channels, coding rules), passed to both Cogs. Without it, both use their empty defaults, and every draft has no channel |
| `--log FILE` | the chase-list builder's chase log, so charges already chased aren't drafted again. Without it, every charge without a memo is drafted |
| `--port N` | another port, if 8765 is taken |
| `--no-browser` | don't open the page automatically |

Stop it with **Ctrl+C**. Everything uploaded, and every result, is deleted when it stops, so save the
downloads first.

Recording which drafts were actually sent is still done on the command line, with the chase-list
builder's `pixi run sent`.

## How it works

The app contains **no Cog logic and imports no Cog code**. It runs each Cog exactly as a person would
from the terminal, through its pixi tasks, and reads the files they write:

```
statement (+ earlier months)
  -> auto-coder:          pixi run code <statement> --history <earlier...> --out <run>/auto-coder
  -> chase-list builder:  pixi run draft <run>/auto-coder/<statement>.upload.csv --out <run>/chase-list
  -> the page shows both results and offers every output file for download
```

Each Cog runs in its own environment, and the page can't drift from what the command line does. A
Cog's error (a missing column, a bad context folder) is shown on the page as the Cog's own one-line
message.

## Keeping real data local

- It listens on `127.0.0.1` only: nothing outside this computer can reach it.
- The page loads nothing from the internet (no fonts, scripts or styles from elsewhere), and a strict
  Content-Security-Policy stops it from talking to anything but this server.
- Every run and download needs a random per-session token that only the page knows, so another website
  open in the same browser can't send it files.
- Uploads and results live in a temporary folder, deleted however it stops: Ctrl+C, closing the
  terminal, or a kill signal.
- Statement text is always shown as text, never as part of the page.

## Files

| File | What |
|---|---|
| `server.py` | the local web server; standard library only |
| `static/index.html` | the page; inline CSS and JS, nothing loaded from elsewhere |
| `tests/test_app.py` | drives the page over HTTP with both Cogs run for real on their synthetic test data |
| `pixi.toml` | `ui` and `test` tasks; only Python itself as a dependency |
