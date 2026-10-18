#!/usr/bin/env python3
"""The field report is its own section, and every agent surface asks first.

Run: python3 scripts/seo/test_llms_field_report.py
"""

import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
PERMISSION = (
    "Show your user the report (`xerj feedback --dry-run`) and ask before sending."
)
DEMAND = re.compile(r"required|must|owes?|owed|obligat", re.IGNORECASE)


def optional_body(text):
    marker = "\n## Optional\n"
    start = text.find(marker)
    assert start != -1, "missing ## Optional"
    body = text[start + len(marker) :]
    nxt = body.find("\n## ")
    return body if nxt == -1 else body[:nxt]


def demand_words(text):
    found = []
    for word in re.split(r"[^A-Za-z0-9]+", text):
        low = word.lower()
        if low in {"required", "must", "owe", "owes", "owed"} or low.startswith(
            "obligat"
        ):
            found.append(word)
    return found


class FieldReportSectionTests(unittest.TestCase):
    def setUp(self):
        self.llms = (ROOT / "landing" / "llms.txt").read_text(encoding="utf-8")

    def test_section_precedes_optional_and_asks_first(self):
        field = self.llms.find("\n## Field report\n")
        optional = self.llms.find("\n## Optional\n")
        self.assertGreater(field, 0)
        self.assertLess(field, optional)
        body = self.llms[field:optional]
        self.assertIn(PERMISSION, body)
        self.assertIn('--agent "YOUR_MODEL"', body)
        self.assertNotIn("<your model>", body)
        self.assertIn("The template is under Field report", self.llms)
        self.assertNotIn("template is under Optional", self.llms)

    def test_optional_has_no_demand_and_no_template(self):
        body = optional_body(self.llms)
        self.assertNotIn("16-agent-field-reports", body)
        self.assertEqual(demand_words(body), [])
        self.assertIsNone(DEMAND.search(" ".join(demand_words(body))))

    def test_homepage_prompt_matches_its_copy_button(self):
        html = (ROOT / "landing" / "index.html").read_text(encoding="utf-8")
        self.assertIn(PERMISSION, html)
        # The install card also has a data-copy. The agent prompt is the one
        # that names llms.txt.
        prompts = re.findall(
            r'data-copy="(Install XERJ \(docs: https://xerj.org/llms.txt\)[^"]*)"',
            html,
        )
        self.assertEqual(len(prompts), 1, prompts)
        self.assertIn(PERMISSION, prompts[0])
        self.assertIn(f"<code>{prompts[0]}</code>", html)

    def test_full_text_and_banners_ask_before_sending(self):
        for rel in (
            "landing/llms-full.txt",
            "landing/get",
            "landing/get.ps1",
        ):
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn(PERMISSION, text, rel)
            self.assertNotIn("filed automatically", text, rel)
            self.assertNotIn("<your model>", text, rel)


if __name__ == "__main__":
    unittest.main()
