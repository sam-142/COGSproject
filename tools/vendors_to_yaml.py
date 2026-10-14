"""Turn a plain vendor list into a vendors.yaml the Cogs can use.

Run it yourself, on files that stay in private/:

    python3 tools/vendors_to_yaml.py private/vendors.txt private/context/vendors.yaml

Then point either Cog at that folder with `--context private/context`. Files in
that folder replace the Cog's defaults one by one, so this vendors.yaml is used
and everything else stays as it was.

Input, either:
  - a text file, one vendor name per line (blank lines and lines starting # are skipped); or
  - a CSV whose first column is the vendor name, optionally with columns called
    `category` and `billing` (case doesn't matter):
      category  default `subscription`, the only category the auto-coder can
                label recurring. Use e.g. `travel` to keep a vendor out;
      billing   `usage` (amount varies: cloud, APIs) or `fixed` (same price every
                month, so a change goes to a person). Left blank, it counts as usage.

Names are matched against the start of Brex's Merchant Name (then the
statement descriptor), ignoring case. So write them the way Brex's Merchant Name
column writes them: "Amazon Web Services", not "AWS".

Prints only counts, never names. Standard library only; no network.
"""
import csv
import json
import re
import sys
from pathlib import Path


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def read_names(path):
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".csv":
        rows = list(csv.reader(text.splitlines()))
        if not rows:
            return []
        header = [h.strip().lower() for h in rows[0]]
        has_header = ("category" in header or "billing" in header
                      or header[0] in ("vendor", "name", "vendor name", "merchant"))
        col = lambda name: header.index(name) if name in header else None
        cat, bill = col("category"), col("billing")
        get = lambda r, i: r[i].strip() if i is not None and i < len(r) else ""
        body = rows[1:] if has_header else rows
        return [(r[0].strip(), get(r, cat), get(r, bill)) for r in body if r and r[0].strip()]
    return [(line.strip(), "", "") for line in text.splitlines()
            if line.strip() and not line.strip().startswith("#")]


def main(src, dst):
    src, dst = Path(src), Path(dst)
    entries, seen, dupes = [], set(), 0
    for name, category, billing in read_names(src):
        key = slug(name)
        if not key or key in seen:
            dupes += bool(key)
            continue
        seen.add(key)
        entry = {"name": name}
        if category:
            entry["category"] = category.lower()
        if billing:
            billing = billing.lower()
            if billing not in ("usage", "fixed"):
                sys.exit(f"billing must be usage or fixed (row {len(entries) + dupes + 1})")
            entry["billing"] = billing
        entries.append(entry)

    # JSON strings are valid YAML, and quote anything awkward (colons, #, quotes).
    lines = [
        "# Real vendor list, made by tools/vendors_to_yaml.py. Keep it in private/.",
        "# Each name is matched against the start of Brex's Merchant Name, ignoring case.",
        'version: "1"',
        "status: real",
        "",
        "vendors:",
    ] + ["  - {" + ", ".join(f"{k}: {json.dumps(v)}" for k, v in e.items()) + "}" for e in entries]
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text("\n".join(lines) + "\n", encoding="utf-8")
    cats = sorted({e.get("category", "subscription") for e in entries})
    fixed = sum(e.get("billing") == "fixed" for e in entries)
    print(f"wrote {len(entries)} vendors to {dst.name} ({dupes} duplicates skipped); "
          f"categories used: {', '.join(cats) or '-'}; {fixed} fixed-price, "
          f"{len(entries) - fixed} usage-billed or unset")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: python3 tools/vendors_to_yaml.py <list.txt|list.csv> <output vendors.yaml>")
    main(*sys.argv[1:])
