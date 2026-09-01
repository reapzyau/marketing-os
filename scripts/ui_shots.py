"""Drive the local app end to end with a real browser and capture every screen.

Not part of the test suite: it needs a running server and a local Chromium.
Run it with `uv run --with playwright python scripts/ui_shots.py`.
"""
from __future__ import annotations

import pathlib
import shutil
import sys
import tempfile

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover - the test suite imports this module without a browser
    sync_playwright = None

CHROME = "/home/richard/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome"
URL = "http://127.0.0.1:4399/"
SHOTS = pathlib.Path("/mnt/c/Users/richa/Desktop/marketing-os-next/.mos-shots")
DESKTOP = {"width": 1440, "height": 900}
MOBILE = {"width": 390, "height": 844}

FIXTURE_PREFIX = "mos-shots-"


def fixture_root() -> pathlib.Path:
    """A fresh, throwaway folder for the brains the run scaffolds. It lives under the
    system temp dir and is removed when the run ends, so screenshots never leave three
    fixture brains behind in the operator's home folder."""
    return pathlib.Path(tempfile.mkdtemp(prefix=FIXTURE_PREFIX))


def shot(page, name: str, tag: str) -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    path = SHOTS / f"{name}-{tag}.png"
    page.screenshot(path=str(path))
    print("shot", path.name, flush=True)


def open_tech(page, scope: str, opened: bool = True) -> None:
    """Open or close the technical disclosures inside one region."""
    page.eval_on_selector_all(
        scope + " details.tech", "(ns, open) => ns.forEach(n => (n.open = open))", opened
    )


def set_path(page, value: str) -> None:
    """Step 1 confirms a default; the field that overrides it lives behind the quiet
    "Put it somewhere else" disclosure. Open it, type, close it."""
    page.evaluate("() => { document.getElementById('where-tech').open = true; }")
    page.fill("#in-path", value)
    page.wait_for_selector(".note--ok, .note--accent, .note--err", timeout=30000)
    page.evaluate("() => { document.getElementById('where-tech').open = false; }")
    page.wait_for_timeout(200)


def wizard(page, tag: str, target: str, mode: str, name: str, agency: str = "") -> None:
    """Walk the five steps, screenshotting each one."""
    page.wait_for_selector('.step[data-step="1"]:not([hidden])', timeout=30000)
    page.wait_for_selector(".note--ok, .note--accent", timeout=30000)
    shot(page, f"{mode}-01-where-default", tag)
    set_path(page, target)
    shot(page, f"{mode}-01-where", tag)

    page.click("#btn-next")
    page.wait_for_selector('.step[data-step="2"]:not([hidden])', timeout=20000)
    shot(page, f"{mode}-02-who-blank", tag)
    page.click(f"label[for=mode-{mode}]")
    if mode == "client":
        page.wait_for_timeout(200)
        shot(page, f"{mode}-02-who-needs-agency", tag)
        page.fill("#in-agency", agency)
    page.wait_for_timeout(200)
    shot(page, f"{mode}-02-who", tag)

    page.click("#btn-next")
    page.wait_for_selector('.step[data-step="3"]:not([hidden])', timeout=20000)
    page.fill("#in-name", name)
    page.wait_for_timeout(200)
    shot(page, f"{mode}-03-name", tag)

    page.click("#btn-next")
    page.wait_for_selector(".tree-wrap", timeout=90000)
    page.wait_for_timeout(300)
    shot(page, f"{mode}-04-preview", tag)
    page.mouse.wheel(0, 520)
    page.wait_for_timeout(250)
    shot(page, f"{mode}-04-preview-tree", tag)
    open_tech(page, "#preview-body")
    page.wait_for_timeout(200)
    shot(page, f"{mode}-04-preview-technical", tag)
    page.mouse.wheel(0, -2000)
    page.wait_for_timeout(200)

    page.click("#btn-next")
    page.wait_for_selector(".runstep", timeout=20000)
    page.wait_for_timeout(150)
    shot(page, f"{mode}-05-building", tag)
    page.wait_for_selector("text=Open the dashboard", timeout=180000)
    page.wait_for_timeout(400)
    shot(page, f"{mode}-05-done", tag)


def interview(page, tag: str) -> None:
    """The in-app interview: the hole both critics found, now filled."""
    page.click("text=Answer the questions")
    page.wait_for_selector("#iv-body .iv-card", timeout=60000)
    page.wait_for_timeout(300)
    shot(page, "17-interview-question", tag)
    page.fill(
        "#iv-answer",
        "Cascade Strength Co. is a barbell gym in Marrickville for adults who have never "
        "trained with a barbell. We coach the first six months properly and we do not sell "
        "twelve-month lock-in contracts. The promise: you squat, press and deadlift with real "
        "technique inside eight weeks, with a coach on the floor every single session.",
    )
    page.wait_for_timeout(200)
    shot(page, "18-interview-answered", tag)
    page.click("text=Review this answer")
    page.wait_for_selector("#iv-preview details.tech", timeout=90000)
    page.wait_for_timeout(400)
    shot(page, "19-interview-preview", tag)
    open_tech(page, "#iv-preview")
    page.wait_for_timeout(250)
    shot(page, "20-interview-preview-technical", tag)
    open_tech(page, "#iv-preview", False)
    page.click("text=Save this answer")
    page.wait_for_timeout(3500)
    page.wait_for_selector("#iv-body .iv-card, #iv-body .card", timeout=90000)
    page.wait_for_timeout(400)
    shot(page, "21-interview-next-question", tag)
    page.click("#iv-exit")
    page.wait_for_selector(".hero", timeout=30000)
    page.wait_for_timeout(500)
    shot(page, "22-dashboard-after-one-answer", tag)


