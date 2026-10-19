#!/usr/bin/env python3
"""Regression tests for gen.py (the Corpus Hub site generator).

Stdlib only, no network, deterministic — same constraints as gen.py. Run:

    python3 tools/corpus-hub-site/test_gen.py

Covers issue #1279: a graded backlog file whose "graded" value is a string
(a timestamp note, not a slug->suite map) must not crash the whole site
build. One malformed file froze every corpus discovery page in the deploy.
"""
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import gen  # noqa: E402


class ParseGradedSuitesTest(unittest.TestCase):
    def _run_against(self, files):
        """Run parse_graded_suites against a throwaway backlog dir."""
        with tempfile.TemporaryDirectory() as d:
            hub = pathlib.Path(d)
            (hub / "backlog").mkdir()
            for name, payload in files.items():
                (hub / "backlog" / name).write_text(json.dumps(payload))
            orig = gen.HUB
            gen.HUB = hub
            try:
                return gen.parse_graded_suites()
            finally:
                gen.HUB = orig

    def test_string_graded_value_is_skipped_not_fatal(self):
        # issue #1279: "graded" is a timestamp string, not a dict. Before the
        # fix this raised AttributeError: 'str' object has no attribute 'items'
        # and aborted the entire deploy.
        out = self._run_against({
            "g7-otel-proto-graded.json": {
                "suite": "g7-otel-proto",
                "graded": "2026-10-08 (re-graded same day; run 2 PASS 5/5)",
                "verdict": "PASS",
            },
        })
        self.assertEqual(out, {})

    def test_well_formed_dict_suite_still_parses(self):
        out = self._run_against({
            "g7-good-graded.json": {
                "graded": {
                    "mycorpus": {
                        "verdict": "PASS",
                        "queries": [
                            {"q": "a", "verdict": "relevant"},
                            {"q": "b", "verdict": "relevant"},
                        ],
                    }
                }
            },
        })
        self.assertIn("mycorpus", out)
        self.assertEqual(out["mycorpus"]["median"], 5.0)

    def test_malformed_file_does_not_hide_good_siblings(self):
        # The real-world failure mode: the whole build must survive one bad
        # file and still emit every other corpus' suite.
        out = self._run_against({
            "g7-bad-graded.json": {"graded": "just a note"},
            "g7-ok-graded.json": {
                "corpora": {
                    "ok": {"verdict": "PASS",
                           "queries": [{"q": "x", "verdict": "relevant"}]}
                }
            },
        })
        self.assertIn("ok", out)

    def test_list_graded_value_is_also_tolerated(self):
        out = self._run_against({
            "g7-list-graded.json": {"graded": ["not", "a", "map"]},
        })
        self.assertEqual(out, {})


class ContributorVolumeTest(unittest.TestCase):
    """Contributor pages aggregate on login across every corpus (PR #1782 follow-up)."""

    def _hub(self, d):
        hub = pathlib.Path(d)
        (hub / "candidates" / "authors").mkdir(parents=True)
        rows = [
            {"corpus": "ann--one", "repo": "Ann/one", "repo_url": "https://github.com/Ann/one", "repo_stars": 10,
             "contributor": {"login": "Ann", "name": "Ann A"}, "consent": {"at": "2026-10-09T10:00Z"},
             "contribution": {"commit": "a" * 40, "commit_url": "u", "files": 3, "lines": 100},
             "licence": {"spdx": "MIT", "reviewed": False}},
            {"corpus": "bob--two", "repo": "bob/two", "repo_url": "https://github.com/bob/two", "repo_stars": 5,
             "contributor": {"login": "ann", "name": ""}, "consent": {"at": "2026-10-08T10:00Z"},
             "contribution": {"commit": "b" * 40, "commit_url": "u", "files": 2, "lines": 50},
             "licence": {"spdx": "MIT", "reviewed": False}},
        ]
        (hub / "candidates" / "authors" / "CONTRIBUTORS.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        (hub / "candidates" / "CONTRIBUTORS-2026-10.md").write_text(
            "## themed (2)\n\n| repo | author | commit | licence | permission |\n|---|---|---|---|---|\n"
            "| [Ann/one](https://github.com/Ann/one) | @ANN | [aaaaaaaaaa](u) same commit again | MIT | 2026-10-05 |\n"
            "| [cat/three](https://github.com/cat/three) | @cat | [cccccccccc](u) only here | GPL-3.0 | 2026-10-06 |\n")
        return hub

    def test_one_person_per_login_across_corpora(self):
        import contributors
        with tempfile.TemporaryDirectory() as d:
            reg = [{"slug": "live-one", "status": "live", "repos": [{"url": "https://github.com/ann/x"}]}]
            people = contributors.load(self._hub(d), reg)
        self.assertEqual(sorted(people), ["Ann", "cat"])
        v = contributors.volume(people["Ann"], {"live-one"})
        # 2 distinct commits (the themed row repeats the first), files/lines once each
        self.assertEqual((v["commits"], v["files"], v["lines"]), (2, 5, 150))
        # ann--one, bob--two, themed, and the live corpus pinning a repo she owns
        self.assertEqual(v["corpora"], 4)
        self.assertEqual(v["live"], ["live-one"])
        self.assertEqual(v["gh_stars"], 15)
        self.assertEqual(v["since"], "2026-10-05")
        self.assertEqual(contributors.volume(people["cat"])["commits"], 1)
        idx = contributors.by_corpus(people)
        self.assertEqual(idx["themed"], ["Ann", "cat"])
        self.assertEqual(idx["live-one"], ["Ann"])
        html = contributors.corpus_section(idx["themed"], gen.esc, people)
        self.assertIn('href="../contributors/Ann.html"', html)
        self.assertEqual(contributors.corpus_section([], gen.esc, people), "")

    def test_no_licence_is_marked_reviewed(self):
        import contributors
        with tempfile.TemporaryDirectory() as d:
            people = contributors.load(self._hub(d))
        self.assertFalse(any(w["reviewed"] for p in people.values() for w in p["work"].values()))


class SignInNavTest(unittest.TestCase):
    def test_sign_in_box_ships_hidden_and_asks_api_me(self):
        html = gen.page("t", "d", "<main></main>")
        # hidden in the static HTML: an anonymous visitor on a hub without the
        # OAuth secrets sees exactly the page they saw before
        self.assertIn('<details class="authbox" id="hubauth" hidden></details>', html)
        self.assertIn("fetch('/api/me'", html)
        self.assertIn("if(!box||!me||!me.ok||!me.enabled)return;", html)
        # user-controlled text is never written as HTML
        self.assertNotIn("innerHTML", gen.AUTH_JS)

    def test_me_page_is_an_empty_shell(self):
        # personal data only ever arrives from the authenticated API
        self.assertIn("/api/v1/me/stars", gen.ME_JS)
        self.assertNotIn("innerHTML", gen.ME_JS)


if __name__ == "__main__":
    unittest.main()
