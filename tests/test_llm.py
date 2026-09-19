import tempfile
import unittest

from kit.llm import LLM, LLMCacheMiss, LLMError, validate

SCHEMA = {"type": "object", "properties": {"category": {"type": "string"}},
          "required": ["category"]}
ITEM_SCHEMA = {"type": "object", "properties": {"category": {"type": "string",
               "enum": ["food", "tools", "other"]}}, "required": ["category"]}


class FakeRunner:
    """Answers batch prompts by echoing ids; drops ids listed in `drop` (once per id)."""

    def __init__(self, drop=()):
        self.calls = 0
        self.drop = set(drop)

    def __call__(self, prompt, schema, model):
        self.calls += 1
        if "results" not in schema.get("properties", {}):
            return {"category": "food"}
        import json
        results = []
        for line in prompt.splitlines():
            if line.startswith("{"):
                item = json.loads(line)
                if item["id"] in self.drop:
                    self.drop.discard(item["id"])
                    continue
                results.append({"id": item["id"], "category": "tools" if "saw" in item["name"] else "other"})
        return {"results": results}


class LLMTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_ask_caches_by_prompt_schema_and_model(self):
        run = FakeRunner()
        llm = LLM(self.tmp, runner=run)
        self.assertEqual(llm.ask("classify x", SCHEMA), {"category": "food"})
        self.assertEqual(llm.ask("classify x", SCHEMA), {"category": "food"})
        self.assertEqual(run.calls, 1)
        LLM(self.tmp, runner=run, model="other").ask("classify x", SCHEMA)
        self.assertEqual(run.calls, 2)

    def test_offline_miss_raises(self):
        with self.assertRaises(LLMCacheMiss):
            LLM(self.tmp, offline=True, runner=FakeRunner()).ask("new prompt", SCHEMA)

    def test_invalid_output_raises_and_is_not_cached(self):
        bad = lambda prompt, schema, model: {"wrong": 1}
        with self.assertRaises(LLMError):
            LLM(self.tmp, runner=bad).ask("p", SCHEMA)
        with self.assertRaises(LLMCacheMiss):
            LLM(self.tmp, offline=True).ask("p", SCHEMA)

    def test_map_batched_returns_per_item_results_and_caches_per_item(self):
        items = [{"id": i, "name": n} for i, n in enumerate(["saw", "bread", "hammer", "saw blade", "x"])]
        run = FakeRunner()
        out = LLM(self.tmp, runner=run).map_batched(items, instruction="Categorize.",
                                                  item_schema=ITEM_SCHEMA, batch_size=2, workers=1)
        self.assertEqual(run.calls, 3)
        self.assertEqual(out[0], {"category": "tools"})
        self.assertEqual(out[1], {"category": "other"})
        self.assertEqual(out[3], {"category": "tools"})

        def explode(*a):
            raise AssertionError("should be served from cache")
        again = LLM(self.tmp, runner=explode).map_batched(items, instruction="Categorize.",
                                                        item_schema=ITEM_SCHEMA, batch_size=3)
        self.assertEqual(again, out)

    def test_missing_ids_are_retried_once_then_none(self):
        items = [{"id": "a", "name": "saw"}, {"id": "b", "name": "bread"}]
        run = FakeRunner(drop=["b"])
        out = LLM(self.tmp, runner=run).map_batched(items, instruction="c", item_schema=ITEM_SCHEMA)
        self.assertEqual(out["b"], {"category": "other"})  # recovered on retry
        self.assertEqual(run.calls, 2)

        always_drop = lambda prompt, schema, model: {"results": []}
        llm = LLM(tempfile.mkdtemp(), runner=always_drop)
        out = llm.map_batched(items, instruction="c", item_schema=ITEM_SCHEMA)
        self.assertEqual(out, {"a": None, "b": None})
        self.assertEqual(llm.stats["missing"], 2)

    def test_one_bad_item_does_not_sink_its_batch(self):
        def runner(prompt, schema, model):
            return {"results": [{"id": "a", "category": "tools"}, {"id": "b", "category": "cars"}]}
        items = [{"id": "a", "name": "saw"}, {"id": "b", "name": "bread"}]
        out = LLM(self.tmp, runner=runner).map_batched(items, instruction="c", item_schema=ITEM_SCHEMA)
        self.assertEqual(out, {"a": {"category": "tools"}, "b": None})

    def test_validate(self):
        validate({"category": "food"}, ITEM_SCHEMA)
        with self.assertRaises(LLMError):
            validate({"category": "cars"}, ITEM_SCHEMA)
        with self.assertRaises(LLMError):
            validate({"n": "3"}, {"type": "object", "properties": {"n": {"type": "integer"}}})
        validate({"n": [1, 2]}, {"type": "object", "properties": {"n": {"type": "array", "items": {"type": "integer"}}}})


if __name__ == "__main__":
    unittest.main()
