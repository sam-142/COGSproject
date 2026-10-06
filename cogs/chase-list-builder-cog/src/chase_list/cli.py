"""Command line. Thin on purpose: the logic lives elsewhere, so other interfaces
can be added later without rewriting it."""
import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

from cog_transactions import combine, load
from chase_list import context, core, log, report

DEFAULT_LOG = "chase-log.json"


def _path(p):
    # pixi runs tasks from the Cog root, so a relative path the user typed is
    # resolved against where they typed it (pixi sets INIT_CWD to that).
    p = Path(p)
    return p if p.is_absolute() else Path(os.environ.get("INIT_CWD", ".")) / p


def cmd_draft(args):
    log_path = None if args.no_log else _path(args.log)
    try:
        result = core.run(
            [_path(p) for p in args.exports],
            coded_path=_path(args.coded) if args.coded else None,
            log_path=log_path,
            context_dir=_path(args.context) if args.context else context.DEFAULT_DIR,
            template_path=_path(args.template) if args.template else None,
        )
    except (load.ExportError, context.ContextError, ValueError, FileNotFoundError) as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(2)
    paths = report.write(result, _path(args.out))
    print(report.summary(result))
    print("\n" + "\n".join(f"wrote {p}" for p in paths))


def cmd_sent(args):
    """Record drafts a person has actually sent, so they aren't drafted again."""
    result = json.loads(_path(args.result).read_text(encoding="utf-8"))
    if result.get("run", {}).get("cog") != "chase-list-builder-cog":
        sys.exit(f"error: {args.result} isn't output from chase-list-builder-cog")
    wanted = set(args.only or [])
    drafts = [d for d in result["drafts"]
              if not wanted or d["id"] in wanted or d["transaction_id"] in wanted]
    unknown = wanted - {d["id"] for d in drafts} - {d["transaction_id"] for d in drafts}
    if unknown:
        sys.exit(f"error: not in this result: {', '.join(sorted(unknown))}")

    log_path = _path(args.log)
    entries = log.read(log_path)
    have = {e["transaction_id"] for e in entries}
    txs = {tx["id"]: tx for tx in result["transactions"]}
    added = 0
    for d in drafts:
        if d["transaction_id"] in have:
            continue
        tx = txs[d["transaction_id"]]
        tx["parsed"]["transaction_date"] = date.fromisoformat(tx["parsed"]["transaction_date"])
        entries.append({**combine.summary(tx), "status": tx["parsed"]["status"],
                        "channel": d["channel"], "sent_on": date.today().isoformat()})
        added += 1
    log.write(log_path, entries)
    print(f"recorded {added} sent message(s) in {log_path} ({len(entries)} in total)")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="chase_list")
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("draft", help="find charges to chase and draft a message for each (sends nothing)")
    p.add_argument("exports", nargs="+", help="one or more CSV exports, any date range, may overlap")
    p.add_argument("--coded", help="the auto-coder's .recurring.json output, to skip what it coded")
    p.add_argument("--log", default=DEFAULT_LOG, help=f"chase log (default: ./{DEFAULT_LOG})")
    p.add_argument("--no-log", action="store_true", help="ignore the chase log for this run")
    p.add_argument("--context", help="directory of context files (default: this Cog's context/)")
    p.add_argument("--template", help="message template to use instead of context/message-template.md")
    p.add_argument("--out", default="output", help="where to write results (default: ./output)")
    p.set_defaults(func=cmd_draft)

    p = sub.add_parser("sent", help="record which drafts a person actually sent")
    p.add_argument("result", help="the .chase.json file the drafts came from")
    p.add_argument("--only", nargs="+", help="draft or transaction ids; default is every draft")
    p.add_argument("--log", default=DEFAULT_LOG, help=f"chase log (default: ./{DEFAULT_LOG})")
    p.set_defaults(func=cmd_sent)

    args = ap.parse_args(argv)
    args.func(args)
