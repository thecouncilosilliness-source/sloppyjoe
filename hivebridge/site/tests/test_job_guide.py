"""Privacy and completeness checks for the job scam first-aid page."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
import unittest

PAGE = Path(__file__).resolve().parents[1] / "jobs.html"
HOME = PAGE.with_name("index.html")

class Structure(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.links = []
        self.lang = None
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.tags.append(tag)
        if tag == "html": self.lang = a.get("lang")
        if tag == "a": self.links.append(a.get("href", ""))

class JobGuideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = PAGE.read_text(encoding="utf-8")
        cls.markup = Structure()
        cls.markup.feed(cls.page)

    def test_page_structure_and_navigation(self):
        self.assertEqual(self.markup.lang, "en")
        self.assertIn("main", self.markup.tags)
        self.assertIn("h1", self.markup.tags)
        self.assertIn("summary", self.markup.tags)
        self.assertIn("jobs.html", HOME.read_text(encoding="utf-8"))
        self.assertIn("help.html", self.markup.links)

    def test_no_visitor_data_capture(self):
        for tag in ("form", "input", "textarea", "iframe", "script"):
            self.assertNotIn(tag, self.markup.tags)
        for mechanism in ("fetch(", "localStorage", "XMLHttpRequest", "document.cookie"):
            self.assertNotIn(mechanism, self.page)

    def test_official_external_destinations(self):
        links = [l for l in self.markup.links if l.startswith("http")]
        self.assertGreaterEqual(len(links), 6)
        approved = {"consumer.ftc.gov", "www.ic3.gov", "www.identitytheft.gov", "reportfraud.ftc.gov"}
        self.assertTrue(all(urlparse(l).scheme == "https" and urlparse(l).hostname in approved for l in links))
        self.assertIn("https://consumer.ftc.gov/articles/job-scams", links)

    def test_material_recovery_information(self):
        for key in ("crypto", "equipment", "check", "bank", "IdentityTheft.gov", "No automatic verdict", "no refund is guaranteed"):
            self.assertIn(key.lower(), self.page.lower())
        self.assertIn("No personal information collected", self.page)
        self.assertIn("live multi-provider agents are not connected", self.page)

if __name__ == "__main__":
    unittest.main()
