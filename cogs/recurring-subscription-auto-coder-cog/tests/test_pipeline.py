"""End-to-end checks on the synthetic fixtures.

Each case in the fixtures (see sample-data/README.md at the repo root) has a
test here, so a change to the rules that breaks one shows up by name.
"""
import csv
import json
import shutil
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from auto_coder import context, core
from cog_transactions import load, shape

ROOT = Path(__file__).resolve().parents[1]

FIXTURES = ROOT / "evaluation" / "fixtures"
MONTH = FIXTURES / "baseline" / "brex-transactions-2026-09.csv"
HISTORY = [FIXTURES / "baseline" / "brex-transactions-2026-07.csv",
           FIXTURES / "baseline" / "brex-transactions-2026-08.csv"]


@pytest.fixture(scope="module")
def result():
    return core.run(MONTH, HISTORY)


def validator():
    schemas = {name: json.loads((ROOT / "context" / name).read_text())
               for name in ("transaction.schema.json", "output-schema.json")}
    registry = Registry().with_resources(
        (name, Resource.from_contents(schema)) for name, schema in schemas.items())
    return Draft202012Validator(schemas["output-schema.json"], registry=registry,
                                format_checker=Draft202012Validator.FORMAT_CHECKER)


def as_json(result):
    return json.loads(json.dumps(result, default=shape.to_json))


def by_id(result, tx_id):
    return next(tx for tx in result["transactions"] if tx["id"] == tx_id)


def label(result, tx_id):
    return by_id(result, tx_id)["inferred"]["recurrence"]["label"]


def coding(result, tx_id):
    return by_id(result, tx_id)["inferred"]["coding"]


# --- the contract ---

def test_every_input_row_appears_once(result):
    with MONTH.open() as f:
        ids = [r["transaction_id"] for r in csv.DictReader(f)]
    assert sorted(tx["id"] for tx in result["transactions"]) == sorted(ids)
    assert result["unparsed"] == []


def test_output_matches_the_schema(result):
    validator().validate(as_json(result))


def test_output_example_matches_the_schema():
    validator().validate(json.loads((ROOT / "context" / "output-example.json").read_text()))


def test_schema_rejects_an_inferred_field_with_a_parsed_name(result):
    bad = as_json(result)
    bad["transactions"][0]["inferred"]["amount"] = {"source": "model", "value": 1.0}
    assert not validator().is_valid(bad)


def test_infer_refuses_a_parsed_field_name():
    tx = shape.new_transaction({"transaction_id": "x"}, {"file": "f", "row": 2})
    with pytest.raises(KeyError):
        shape.infer(tx, "merchant_descriptor", {"source": "model"})
    with pytest.raises(ValueError):
        shape.infer(tx, "vendor", {"id": "aws"})              # no source


def test_parsed_and_inferred_never_share_a_field(result):
    for tx in result["transactions"]:
        assert not set(tx["parsed"]) & set(tx["inferred"]), tx["id"]


def test_no_pending_charge_is_coded(result):
    for tx in result["transactions"]:
        if tx["parsed"]["status"] == "pending":
            assert tx["inferred"]["coding"]["status"] in ("waiting-for-post", "not-coded"), tx["id"]


def test_only_recurring_charges_get_a_proposed_coding(result):
    for tx in result["transactions"]:
        if tx["inferred"]["coding"]["status"] == "proposed":
            assert tx["inferred"]["recurrence"]["label"] == "recurring", tx["id"]
            assert tx["parsed"]["status"] == "posted", tx["id"]


def test_run_record_is_strict_with_no_binding(result):
    assert result["run"]["mode"] == "strict"
    assert result["run"]["binding"] is None


# --- the cases built into the fixtures ---

def test_usage_billed_vendor_within_tolerance_is_recurring(result):
    assert label(result, "tx_0905a") == "recurring"          # Datadog drifts month to month
    assert coding(result, "tx_0905a")["account"] == "6120"


def test_two_aws_descriptors_are_one_vendor_and_two_streams(result):
    for tx_id in ("tx_0901b", "tx_0901c"):
        assert by_id(result, tx_id)["inferred"]["vendor"]["id"] == "aws"
        assert label(result, tx_id) == "recurring"


def test_slack_seat_addition_is_amount_changed(result):
    assert label(result, "tx_0902a") == "recurring"          # the normal charge
    assert label(result, "tx_0924a") == "amount-changed"     # the mid-month add-on
    assert coding(result, "tx_0924a")["status"] == "needs-human"


