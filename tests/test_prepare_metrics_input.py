#!/usr/bin/env python3
"""Tests for scripts/prepare_metrics_input.py.

The adapter's only real logic is: derive `year` from `release_date`'s
first 4 chars, and DROP (not placeholder) rows missing release_date or
poster_path -- a fabricated year would silently break metrics-pipeline's
title+year lookups, so dropping is deliberate and worth pinning down.

Stdlib unittest only.

  python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

_MOD_PATH = Path(__file__).resolve().parent.parent / "scripts" / "prepare_metrics_input.py"
_spec = importlib.util.spec_from_file_location("prepare_metrics_input", _MOD_PATH)
prepare_metrics_input = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(prepare_metrics_input)


class PrepareMetricsInputTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, rows, fieldnames):
        src = self.dir / "validated_corpus.csv"
        with src.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
        out = self.dir / "metrics_input.csv"

        import sys
        old = sys.argv
        sys.argv = ["prepare_metrics_input.py", "--in", str(src), "--out", str(out)]
        try:
            prepare_metrics_input.main()
        finally:
            sys.argv = old

        with out.open(newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def test_year_derived_and_schema_narrowed(self):
        out = self._run(
            [{"id": "7", "title": "Saw", "original_title": "Saw",
              "release_date": "2004-10-29", "poster_path": "/x.jpg", "extra": "ignored"}],
            ["id", "title", "original_title", "release_date", "poster_path", "extra"],
        )
        self.assertEqual(len(out), 1)
        self.assertEqual(
            out[0],
            {"id": "7", "title": "Saw", "year": "2004", "poster_path": "/x.jpg"},
        )

    def test_rows_missing_release_date_or_poster_are_dropped(self):
        out = self._run(
            [
                {"id": "1", "title": "ok", "release_date": "1999-01-01", "poster_path": "/a.jpg"},
                {"id": "2", "title": "no date", "release_date": "", "poster_path": "/b.jpg"},
                {"id": "3", "title": "no poster", "release_date": "2010-05-05", "poster_path": ""},
            ],
            ["id", "title", "release_date", "poster_path"],
        )
        self.assertEqual([r["id"] for r in out], ["1"])


if __name__ == "__main__":
    unittest.main()
