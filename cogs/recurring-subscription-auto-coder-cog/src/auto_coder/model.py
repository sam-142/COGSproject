"""Where the model is, and proof that it answers.

The binding is resolved in this order, later entries winning:

    1. defaults in this file     a model on this machine; statements stay local
    2. model.json                written by `pixi run use`, survives new shells
    3. COG_MODEL_* env vars      an explicit one-off override

Every result records the binding and which of these it came from. Without that,
a run that silently talked to the wrong model looks exactly like a good run.

API keys are never written to model.json. It holds the *name* of the variable
that holds the key, so the file is safe to share.
"""
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

COG_ROOT = Path(__file__).resolve().parents[2]
CONFIG = COG_ROOT / "model.json"

# Accounting asked that statements not go to ChatGPT or the public cloud, so the
# default is local. 8080 is llama-server's default port. "local" is a placeholder
# alias: set the real served alias with `pixi run use`, or provenance is useless.
DEFAULTS = {
    "endpoint": "http://127.0.0.1:8080/v1",
    "model": "local",
    "api_key_env": None,
}

PRESETS = {
    "local": dict(DEFAULTS),
    "ollama": {"endpoint": "http://127.0.0.1:11434/v1", "model": "qwen2.5:3b", "api_key_env": None},
}


def load_binding():
    binding = dict(DEFAULTS)
    source = "default"
    if CONFIG.exists():
        binding.update(json.loads(CONFIG.read_text()))
        source = "model.json"
    for key, var in (("endpoint", "COG_MODEL_ENDPOINT"), ("model", "COG_MODEL_NAME")):
        if os.environ.get(var):
            binding[key] = os.environ[var]
            source = "env"
    binding["source"] = source
    return binding


def api_key(binding):
    if os.environ.get("COG_MODEL_API_KEY"):
        return os.environ["COG_MODEL_API_KEY"]
    env = binding.get("api_key_env")
    return os.environ.get(env, "") if env else ""


def write_binding(endpoint, model, api_key_env):
    cfg = {"endpoint": endpoint, "model": model, "api_key_env": api_key_env}
    CONFIG.write_text(json.dumps(cfg, indent=2) + "\n")
    return cfg


def check(binding, timeout=30):
    """One-token completion. Returns a result dict; never raises on a bad endpoint."""
    url = binding["endpoint"].rstrip("/") + "/chat/completions"
    body = json.dumps({
        "model": binding["model"],
        "messages": [{"role": "user", "content": "Reply with OK."}],
        "max_tokens": 1,
        "temperature": 0,
    }).encode()
    headers = {"Content-Type": "application/json"}
    key = api_key(binding)
    if key:
        headers["Authorization"] = f"Bearer {key}"

    result = {
        "ok": False,
        "binding": {
            "endpoint": binding["endpoint"],
            "model_requested": binding["model"],
            "model_echoed": None,
            "source": binding["source"],
        },
        "error": None,
    }
    started = time.monotonic()
    try:
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            reply = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        result["error"] = f"HTTP {e.code}: {e.read().decode(errors='replace')[:200]}"
        return result
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        result["error"] = f"cannot reach {url}: {getattr(e, 'reason', e)}"
        return result
    except json.JSONDecodeError:
        result["error"] = f"{url} did not return JSON"
        return result

    result["latency_s"] = round(time.monotonic() - started, 2)
    result["binding"]["model_echoed"] = reply.get("model")
    if not reply.get("choices"):
        result["error"] = "reply had no choices"
        return result
    result["ok"] = True
    return result
