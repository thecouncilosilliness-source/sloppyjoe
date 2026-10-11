"""Offline sanity checks for the static Operation Help Humanity first-aid guide."""
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

PAGE = Path(__file__).resolve().parents[1] / "help.html"

class Markup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.links = []
        self.lang = None
        self.scripts = 0
    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        self.tags.append((tag, values))
        if tag == "html":
            self.lang = values.get("lang")
        if tag == "a":
            self.links.append(values.get("href", ""))
        if tag == "script":
            self.scripts += 1

class HelpPageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = PAGE.read_text(encoding="utf-8")
        cls.parser = Markup()
        cls.parser.feed(cls.content)
    def test_accessible_structure(self):
        self.assertEqual(self.parser.lang, "en")
        self.assertTrue(any(tag=="main" for tag,_ in self.parser.tags))
        self.assertTrue(any(tag=="h1" for tag,_ in self.parser.tags))
        self.assertTrue(any(tag=="details" for tag,_ in self.parser.tags))
        self.assertTrue(any(tag=="summary" for tag,_ in self.parser.tags))
    def test_no_data_collection_or_external_js(self):
        names = [tag for tag,_ in self.parser.tags]
        self.assertNotIn("form", names)
        self.assertNotIn("input", names)
        self.assertNotIn("textarea", names)
        self.assertNotIn("iframe", names)
        self.assertEqual(self.parser.scripts, 0)
        self.assertNotIn("fetch(", self.content)
        self.assertNotIn("localStorage", self.content)
    def test_official_external_sources(self):
        urls = [x for x in self.parser.links if x.startswith("http")]
        self.assertGreaterEqual(len(urls), 5)
        allowed = {"consumer.ftc.gov", "reportfraud.ftc.gov", "www.identitytheft.gov", "www.cisa.gov"}
        self.assertTrue(all(urlparse(x).scheme == "https" and urlparse(x).hostname in allowed for x in urls))
        self.assertIn("https://reportfraud.ftc.gov/", urls)
        self.assertIn("https://www.identitytheft.gov/", urls)
    def test_key_recovery_scenarios(self):
        for marker in ("I clicked a link", "I sent money", "shared an account password", "identity theft", "immediately"):
            self.assertIn(marker, self.content)
        self.assertIn("Recovery cannot be guaranteed", self.content)
    def test_no_unsupported_automation_claim(self):
        self.assertIn("not a live multi-agent service", self.content)
        self.assertIn("No AI diagnosis", self.content)

if __name__ == "__main__":
    unittest.main(verbosity=2)
