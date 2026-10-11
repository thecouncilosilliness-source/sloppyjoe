"""Offline link-integrity checks for human-facing static HTML pages.

Runs in the existing GitHub Actions help-page suite. No external requests, API keys,
visitor information, or network services required.
"""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse
import unittest

SITE = Path(__file__).resolve().parents[1]

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        a = dict(attrs)
        self.links.append(a.get("href", ""))

class PublicSiteLinkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = sorted(SITE.glob("*.html"))
        cls.parsed = {}
        for page in cls.pages:
            parser = Links()
            parser.feed(page.read_text(encoding="utf-8"))
            cls.parsed[page] = parser.links

    def test_site_has_home_and_both_first_aid_guides(self):
        self.assertTrue((SITE / "index.html").is_file())
        self.assertTrue((SITE / "help.html").is_file())
        self.assertTrue((SITE / "jobs.html").is_file())

    def test_relative_page_links_exist_inside_site(self):
        root = SITE.resolve()
        for page, links in self.parsed.items():
            with self.subTest(page=page.name):
                for href in links:
                    u = urlparse(href)
                    if u.scheme or u.netloc or not u.path:
                        continue
                    self.assertFalse(u.path.startswith("/"), f"{page.name}: absolute path {href}")
                    target = (page.parent / unquote(u.path)).resolve()
                    self.assertTrue(target.is_relative_to(root), f"{page.name}: path escapes site: {href}")
                    self.assertTrue(target.is_file(), f"{page.name}: missing local link {href}")

    def test_no_insecure_or_javascript_links(self):
        for page, links in self.parsed.items():
            with self.subTest(page=page.name):
                for href in links:
                    u = urlparse(href)
                    self.assertNotEqual(u.scheme.lower(), "javascript", f"{page.name}: JavaScript URL")
                    self.assertNotEqual(u.scheme.lower(), "http", f"{page.name}: insecure URL")
                    self.assertTrue(
                        u.scheme.lower() in ("", "https", "mailto", "tel"),
                        f"{page.name}: disallowed scheme {u.scheme}"
                    )

    def test_each_aid_guide_linked_from_home(self):
        hrefs = set(self.parsed[SITE / "index.html"])
        self.assertIn("help.html", hrefs)
        self.assertIn("jobs.html", hrefs)

if __name__ == "__main__":
    unittest.main(verbosity=2)
