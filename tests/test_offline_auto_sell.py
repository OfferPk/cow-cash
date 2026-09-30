"""Verify offline payout behavior using disposable synthetic saves.

Run with `python -B -m unittest discover -s tests -v` after installing
requirements-test.txt and Chromium (`python -m playwright install chromium`).
"""
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import shutil
import unittest

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]


class OfflineAutoSellTests(unittest.TestCase):
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

    def _run_offline_scenario(self, auto_sell):
        now_ms = 1_700_000_000_000
        initial_milk = 12
        synthetic_save = {
            "coins": 7,
            "milk": initial_milk,
            "totalMilk": 34,
            "autoSell": auto_sell,
            "owned": {"cow": 2, "machine": 0, "feed": 0, "barn": 0},
            "lastSaved": now_ms - 60_000,
        }
        context = self.browser.new_context(viewport={"width": 390, "height": 844})
        try:
            page = context.new_page()
            page.add_init_script(
                """(() => {
                  const now = __NOW__;
                  Date.now = () => now;
                  window.requestAnimationFrame = () => 0;
                  localStorage.clear();
                  localStorage.setItem("cowCashSave.v1", JSON.stringify(__SAVE__));
                })();"""
                .replace("__NOW__", str(now_ms))
                .replace("__SAVE__", json.dumps(synthetic_save))
            )
            page.goto(
                f"http://127.0.0.1:{self.server.server_port}/",
                wait_until="load",
            )
            return {
                "coins": page.locator("#coins").inner_text(),
                "milk": page.locator("#milk").inner_text(),
                "auto_sell": page.locator("#autoSell").is_checked(),
            }
        finally:
            context.close()

    def test_offline_payout_is_independent_of_auto_sell_and_preserves_milk(self):
        outcomes = {}
        for auto_sell in (False, True):
            with self.subTest(auto_sell=auto_sell):
                outcomes[auto_sell] = self._run_offline_scenario(auto_sell)

        for auto_sell, outcome in outcomes.items():
            with self.subTest(auto_sell=auto_sell):
                self.assertEqual(outcome["coins"], "127")  # 7 starting + 120 offline
                self.assertEqual(outcome["milk"], "12 / 100")  # unchanged from save
                self.assertIs(outcome["auto_sell"], auto_sell)  # toggle unchanged

        self.assertEqual(outcomes[False]["coins"], outcomes[True]["coins"])
        self.assertEqual(outcomes[False]["milk"], outcomes[True]["milk"])


if __name__ == "__main__":
    unittest.main()
