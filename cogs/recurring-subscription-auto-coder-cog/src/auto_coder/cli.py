"""Command line. Thin on purpose: the logic lives elsewhere, so other interfaces
can be added later without rewriting it."""
import argparse
import json
import sys

from auto_coder import model


def cmd_check(args):
    binding = model.load_binding()
    result = model.check(binding)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        b = result["binding"]
        print(f"endpoint  : {b['endpoint']}")
        print(f"requested : {b['model_requested']}")
        print(f"echoed    : {b['model_echoed'] or '-'}")
        print(f"source    : {b['source']}")
        if result["ok"]:
            print(f"ok        : one-token completion in {result['latency_s']}s")
        else:
            print(f"FAILED    : {result['error']}")
            print("\nStart a local model server, or point the Cog at one: pixi run use --help")
    if result["ok"] and result["binding"]["model_echoed"] != result["binding"]["model_requested"]:
        # Some servers echo a file path or their own name instead of the alias.
        # The completion worked, but provenance would be wrong, so say so.
        print("\nWARNING: the server echoed a different model id than requested. "
              "Set the served model alias on the server.", file=sys.stderr)
    sys.exit(0 if result["ok"] else 1)


def cmd_use(args):
    if not (args.preset or args.endpoint):
        b = model.load_binding()
        print(f"endpoint : {b['endpoint']}")
        print(f"model    : {b['model']}")
        print(f"key env  : {b.get('api_key_env') or '-'}")
        print(f"source   : {b['source']}")
        print(f"\npresets  : {', '.join(sorted(model.PRESETS))}")
        return
    cfg = dict(model.PRESETS.get(args.preset, model.DEFAULTS))
    for key, val in (("endpoint", args.endpoint), ("model", args.model),
                     ("api_key_env", args.api_key_env)):
        if val:
            cfg[key] = val
    model.write_binding(cfg["endpoint"], cfg["model"], cfg["api_key_env"])
    print(f"wrote {model.CONFIG.name}: {cfg['endpoint']} model={cfg['model']}")
    print("next: pixi run check")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="auto_coder")
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("check", help="prove the model answers with a one-token completion")
    p.add_argument("--json", action="store_true", help="print the full result as JSON")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("use", help="show or set the model binding")
    p.add_argument("preset", nargs="?", choices=sorted(model.PRESETS))
    p.add_argument("--endpoint", help="OpenAI-compatible base URL")
    p.add_argument("--model", help="model id the server answers to")
    p.add_argument("--api-key-env", help="name of the env var holding the key (never the key)")
    p.set_defaults(func=cmd_use)

    args = ap.parse_args(argv)
    args.func(args)
