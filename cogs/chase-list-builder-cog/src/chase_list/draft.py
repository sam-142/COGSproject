"""Fill the message template for each charge being chased.

Values from the export are inserted as text and never interpreted. They are
also defused for Slack: a descriptor containing `@channel` or `<!here>` would
otherwise ping a whole channel when the draft is pasted in.
"""
from chase_list.context import PLACEHOLDERS


def _defuse(value):
    return (str(value).replace("@", "(at)").replace("<", "‹").replace(">", "›")
            .replace("`", "'"))


def _values(tx, questions):
    p, inf = tx["parsed"], tx["inferred"]
    pending = p["status"] == "pending"
    original = (f" (originally {p['original_amount']:,.2f} {p['original_currency']})"
                if p["original_amount"] and p["original_currency"] else "")
    form = [f"ref: {tx['id']}"] + [f"{q['key']}:" for q in questions]
    values = {
        "card_last4": p["card_last4"] or "????",
        "cardholder": p["cardholder"] or "",
        "channel": inf["route"]["channel"] or "",
        "merchant": p["merchant_descriptor"],
        "vendor": inf["vendor"]["id"] or p["merchant_descriptor"],
        "amount": f"{p['amount']:,.2f}",
        "currency": p["currency"] or "",
        "original_amount": original,
        "date": p["transaction_date"].isoformat(),
        "status": p["status"],
        "status_note": " (pending: the amount may change when it settles)" if pending else "",
        "questions": "\n".join(f"• {q['question']}" for q in questions),
        "reply_form": "\n".join(form),
        "transaction_id": tx["id"],
    }
    assert set(values) == PLACEHOLDERS
    # Defuse what came from the export. The questions and the form come from
    # context/, which a person on the team wrote.
    for key in ("cardholder", "merchant", "vendor", "currency", "transaction_id"):
        values[key] = _defuse(values[key])
    values["reply_form"] = "\n".join([f"ref: {_defuse(tx['id'])}"] + form[1:])
    return values


def drafts(transactions, ctx):
    out = []
    by_key = {q["key"]: q for q in ctx["policy"]["ask_for"]}
    for tx in transactions:
        chase = tx["inferred"]["chase"]
        if chase["status"] not in ("draft", "needs-routing"):
            continue
        questions = [by_key[k] for k in chase["ask_for"]]
        out.append({
            "id": f"draft-{tx['id']}",
            "transaction_id": tx["id"],
            "channel": tx["inferred"]["route"]["channel"],
            "needs_routing": chase["status"] == "needs-routing",
            "text": ctx["template"].format_map(_values(tx, questions)).strip() + "\n",
        })
    return out
