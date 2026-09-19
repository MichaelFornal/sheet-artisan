"""The AI step: structured output from `claude -p`, cached so a crawl never pays twice.

    llm = LLM("data/llm_cache")                       # model defaults to haiku
    llm.ask("Classify this business: ...", schema)    # -> dict matching schema
    llm.map_batched(rows, instruction="Categorize each product.",
                    item_schema={...}, render=lambda r: {"id": r["id"], "name": r["name"]})

Every answer is cached by (prompt, schema, model); batched answers are cached per ITEM, so
re-batching or resuming never re-asks. `offline=True` replays the cache only. Use it only where it
earns its place (see playbook/b2-ideation.md) and label every column it fills as AI-derived.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


class LLMError(Exception):
    pass


class LLMCacheMiss(LLMError):
    pass


_TYPES = {"string": str, "boolean": bool, "object": dict, "array": list, "null": type(None)}


def _is_type(obj, t):
    if t == "integer":
        return isinstance(obj, int) and not isinstance(obj, bool)
    if t == "number":
        return isinstance(obj, (int, float)) and not isinstance(obj, bool)
    return isinstance(obj, _TYPES[t]) if t in _TYPES else True


def validate(obj, schema, path="$"):
    """A small JSON-schema subset: type, properties, required, items, enum."""
    t = schema.get("type")
    if t is not None and not any(_is_type(obj, one) for one in (t if isinstance(t, list) else [t])):
        raise LLMError(f"{path}: expected {t}, got {type(obj).__name__}")
    if "enum" in schema and obj not in schema["enum"]:
        raise LLMError(f"{path}: {obj!r} not in {schema['enum']}")
    if isinstance(obj, dict):
        for k in schema.get("required", []):
            if k not in obj:
                raise LLMError(f"{path}: missing required key {k!r}")
        for k, sub in schema.get("properties", {}).items():
            if k in obj:
                validate(obj[k], sub, f"{path}.{k}")
    if isinstance(obj, list) and "items" in schema:
        for i, v in enumerate(obj):
            validate(v, schema["items"], f"{path}[{i}]")
    return obj


def claude_runner(prompt, schema, model, timeout=600):
    exe = shutil.which("claude")
    if not exe:
        raise LLMError("the `claude` CLI is not on PATH (install Claude Code, or run with OFFLINE=1)")
    cmd = [exe, "-p", prompt, "--output-format", "json", "--json-schema", json.dumps(schema)]
    if model:
        cmd += ["--model", model]
    # Run outside any project so no CLAUDE.md is loaded into every call.
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=tempfile.gettempdir())
    if p.returncode != 0:
        raise LLMError(f"claude exited {p.returncode}: {p.stderr.strip()[:300]}")
    try:
        d = json.loads(p.stdout)
    except ValueError:
        raise LLMError(f"claude returned non-JSON: {p.stdout[:300]}")
    if d.get("is_error") or d.get("structured_output") is None:
        raise LLMError(f"claude returned no structured output: {str(d.get('result'))[:300]}")
    return d["structured_output"]


class LLM:
    def __init__(self, cache_dir, model="haiku", offline=False, runner=None):
        self.cache_dir = Path(cache_dir)
        self.model = model
        self.offline = offline
        self.runner = runner or claude_runner
        self.stats = {"calls": 0, "cache_hits": 0, "missing": 0}
        self._lock = threading.Lock()

    @staticmethod
    def available():
        return shutil.which("claude") is not None

    # ---- cache ----
    def _key(self, *parts):
        return hashlib.sha256(json.dumps([*parts, self.model], sort_keys=True, default=str).encode()).hexdigest()

    def _read(self, key):
        p = self.cache_dir / key[:2] / f"{key}.json"
        if p.exists():
            with self._lock:
                self.stats["cache_hits"] += 1
            return json.loads(p.read_text())["output"]
        return None

    def _write(self, key, record):
        p = self.cache_dir / key[:2] / f"{key}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(f".tmp{os.getpid()}.{threading.get_ident()}")
        tmp.write_text(json.dumps(record))
        os.replace(tmp, p)

    def _run(self, prompt, schema, check=True):
        if self.offline:
            raise LLMCacheMiss("offline and not cached")
        with self._lock:
            self.stats["calls"] += 1
        out = self.runner(prompt, schema, self.model)
        return validate(out, schema) if check else out

    # ---- API ----
    def ask(self, prompt, schema):
        key = self._key(prompt, schema)
        hit = self._read(key)
        if hit is not None:
            return hit
        out = self._run(prompt, schema)
        self._write(key, {"prompt": prompt, "schema": schema, "model": self.model, "output": out})
        return out

    def map_batched(self, items, *, instruction, item_schema, id_key="id", render=None,
                    batch_size=20, workers=3):
        """Answer `instruction` for every item; returns {id: result or None}."""
        render = render or (lambda it: it)
        rendered = {}
        for it in items:
            r = render(it)
            if r.get(id_key) is None:
                raise LLMError(f"item without {id_key!r}: {r}")
            rendered[r[id_key]] = r
        out, todo = {}, []
        for iid, r in rendered.items():
            hit = self._read(self._key(instruction, item_schema, r))
            if hit is not None:
                out[iid] = hit
            else:
                todo.append(iid)
        if todo and self.offline:
            raise LLMCacheMiss(f"offline and {len(todo)} items not cached")

        props = dict(item_schema.get("properties", {}))
        props["id"] = {"type": ["string", "integer"]}
        batch_item = {**item_schema, "properties": props,
                      "required": sorted(set(item_schema.get("required", [])) | {"id"})}
        batch_schema = {"type": "object", "required": ["results"],
                        "properties": {"results": {"type": "array", "items": batch_item}}}

        def run_batch(ids):
            lines = "\n".join(json.dumps({"id": i, **{k: v for k, v in rendered[i].items() if k != id_key}},
                                         sort_keys=True, default=str) for i in ids)
            prompt = (f"{instruction}\n\nReturn exactly one entry in `results` per item below, copying "
                      f"its \"id\" exactly.\n\nItems (one JSON object per line):\n{lines}\n")
            try:  # items are validated one by one below, so one bad item can't sink the batch
                res = self._run(prompt, batch_schema, check=False).get("results")
            except LLMError:
                return {}
            if not isinstance(res, list):
                return {}
            got = {}
            for entry in res:
                if not isinstance(entry, dict):
                    continue
                iid = entry.get("id")
                match = next((i for i in ids if i == iid or str(i) == str(iid)), None)
                if match is None:
                    continue
                result = {k: v for k, v in entry.items() if k != "id"}
                try:
                    validate(result, item_schema)
                except LLMError:
                    continue
                got[match] = result
                self._write(self._key(instruction, item_schema, rendered[match]),
                            {"instruction": instruction, "item": rendered[match],
                             "model": self.model, "output": result})
            return got

        def run_all(ids, size):
            batches = [ids[i:i + size] for i in range(0, len(ids), size)]
            got = {}
            with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
                for part in ex.map(run_batch, batches):
                    got.update(part)
            return got

        got = run_all(todo, batch_size)
        missing = [i for i in todo if i not in got]
        if missing:  # one retry, in smaller batches
            got.update(run_all(missing, max(1, batch_size // 4)))
        for iid in todo:
            out[iid] = got.get(iid)
            if iid not in got:
                self.stats["missing"] += 1
        return {iid: out[iid] for iid in rendered}
