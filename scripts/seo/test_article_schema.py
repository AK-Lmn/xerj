#!/usr/bin/env python3
"""Regression tests for the required `updated:` frontmatter field (#974).

Until #974 an article could omit `updated:`, and build_articles fell back to
the content file's git committer date (`article.updated or
context.dates.last_modified(...)`).  A squash merge rewrites that date to the
merge day, so any PR whose pages were regenerated on day N went red on
`build_articles --check` the moment it merged on day N+1 (#942 was the live
instance; #972 band-aided it).  These tests pin the fix: the field is
materialized in every content source and `article_data.load` rejects a source
without it, so article dates are author-controlled data and cannot drift with
git history.

Run: python3 scripts/seo/test_article_schema.py
"""

import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import article_data
from article_data import FrontmatterError, load

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent

# Minimal frontmatter that passes _validate as written; each test mutates
# only the `updated:` line it exercises.
FRONTMATTER = """---
title: "Schema test article"
h1: "H1 of the schema test article?"
description: "A minimal article that satisfies the frontmatter schema."
slug: "schema-test-article"
cluster: "Test cluster"
question: "What does the schema test article cover?"
intent: "how-to"
published: "2026-08-21"
updated: "2026-09-01"
author: "XERJ documentation team"
reviewer: "XERJ engineering team"
schema_type: "TechArticle"
links_out:
  - /answers/what-is-xerj/
faq:
  - q: "Question one?"
    a: "Answer one."
  - q: "Question two?"
    a: "Answer two."
  - q: "Question three?"
    a: "Answer three."
  - q: "Question four?"
    a: "Answer four."
---
Body of the schema test article.
"""


def _write(tmp: pathlib.Path, text: str) -> pathlib.Path:
    # The slug must match the filename and the parent directory selects the
    # category, so the fixture layout mirrors content/answers/.
    directory = tmp / "answers"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "schema-test-article.md"
    path.write_text(text, encoding="utf-8")
    return path


class UpdatedFieldTests(unittest.TestCase):
    def test_missing_updated_is_rejected(self):
        # The #974 regression: before the field became required this loaded
        # cleanly and the generator silently dated the page from git.
        text = FRONTMATTER.replace('updated: "2026-09-01"\n', "")
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(pathlib.Path(tmp), text)
            with self.assertRaises(FrontmatterError) as ctx:
                load(path)
            self.assertIn("missing required frontmatter field(s): updated",
                          str(ctx.exception))

    def test_valid_updated_is_parsed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(pathlib.Path(tmp), FRONTMATTER)
            article = load(path)
        self.assertEqual(article.updated, "2026-09-01")

    def test_malformed_updated_is_rejected(self):
        text = FRONTMATTER.replace('updated: "2026-09-01"',
                                   'updated: "Sep 1st"')
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(pathlib.Path(tmp), text)
            with self.assertRaises(FrontmatterError) as ctx:
                load(path)
            self.assertIn("updated must be an ISO date YYYY-MM-DD",
                          str(ctx.exception))

    def test_impossible_calendar_date_is_rejected(self):
        # Matches the YYYY-MM-DD shape but is not a real date, so only the
        # date.fromisoformat fallback catches it.
        text = FRONTMATTER.replace('updated: "2026-09-01"',
                                   'updated: "2026-09-32"')
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(pathlib.Path(tmp), text)
            with self.assertRaises(FrontmatterError) as ctx:
                load(path)
            self.assertIn("updated is not a valid ISO date", str(ctx.exception))


GEO_ANSWER = ("What does the schema test article cover? It covers the GEO fields: a forty "
              "to sixty word answer that restates the question, one dated and sourced number, "
              "an intent group, the literal queries the page targets, and optional HowTo steps "
              "taken from the commands. This sentence pads the answer past forty words.")


def _geo(text: str = FRONTMATTER, **extra: str) -> str:
    lines = [f'answer: "{GEO_ANSWER}"',
             'key_fact: "The suite passes 1366 of 1369 cases."',
             'key_fact_source: "https://github.com/xerj-org/xerj"',
             'key_fact_date: "2026-10-19"',
             'intent_group: "code search for agents"',
             "queries:", '  - "local code search MCP"']
    for key, value in extra.items():
        lines = [line for line in lines if not line.startswith(key + ":")]
        if value is not None:
            lines.append(f"{key}: {value}")
    return text.replace('schema_type: "TechArticle"\n',
                        'schema_type: "TechArticle"\n' + "\n".join(lines) + "\n")


