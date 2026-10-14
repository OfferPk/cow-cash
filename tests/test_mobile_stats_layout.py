"""Verify that the dashboard stat cards form a readable grid on narrow phones.

Run with `python -B -m unittest discover -s tests -v` after installing
requirements-test.txt and Chromium (`python -m playwright install chromium`).
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import shutil
import unittest

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]


class MobileStatsLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler = partial(SimpleHTTPRequestHandler, directory=str(ROOT))
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.server_thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()

        cls.playwright = sync_playwright().start()
        executable = shutil.which("chromium")
        launch_options = {"headless": True}
        if executable:
            launch_options["executable_path"] = executable
        cls.browser = cls.playwright.chromium.launch(**launch_options)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.server_thread.join(timeout=2)

    def test_stats_use_two_columns_on_narrow_mobile_viewport(self):
        context = self.browser.new_context(viewport={"width": 390, "height": 844})
        try:
            page = context.new_page()
            page.goto(f"http://127.0.0.1:{self.server.server_port}/", wait_until="load")

            stats = page.locator(".stats")
            self.assertEqual(stats.evaluate("el => getComputedStyle(el).display"), "grid")
            self.assertEqual(
                stats.evaluate("el => getComputedStyle(el).gridTemplateColumns.split(' ').length"),
                2,
            )
            self.assertEqual(stats.locator(":scope > .stat").count(), 4)
        finally:
            context.close()


if __name__ == "__main__":
    unittest.main()
