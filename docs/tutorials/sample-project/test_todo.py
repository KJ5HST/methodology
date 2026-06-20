"""Tests for the sample todo CLI — the project's "build equivalent".

Written with stdlib `unittest` so they pass under BOTH:

    python -m pytest        # the runner the tutorials document
    python -m unittest      # zero extra dependencies

Run either from inside docs/tutorials/sample-project/.
"""
import json
import tempfile
import unittest
from pathlib import Path

import todo


class CoreTests(unittest.TestCase):
    def test_add_assigns_incrementing_ids(self):
        todos: list[dict] = []
        first = todo.add_todo(todos, "write the report")
        second = todo.add_todo(todos, "submit the report")
        self.assertEqual(first["id"], 1)
        self.assertEqual(second["id"], 2)
        self.assertFalse(first["done"])
        self.assertEqual(len(todos), 2)

    def test_add_reuses_max_id_plus_one_after_gaps(self):
        # Ids continue from the current max, not the count — survives future deletes.
        todos = [{"id": 5, "text": "old", "done": True}]
        new = todo.add_todo(todos, "new")
        self.assertEqual(new["id"], 6)

    def test_render_empty_is_friendly(self):
        self.assertIn("no todos yet", todo.render([]))

    def test_render_marks_done_and_pending(self):
        out = todo.render([
            {"id": 1, "text": "done thing", "done": True},
            {"id": 2, "text": "pending thing", "done": False},
        ])
        self.assertIn("[x] done thing", out)
        self.assertIn("[ ] pending thing", out)

    def test_save_then_load_round_trips(self):
        with tempfile.TemporaryDirectory() as d:
            store = Path(d) / "todos.json"
            todos = [{"id": 1, "text": "persisted", "done": False}]
            todo.save_todos(store, todos)
            self.assertEqual(todo.load_todos(store), todos)
            # File is valid, human-readable JSON.
            self.assertEqual(json.loads(store.read_text())[0]["text"], "persisted")

    def test_load_missing_store_returns_empty(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(todo.load_todos(Path(d) / "nope.json"), [])


class CliTests(unittest.TestCase):
    def test_add_then_list_via_main(self):
        with tempfile.TemporaryDirectory() as d:
            store = str(Path(d) / "todos.json")
            self.assertEqual(todo.main(["--file", store, "add", "buy milk"]), 0)
            data = json.loads(Path(store).read_text())
            self.assertEqual(data[0]["text"], "buy milk")
            self.assertEqual(todo.main(["--file", store, "list"]), 0)


if __name__ == "__main__":
    unittest.main()