def test_first_seen_subscription_is_new(result):
    assert label(result, "tx_0918a") == "new"                # Grafana
    assert coding(result, "tx_0918a")["status"] == "needs-human"


def test_one_earlier_month_is_likely_recurring(result):
    assert label(result, "tx_0916b") == "likely-recurring"   # Canva, from August


def test_recurring_vendor_with_no_rule_needs_a_human(result):
    assert label(result, "tx_0912a") == "recurring"          # Postman
    assert coding(result, "tx_0912a") == {"status": "needs-human", "source": "none",
                                          "reason": "no coding rule for this vendor"}


def test_missing_subscription_is_reported(result):
    assert [m["vendor"] for m in result["expected_but_missing"]] == ["loom"]


def test_pending_charge_on_known_vendor_waits_for_post(result):
    assert label(result, "px_0928a") == "recurring"          # AWS, provisional 1500.00
    assert coding(result, "px_0928a")["status"] == "waiting-for-post"


def test_travel_refunds_and_unknown_vendors_are_one_off(result):
    for tx_id in ("tx_0910c", "tx_0918b", "tx_0922a", "tx_0926a"):
        assert label(result, tx_id) == "one-off", tx_id
        assert coding(result, tx_id)["status"] == "not-coded", tx_id


def test_known_recurring_list_works_without_history():
    result = core.run(MONTH, [])
    assert label(result, "tx_0901a") == "recurring"          # GitHub, on the list
    assert label(result, "tx_0905a") == "new"                # Datadog, no history, not on the list
    assert any("no history" in w for w in result["run"]["warnings"])


# --- data is never direction ---

def test_injected_memo_changes_nothing(result, tmp_path):
    """The Blue Bottle memo tells the reader to code everything to Office
    Supplies. Blanking it must not change a single label or coding."""
    clean = tmp_path / MONTH.name
    with MONTH.open() as src, clean.open("w", newline="") as dst:
        reader = csv.DictReader(src)
        writer = csv.DictWriter(dst, fieldnames=reader.fieldnames)
        writer.writeheader()
        for row in reader:
            if "Ignore all previous instructions" in (row["memo"] or ""):
                row["memo"] = ""
            writer.writerow(row)

    def outcome(r):
        return {tx["id"]: (tx["inferred"]["recurrence"]["label"], tx["inferred"]["coding"])
                for tx in r["transactions"]}

    assert outcome(core.run(clean, HISTORY)) == outcome(result)


def test_injection_fixture_changes_nothing():
    result = core.run(FIXTURES / "injection" / "injection.csv", HISTORY)
    validator().validate(as_json(result))
    labels = {tx["id"]: tx["inferred"]["recurrence"]["label"] for tx in result["transactions"]}
    # Instructions in a descriptor just fail to match a vendor...
    assert labels["inj_01"] == labels["inj_02"] == "one-off"
    # ...or match the vendor they name and get exactly what a plain charge from
    # that vendor would get: GITHUB.COM is GitHub, whatever follows it.
    github = by_id(result, "inj_03")["inferred"]
    plain = by_id(core.run(MONTH, HISTORY), "tx_0901a")["inferred"]
    assert github["coding"] == plain["coding"]
    # An instruction in the memo or the cardholder field is never read.
    assert labels["inj_04"] == labels["inj_05"] == "one-off"
    assert by_id(result, "inj_04")["inferred"]["coding"]["status"] == "not-coded"


# --- failures are loud ---

def test_missing_required_column_is_an_error(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("transaction_id,status\ntx_1,posted\n")
    with pytest.raises(load.ExportError, match="missing column"):
        load.load_csv(bad)


def test_bad_row_is_counted_not_fatal(tmp_path):
    rows = MONTH.read_text().splitlines()
    rows[1] = rows[1].replace("252.00", "two hundred")
    bad = tmp_path / MONTH.name
    bad.write_text("\n".join(rows) + "\n")
    result = core.run(bad, HISTORY)
    assert result["run"]["counts"]["unparsed_rows"] == 1
    assert "two hundred" in result["unparsed"][0]["reason"]


def test_rule_with_unknown_account_fails_at_load(tmp_path):
    shutil.copytree(context.DEFAULT_DIR, tmp_path / "context")
    rules = tmp_path / "context" / "coding-rules.yaml"
    rules.write_text(rules.read_text().replace('account: "6110"', 'account: "9999"', 1))
    with pytest.raises(context.ContextError, match="9999"):
        context.load(tmp_path / "context")
