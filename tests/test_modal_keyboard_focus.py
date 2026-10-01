"""Run with `python -B -m unittest discover -s tests -v` after installing
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


class ModalKeyboardFocusTests(unittest.TestCase):
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

    def setUp(self):
        self.context = self.browser.new_context(viewport={"width": 390, "height": 844})
        self.page = self.context.new_page()

    def tearDown(self):
        self.context.close()

    def test_reset_dialog_traps_tab_and_escape_returns_focus_to_opener(self):
        self.page.goto(f"http://127.0.0.1:{self.server.server_port}/", wait_until="load")
        self.page.get_by_role("button", name="↺ Reset").click()

        dialog = self.page.get_by_role("dialog")
        self.assertTrue(dialog.is_visible())
        self.assertEqual(self.page.evaluate("() => document.activeElement.textContent"), "Cancel")

        self.page.keyboard.press("Shift+Tab")
        self.assertEqual(self.page.evaluate("() => document.activeElement.textContent"), "Yes, reset")
        self.page.keyboard.press("Tab")
        self.assertEqual(self.page.evaluate("() => document.activeElement.textContent"), "Cancel")

        self.page.keyboard.press("Escape")
        self.assertFalse(dialog.is_visible())
        self.assertEqual(self.page.evaluate("() => document.activeElement.id"), "resetBtn")

    def test_single_action_offline_dialog_keeps_tab_focus_on_collect(self):
        self.page.add_init_script(
            """(() => {
              localStorage.setItem("cowCashSave.v1", JSON.stringify({
                coins: 0,
                milk: 0,
                totalMilk: 0,
                autoSell: false,
                owned: {cow: 1, machine: 0, feed: 0, barn: 0},
                lastSaved: Date.now() - 60_000
              }));
            })();"""
        )
        self.page.goto(f"http://127.0.0.1:{self.server.server_port}/", wait_until="load")

        dialog = self.page.get_by_role("dialog")
        collect = dialog.get_by_role("button", name="Collect")
        self.assertTrue(dialog.is_visible())
        self.assertTrue(collect.evaluate("el => el === document.activeElement"))

        self.page.keyboard.press("Tab")
        self.assertTrue(collect.evaluate("el => el === document.activeElement"))
        self.page.keyboard.press("Shift+Tab")
        self.assertTrue(collect.evaluate("el => el === document.activeElement"))


if __name__ == "__main__":
    unittest.main()
