"""Load and check the files in context/: cards, chase policy, message template,
and the shared vendor patterns.

Everything is checked once, at load, so a typo fails the run instead of
producing a message with a broken placeholder or a card routed nowhere.
"""
import string
from pathlib import Path

import yaml

from cog_transactions.vendors import DEFAULT_SUBSCRIPTION_CATEGORIES, compile_vendors

COG_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DIR = COG_ROOT / "context"
TEMPLATE_NAME = "message-template.md"

# What a template may use. See context/README.md.
PLACEHOLDERS = {
    "card_last4", "cardholder", "channel", "merchant", "descriptor", "vendor", "amount", "currency",
    "original_amount", "date", "status", "status_note", "questions", "reply_form",
    "transaction_id",
}


class ContextError(ValueError):
    pass


def check_override_dir(override_dir, names):
    """Fail loudly instead of silently falling back to the defaults."""
    if override_dir is None:
        return
    d = Path(override_dir)
    if d.is_file():
        raise ContextError(f"--context takes a folder, not a file: use --context {d.parent}")
    if not d.is_dir():
        raise ContextError(f"--context folder not found: {d}")
    if not any((d / n).exists() for n in names):
        raise ContextError(f"--context folder {d} has none of: {', '.join(names)}")


def _pick(override_dir, filename):
    """The override folder's copy of a file if it has one, else this Cog's default."""
    own = Path(override_dir) / filename if override_dir else None
    return own if own and own.exists() else DEFAULT_DIR / filename


def _yaml(path):
    if not path.exists():
        raise ContextError(f"missing context file {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_template(path):
    path = Path(path)
    if not path.exists():
        raise ContextError(f"missing message template {path}")
    text = path.read_text(encoding="utf-8")
    try:
        used = {field for _, field, _, _ in string.Formatter().parse(text) if field is not None}
    except ValueError as e:
        raise ContextError(f"{path.name}: {e} (write {{{{ or }}}} for a literal brace)") from e
    unknown = used - PLACEHOLDERS
    if unknown:
        raise ContextError(f"{path.name}: unknown placeholder(s) {', '.join(sorted(unknown))}; "
                           f"allowed: {', '.join(sorted(PLACEHOLDERS))}")
    return text


def load(override_dir=None, template_path=None):
    """Read the context files. A file in `override_dir` replaces this Cog's
    default, file by file, so real cards, policy, template or vendor list can
    live outside the repo, in private/. `template_path` wins over both."""
    check_override_dir(override_dir, ["vendors.yaml", "cards.yaml", "chase-policy.yaml", TEMPLATE_NAME])
    sources = {name: _pick(override_dir, f"{name}.yaml") for name in ("vendors", "cards", "chase-policy")}
    raw = {name: _yaml(path) for name, path in sources.items()}

    try:
        vendors = compile_vendors(raw["vendors"].get("vendors", []))
    except ValueError as e:
        raise ContextError(f"vendors: {e}") from e

    cards = {}
    for c in raw["cards"].get("cards", []):
        last4 = str(c["last4"])
        if last4 in cards:
            raise ContextError(f"cards: {last4} listed twice")
        cards[last4] = {"cardholder": c.get("cardholder"), "channel": c.get("channel"),
                        "users": list(c.get("users") or []), "shared": bool(c.get("shared"))}

    policy = raw["chase-policy"]
    ask_for = policy.get("ask_for") or []
    if not ask_for:
        raise ContextError("chase-policy: ask_for is empty, so messages would ask nothing")
    for item in ask_for:
        if item.get("skip_if") not in (None, "receipt_attached"):
            raise ContextError(f"chase-policy: unknown skip_if {item['skip_if']!r}")

    template_path = Path(template_path) if template_path else _pick(override_dir, TEMPLATE_NAME)
    return {
        "vendors": vendors,
        "cards": cards,
        "subscription_categories": tuple(raw["vendors"].get("brex_subscription_categories")
                                         or DEFAULT_SUBSCRIPTION_CATEGORIES),
        "policy": {
            "skip_refunds": bool(policy.get("skip_refunds", True)),
            "skip_coded_by_auto_coder": bool(policy.get("skip_coded_by_auto_coder", True)),
            "skip_when_receipt_and_memo": bool(policy.get("skip_when_receipt_and_memo", False)),
            "ask_for": ask_for,
        },
        "template": load_template(template_path),
        "template_file": template_path.name,
        "versions": {name: {"version": str(raw[name].get("version")),
                            "status": raw[name].get("status", "unspecified"),
                            "from": "override" if sources[name].parent != DEFAULT_DIR else "default"}
                     for name in raw},
    }