def main() -> int:
    if sync_playwright is None:
        print("playwright is not installed; run with `uv run --with playwright`", file=sys.stderr)
        return 2
    base = fixture_root()
    try:
        return run(base)
    finally:
        shutil.rmtree(base, ignore_errors=True)


def run(base: pathlib.Path) -> int:
    """Every screen, with the fixture brains scaffolded under ``base``."""
    if SHOTS.exists():
        shutil.rmtree(SHOTS)
    SHOTS.mkdir(parents=True)
    with sync_playwright() as api:
        browser = api.chromium.launch(executable_path=CHROME)
        for tag, viewport in (("desktop", DESKTOP), ("mobile", MOBILE)):
            inhouse = f"{base}/cascade-{tag}"
            agency = f"{base}/northbeam-{tag}"
            client = f"{base}/rivermill-{tag}"
            context = browser.new_context(
                viewport=viewport, device_scale_factor=2, color_scheme="light"
            )
            page = context.new_page()
            page.on("pageerror", lambda exc: print("PAGE ERROR:", exc, file=sys.stderr))
            page.on(
                "console",
                lambda msg: print("CONSOLE", msg.type, msg.text, file=sys.stderr)
                if msg.type == "error"
                else None,
            )

            # --- boot / loading state ---------------------------------------
            page.goto(URL, wait_until="commit")
            page.wait_for_selector("#boot .spinner", timeout=20000)
            shot(page, "00-boot", tag)

            # --- in-house, all five steps -----------------------------------
            wizard(page, tag, inhouse, "in-house", "Cascade Strength Co.")

            page.click("text=Open the dashboard")
            page.wait_for_selector(".hero", timeout=90000)
            page.wait_for_timeout(500)
            shot(page, "06-dashboard", tag)
            page.mouse.wheel(0, 620)
            page.wait_for_timeout(300)
            shot(page, "07-dashboard-lower", tag)
            page.mouse.wheel(0, -2000)
            page.wait_for_timeout(200)

            # --- commands ----------------------------------------------------
            page.click("#tab-commands")
            page.wait_for_selector(".cmd-item", timeout=20000)
            page.wait_for_timeout(250)
            shot(page, "08-commands", tag)
            page.click("#cmd-buttons .btn")
            page.wait_for_timeout(120)
            shot(page, "09-commands-running", tag)
            page.wait_for_selector("#cmd-result details.tech", timeout=120000)
            page.wait_for_timeout(400)
            shot(page, "10-commands-result", tag)

            page.click(".cmd-item:has-text('Sync the assistant skills')")
            page.wait_for_timeout(300)
            shot(page, "11-commands-mutating", tag)

            # a command with a choices argument, the blocker this round fixed
            page.click(".cmd-item:has-text('Create or complete a brain')")
            page.wait_for_selector("#cmd-mode", timeout=20000)
            page.wait_for_timeout(250)
            shot(page, "23-commands-choices", tag)

            # --- the interview -------------------------------------------------
            page.click("#tab-dashboard")
            page.wait_for_selector(".hero", timeout=20000)
            page.wait_for_timeout(300)
            interview(page, tag)

            # --- agency mode, proving the client registry --------------------
            page.click("text=Set up another brain")
            wizard(page, tag, agency, "agency", "Northbeam Marketing")
            page.click("text=Open the dashboard")
            page.wait_for_selector(".hero", timeout=90000)
            page.wait_for_timeout(500)
            shot(page, "12-dashboard-agency", tag)

            # --- client mode ---------------------------------------------------
            page.click("text=Set up another brain")
            wizard(page, tag, client, "client", "Rivermill Dental", agency="Northbeam Marketing")
            page.click("text=Open the dashboard")
            page.wait_for_selector(".hero", timeout=90000)
            page.wait_for_timeout(500)
            shot(page, "client-06-dashboard", tag)

            # --- error state --------------------------------------------------
            page.route("**/api/state", lambda route: route.abort())
            page.goto(URL)
            page.wait_for_selector("#boot-actions .btn", timeout=20000)
            shot(page, "13-error-unreachable", tag)
            page.unroute("**/api/state")
            context.close()

            # --- dark mode ----------------------------------------------------
            dark = browser.new_context(
                viewport=viewport, device_scale_factor=2, color_scheme="dark"
            )
            dpage = dark.new_page()
            dpage.goto(URL)
            dpage.wait_for_selector('.step[data-step="1"]:not([hidden])', timeout=40000)
            dpage.wait_for_selector(".note--ok, .note--accent", timeout=40000)
            shot(dpage, "14-dark-where", tag)
            dpage.click("#btn-next")
            dpage.wait_for_selector('.step[data-step="2"]:not([hidden])', timeout=20000)
            dpage.click("label[for=mode-agency]")
            dpage.wait_for_timeout(250)
            shot(dpage, "15-dark-who", tag)
            dpage.evaluate("path => sessionStorage.setItem('mos.path', path)", inhouse)
            dpage.goto(URL)
            dpage.wait_for_selector(".hero", timeout=90000)
            dpage.wait_for_timeout(500)
            shot(dpage, "16-dark-dashboard", tag)
            dpage.click("text=Answer the questions")
            dpage.wait_for_selector("#iv-body .iv-card", timeout=60000)
            dpage.wait_for_timeout(400)
            shot(dpage, "24-dark-interview", tag)
            dark.close()
        browser.close()
    print("total shots:", len(list(SHOTS.glob("*.png"))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