class GeoFieldTests(unittest.TestCase):
    def _load(self, text: str):
        with tempfile.TemporaryDirectory() as tmp:
            return load(_write(pathlib.Path(tmp), text))

    def _rejects(self, text: str, needle: str) -> None:
        with self.assertRaises(FrontmatterError) as ctx:
            self._load(text)
        self.assertIn(needle, str(ctx.exception))

    def test_valid_geo_fields_load_and_reach_head_meta(self):
        article = self._load(_geo())
        self.assertEqual(article.intent_group, "code search for agents")
        self.assertEqual(list(article.queries), ["local code search MCP"])
        meta = article.head_meta()
        self.assertEqual(len(meta["faq"]), 4)
        self.assertNotIn("howto_steps", meta)

    def test_short_answer_is_rejected(self):
        self._rejects(_geo(answer='"Too short to restate anything."'), "answer")

    def test_key_fact_needs_its_source_and_date(self):
        self._rejects(_geo(key_fact_date=None), "go together")

    def test_key_fact_needs_a_number(self):
        self._rejects(_geo(key_fact='"No number here."'), "number")

    def test_missing_repo_source_is_rejected(self):
        self._rejects(_geo(key_fact_source='"docs/does-not-exist.md"'), "key_fact_source")

    def test_capture_source_is_accepted(self):
        article = self._load(_geo(key_fact_source='"capture"'))
        self.assertEqual(article.key_fact_source, "capture")

    def test_howto_needs_two_commands(self):
        self._rejects(_geo(howto="true"), "at least 2 commands")


class HeadBlockTests(unittest.TestCase):
    def test_faq_and_howto_blocks(self):
        import seo_head
        meta = {"faq": [{"q": "Is it **local**?", "a": "Yes, see [docs](/docs)."}],
                "howto_name": "Index a folder",
                "howto_steps": [{"cmd": "xerj autoindex ./d", "note": "Index."},
                                {"cmd": "xerj mcp", "note": "Serve."}]}
        blocks = {b["@type"]: b for b in seo_head.geo_blocks("https://xerj.org/answers/x", meta)}
        faq = blocks["FAQPage"]["mainEntity"][0]
        self.assertEqual(faq["name"], "Is it local?")
        self.assertEqual(faq["acceptedAnswer"]["text"], "Yes, see docs.")
        steps = blocks["HowTo"]["step"]
        self.assertEqual([s["text"] for s in steps], ["xerj autoindex ./d", "xerj mcp"])
        self.assertEqual(steps[1]["url"], "https://xerj.org/answers/x#step-2")


class VisibleStructuredDataTests(unittest.TestCase):
    """seo_lint rule 46: FAQPage/HowTo only for what the page shows."""

    def _issues(self, body: str, node: dict) -> list[str]:
        import audit as audit_mod
        import seo_lint
        page = audit_mod.Page(path="x.html", abs_path=pathlib.Path("x.html"))
        parser = audit_mod.PageParser(page)
        parser.feed(f"<html><body>{body}</body></html>")
        parser.close()
        lint = object.__new__(seo_lint.Lint)
        lint.issues = []
        lint._check_visible_structured("x.html", page, node, node["@type"], 1)
        return [issue.rule for issue in lint.issues]

    FAQ = {"@type": "FAQPage", "mainEntity": [{
        "@type": "Question", "name": "Does it run offline?",
        "acceptedAnswer": {"@type": "Answer", "text": "Yes, with the default embedder."}}]}

    def test_visible_faq_passes(self):
        body = "<h3>Does it run offline?</h3><p>Yes, with the <code>default</code> embedder.</p>"
        self.assertEqual(self._issues(body, self.FAQ), [])

    def test_invisible_faq_question_is_a_gate(self):
        self.assertEqual(self._issues("<h2>Other</h2><p>Text.</p>", self.FAQ),
                         ["jsonld.faq_invisible"])

    def test_invisible_faq_answer_is_a_gate(self):
        body = "<h3>Does it run offline?</h3><p>Something else entirely.</p>"
        self.assertEqual(self._issues(body, self.FAQ), ["jsonld.faq_invisible"])

    def test_invisible_howto_step_is_a_gate(self):
        node = {"@type": "HowTo", "step": [{"position": 1, "text": "xerj mcp"}]}
        self.assertEqual(self._issues("<pre>xerj autoindex .</pre>", node),
                         ["jsonld.howto_invisible"])


class CommittedContentTests(unittest.TestCase):
    def test_every_committed_article_carries_updated(self):
        """No source may regress to the git-date fallback (#974's root cause).

        load() already rejects a missing field, so this doubles as a check
        that the whole committed corpus still parses under the stricter
        schema.
        """
        sources = sorted(
            (REPO_ROOT / "content").glob("answers/*.md")
        ) + sorted((REPO_ROOT / "content").glob("compare/*.md"))
        self.assertGreater(len(sources), 0, "no content sources found")
        bad: list[str] = []
        for path in sources:
            try:
                article = article_data.load(path)
            except FrontmatterError as exc:
                bad.append(str(exc))
                continue
            if not article.updated:
                bad.append(f"{path}: updated is missing")
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()
