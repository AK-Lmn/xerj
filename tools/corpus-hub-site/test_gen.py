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


class UsageSectionTest(unittest.TestCase):
    """The usage block carries no number of its own: every figure comes from
    /api/hub-usage at page load, and the empty state is stated, not a zero."""

    def test_corpus_section_has_no_baked_in_numbers(self):
        import re
        import usage
        html = usage.corpus_section('lz4"><x', gen.esc)
        self.assertIn('data-usage="lz4&quot;&gt;&lt;x"', html)
        for m in re.finditer(r'<b data-u="\w+">([^<]*)</b>', html):
            self.assertEqual(m.group(1), "&ndash;")
        self.assertIn("No usage recorded yet", usage.USAGE_JS)
        t = usage.traffic_section("lz4", gen.esc)
        self.assertIn('data-traffic="lz4"', t)
        for m in re.finditer(r'<b data-t="\w+">([^<]*)</b>', t):
            self.assertEqual(m.group(1), "&ndash;")
        self.assertIn("No traffic recorded yet", usage.USAGE_JS)
        self.assertNotIn("innerHTML", usage.USAGE_JS)

    def test_privacy_note_states_what_is_and_is_not_stored(self):
        import usage
        for phrase in ("raw query", "IP address", "3 times", "X-Xerj-Disable-Feedback", "changes every\nday", "host name"):
            self.assertIn(phrase, usage.PRIVACY)
        self.assertIn('id="privacy"', gen.ABOUT)


class PrivateDataTest(unittest.TestCase):
    """The signed-in details (private_data.py) carry no consent data and never land in out/."""

    def _hub(self, d):
        hub = pathlib.Path(d) / "hub"
        (hub / "candidates" / "authors").mkdir(parents=True)
        row = {"corpus": "ann--one", "repo": "ann/one", "repo_url": "https://github.com/ann/one",
               "contributor": {"login": "Ann", "name": "Ann A", "email": "ann@example.com"},
               "consent": {"at": "2026-10-05T10:00Z", "channel": "email reply", "scope": "s", "from": "ann@example.com"},
               "contribution": {"commit": "a" * 40, "commit_url": "https://github.com/ann/one/commit/" + "a" * 40,
                                "title": "feat: x", "committed_at": "2026-10-01T00:00:00Z", "files": 3, "lines": 90,
                                "areas": ["src/a", "src/b"], "langs": ["Go"]},
               "pin": {"sha": "a" * 40}, "licence": {"spdx": "MIT", "suggested_use": "adapt-with-attribution"}}
        (hub / "candidates" / "authors" / "CONTRIBUTORS.jsonl").write_text(json.dumps(row) + "\n")
        (hub / "candidates" / "authors" / "ann--one.json").write_text(json.dumps({"corpus": "ann--one", "status": "draft"}))
        root = pathlib.Path(d)
        (root / "benchmarks" / "hub-backfill").mkdir(parents=True)
        rows = [{"run": "2", "date": "2026-10-19", "slug": "live-one", "pin8": "bbbbbbbb", "result": "published", "tag": "pack-live-one-bbbbbbbb", "bytes": 10, "defs": 5, "url": "u2"},
                {"run": "1", "date": "2026-10-18", "slug": "live-one", "pin8": "cccccccc", "result": "failed", "tag": "", "error": "e2e", "url": "u1"}]
        (root / "benchmarks" / "hub-backfill" / "rows.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
        return root, hub

    def test_details_shape_and_no_consent(self):
        import contributors
        import private_data
        with tempfile.TemporaryDirectory() as d:
            root, hub = self._hub(d)
            reg = [{"slug": "live-one", "lane": "A", "status": "live", "repos": [{"repo": "one", "url": "https://github.com/ann/one", "sha": "b" * 40,
                    "review": {"spdx": "MIT", "use": "adapt-with-attribution", "by": "xerj-org", "at": "2026-10-13", "note": "ok"}}]}]
            people = contributors.load(hub, reg)
            data = private_data.build(root, hub, root / "packs", reg, people, "2026-10-19")
            raw = private_data.module(data)
        self.assertNotIn("example.com", raw)
        self.assertNotIn("email reply", raw)
        w = data["contributors"]["ann"]["work"][0]
        self.assertEqual((w["committed_at"], w["areas"], w["files"]), ("2026-10-01T00:00:00Z", ["src/a", "src/b"], 3))
        self.assertNotIn("commit_url", w)                  # derivable, rebuilt by the API
        self.assertEqual(w["corpora"][0]["manifest"], "draft")
        c = data["corpora"]["live-one"]
        self.assertEqual([b["run"] for b in c["builds"]], ["2", "1"])     # newest first
        self.assertEqual([p["pin8"] for p in c["pins"]], ["cccccccc", "bbbbbbbb"])
        self.assertEqual(c["pins"][1]["published"], "pack-live-one-bbbbbbbb")
        self.assertEqual(c["repos"][0]["review"]["by"], "xerj-org")
        self.assertEqual(data["contributors"]["ann"]["also_pinned_in"], {"live-one": "live"})
        self.assertTrue(raw.startswith("// GENERATED"))

    def test_details_never_written_to_the_site(self):
        self.assertIn('export default null;', private_data_stub())


def private_data_stub():
    import private_data
    return private_data.STUB


class AgentScorePanelTest(unittest.TestCase):
    """The Agent score is its own section, never mixed with hub stars, and
    ships with no number in the HTML (the API fills it, or says there is none)."""

    def test_panel_is_separate_and_honest(self):
        import agent_score
        html = agent_score.section("Tokio", gen.esc)
        self.assertIn('id="agent-score"', html)
        self.assertIn('data-corpus="tokio"', html)
        self.assertIn("not</b> the human hub star count", html)
        self.assertNotIn("★", html)
        self.assertIn("No agent reviews yet", agent_score.PANEL_JS)
        self.assertIn("not being collected yet", agent_score.PANEL_JS)
        self.assertNotIn("innerHTML", agent_score.PANEL_JS + agent_score.CARDS_JS)

    def test_cards_carry_the_slug_for_the_agent_sort(self):
        c = {"slug": "Tokio", "cat": "DB", "status": "live", "lane": "A", "usecase": "x", "repos": [],
             "tags": {}, "kind": "reference corpus"}
        html = gen.card(c, {}, {}, {})
        self.assertIn('data-slug="tokio"', html)


if __name__ == "__main__":
    unittest.main()
