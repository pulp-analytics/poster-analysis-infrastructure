#!/usr/bin/env python3
"""Tests for scripts/merge_shards.py.

merge_shards.py is the one step where a silent partial merge would corrupt
the corpus (a crashed shard treated as "zero rows" rather than a hard
error), so its guards matter more than its happy path. These use the
stdlib `unittest` only -- no pytest/numpy required -- so they run in the
same bare python:3.12-slim the validator image is built on. The npz cases
skip themselves if numpy isn't importable (only the metrics image has it).

  python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

# Load merge_shards.py by path (it lives in scripts/, not an importable
# package) so these tests don't depend on cwd or sys.path hacks.
_MOD_PATH = Path(__file__).resolve().parent.parent / "scripts" / "merge_shards.py"
_spec = importlib.util.spec_from_file_location("merge_shards", _MOD_PATH)
merge_shards = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(merge_shards)


class MergeCsvTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, name: str, text: str) -> Path:
        p = self.dir / name
        p.write_text(text, encoding="utf-8")
        return p

    def test_concatenates_rows_and_keeps_single_header(self):
        a = self._write("shard-0-x.csv", "id,title\n1,a\n2,b\n")
        b = self._write("shard-1-x.csv", "id,title\n3,c\n")
        out = self.dir / "merged.csv"
        n = merge_shards.merge_csv([a, b], out)
        self.assertEqual(n, 3)
        self.assertEqual(
            out.read_text(encoding="utf-8").splitlines(),
            ["id,title", "1,a", "2,b", "3,c"],
        )

    def test_mismatched_headers_is_a_hard_error(self):
        a = self._write("shard-0-x.csv", "id,title\n1,a\n")
        b = self._write("shard-1-x.csv", "id,name\n2,b\n")
        with self.assertRaises(ValueError):
            merge_shards.merge_csv([a, b], self.dir / "merged.csv")


class MergeJsonTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, name: str, obj) -> Path:
        p = self.dir / name
        p.write_text(json.dumps(obj), encoding="utf-8")
        return p

    def test_disjoint_dicts_union(self):
        a = self._write("shard-0.json", {"1": {"t": "a"}, "2": {"t": "b"}})
        b = self._write("shard-1.json", {"3": {"t": "c"}})
        out = self.dir / "merged.json"
        n = merge_shards.merge_json([a, b], out)
        self.assertEqual(n, 3)
        self.assertEqual(
            json.loads(out.read_text(encoding="utf-8")),
            {"1": {"t": "a"}, "2": {"t": "b"}, "3": {"t": "c"}},
        )

    def test_overlapping_ids_is_a_hard_error(self):
        a = self._write("shard-0.json", {"1": {"t": "a"}})
        b = self._write("shard-1.json", {"1": {"t": "dup"}})
        with self.assertRaises(ValueError):
            merge_shards.merge_json([a, b], self.dir / "merged.json")


class CliGuardTests(unittest.TestCase):
    """The partial-result guards in main() -- the whole point of the script."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, argv):
        import sys
        old = sys.argv
        sys.argv = ["merge_shards.py", *argv]
        try:
            return merge_shards.main()
        finally:
            sys.argv = old

    def test_glob_matching_fewer_than_expected_fails(self):
        (self.dir / "shard-0-x.csv").write_text("id\n1\n", encoding="utf-8")
        with self.assertRaises(SystemExit):
            self._run([
                "--format", "csv",
                "--shard-glob", str(self.dir / "shard-*-x.csv"),
                "--expected-count", "2",
                "--out", str(self.dir / "m.csv"),
            ])

    def test_explicit_missing_shard_fails(self):
        present = self.dir / "shard-0-x.csv"
        present.write_text("id\n1\n", encoding="utf-8")
        with self.assertRaises(SystemExit):
            self._run([
                "--format", "csv",
                "--shards", str(present), str(self.dir / "does-not-exist.csv"),
                "--out", str(self.dir / "m.csv"),
            ])

    def test_shard_glob_requires_expected_count(self):
        with self.assertRaises(SystemExit):
            self._run([
                "--format", "csv",
                "--shard-glob", str(self.dir / "shard-*-x.csv"),
                "--out", str(self.dir / "m.csv"),
            ])

    def test_cannot_pass_both_shards_and_glob(self):
        p = self.dir / "shard-0-x.csv"
        p.write_text("id\n1\n", encoding="utf-8")
        with self.assertRaises(SystemExit):
            self._run([
                "--format", "csv",
                "--shards", str(p),
                "--shard-glob", str(self.dir / "shard-*-x.csv"),
                "--out", str(self.dir / "m.csv"),
            ])


class MergeNpzTests(unittest.TestCase):
    def setUp(self):
        try:
            import numpy  # noqa: F401
        except ImportError:
            self.skipTest("numpy not installed (only the metrics image has it)")
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        if hasattr(self, "tmp"):
            self.tmp.cleanup()

    def test_disjoint_embedding_caches_concat(self):
        import numpy as np
        a = self.dir / "shard-0.npz"
        b = self.dir / "shard-1.npz"
        np.savez(a, ids=np.array([1, 2]), vecs=np.array([[0.1, 0.2], [0.3, 0.4]]))
        np.savez(b, ids=np.array([3]), vecs=np.array([[0.5, 0.6]]))
        out = self.dir / "merged.npz"
        n = merge_shards.merge_npz([a, b], out)
        self.assertEqual(n, 3)
        z = np.load(out)
        self.assertEqual(sorted(int(x) for x in z["ids"]), [1, 2, 3])
        self.assertEqual(z["vecs"].shape, (3, 2))

    def test_overlapping_ids_is_a_hard_error(self):
        import numpy as np
        a = self.dir / "shard-0.npz"
        b = self.dir / "shard-1.npz"
        np.savez(a, ids=np.array([1]), vecs=np.array([[0.1]]))
        np.savez(b, ids=np.array([1]), vecs=np.array([[0.9]]))
        with self.assertRaises(ValueError):
            merge_shards.merge_npz([a, b], self.dir / "merged.npz")


if __name__ == "__main__":
    unittest.main()
