"""Template: launch Chrome via CDP, navigate to Google, wait, and close."""

import asyncio
import json
import logging
import os
import shutil
import subprocess
import tempfile

from playwright.async_api import async_playwright

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
USER_DATA_DIR = os.path.expanduser("~/Library/Application Support/Google/Chrome")
PROFILE = "Default"
CDP_PORT = 9222


def is_chrome_running() -> bool:
    """Check if Google Chrome is currently running.

    Returns:
        True if Chrome is running, False otherwise.
    """
    try:
        result = subprocess.run(
            ["pgrep", "-x", "Google Chrome"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0 and result.stdout.strip() != ""
    except OSError:
        return False


async def quit_chrome() -> None:
    """Gracefully quit Google Chrome via AppleScript and wait for exit.

    Raises:
        TimeoutError: If Chrome does not quit within 5 seconds.
    """
    logger.info("Quitting existing Chrome instance...")
    subprocess.run(
        ["osascript", "-e", 'quit app "Google Chrome"'],
        check=True,
    )

    elapsed = 0.0
    while is_chrome_running():
        if elapsed >= 5.0:
            raise TimeoutError(
                "Chrome did not quit within the timeout. Close it manually and retry."
            )
        await asyncio.sleep(0.25)
        elapsed += 0.25

    logger.info("Chrome has quit")


def create_cdp_wrapper(profile: str) -> str:
    """Create a temp wrapper directory with symlinks to the real Chrome profile.

    Chrome blocks remote debugging when --user-data-dir points to its own
    default data directory. This creates a wrapper at a temp path with symlinks
    for most entries, but copies the target profile so Chrome can decrypt cookies.

    Args:
        profile: The Chrome profile directory name (e.g., "Profile 1").

    Returns:
        The path to the wrapper directory to use as --user-data-dir.
    """
    wrapper = os.path.join(tempfile.gettempdir(), "chrome-cdp-wrapper")

    if os.path.exists(wrapper):
        shutil.rmtree(wrapper)

    os.makedirs(wrapper)

    skip = {profile, "SingletonLock", "SingletonCookie", "SingletonSocket"}

    for entry in os.listdir(USER_DATA_DIR):
        if entry in skip:
            continue
        os.symlink(
            os.path.join(USER_DATA_DIR, entry),
            os.path.join(wrapper, entry),
        )

    profile_source = os.path.join(USER_DATA_DIR, profile)
    profile_dest = os.path.join(wrapper, profile)

    def ignore_ephemeral(_directory: str, entries: list[str]) -> set[str]:
        """Skip ephemeral Chrome files that vanish after Chrome quits."""
        return {"SingletonLock", "SingletonCookie", "SingletonSocket", "RunningChromeVersion"} & set(entries)

    logger.info("Copying profile '%s' to wrapper...", profile)
    shutil.copytree(
        profile_source,
        profile_dest,
        ignore=ignore_ephemeral,
        ignore_dangling_symlinks=True,
    )

    # Mark the copied profile as cleanly exited to avoid the "Restore pages?" bar
    prefs_path = os.path.join(profile_dest, "Preferences")
    if os.path.exists(prefs_path):
        with open(prefs_path, "r", encoding="utf-8") as f:
            prefs = json.load(f)
        prefs.setdefault("profile", {})["exit_type"] = "Normal"
        prefs["profile"]["exited_cleanly"] = True
        with open(prefs_path, "w", encoding="utf-8") as f:
            json.dump(prefs, f, indent=3)

    logger.info("Created CDP wrapper: %s", wrapper)
    return wrapper


async def main() -> None:
    """Launch Chrome, search Google for 'playwright', click the first result, verify the page, and close."""
    if is_chrome_running():
        await quit_chrome()

    wrapper = create_cdp_wrapper(PROFILE)

    chrome_args = [
        CHROME_PATH,
        f"--remote-debugging-port={CDP_PORT}",
        f"--user-data-dir={wrapper}",
        f"--profile-directory={PROFILE}",
        "--window-size=1720,1440",
    ]

    logger.info("Launching Chrome with profile '%s'...", PROFILE)
    chrome_process = subprocess.Popen(
        chrome_args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    cdp_url = f"http://127.0.0.1:{CDP_PORT}"
    pw = await async_playwright().start()

    await asyncio.sleep(3)

    try:
        logger.info("Connecting to Chrome via CDP...")
        browser = await pw.chromium.connect_over_cdp(cdp_url)
        logger.info("Connected")

        context = browser.contexts[0]

        # Find the visible new-tab page and navigate it directly
        page = None
        for candidate in context.pages:
            if "new-tab" in candidate.url:
                page = candidate
                break

        if page is None:
            page = await context.new_page()

        await page.bring_to_front()

        logger.info("Navigating to Google...")
        await page.goto("https://www.google.com")
        logger.info("Page loaded")

        logger.info("Searching for 'playwright'...")
        search_box = page.locator('textarea[name="q"]')
        await search_box.fill("playwright")
        await search_box.press("Enter")
        await page.wait_for_load_state("load")
        logger.info("Search results loaded")

        logger.info("Clicking first search result...")
        first_result = page.locator("#search a h3").first
        await first_result.click()
        await page.wait_for_load_state("load")
        logger.info("Clicked: %s", page.url)

        heading = page.get_by_text("Playwright enables reliable end-to-end testing for modern web apps.")
        if await heading.is_visible():
            logger.info("VERIFIED: heading is visible on the page")
        else:
            logger.error("FAILED: heading not found on the page")

        logger.info("Waiting 2 seconds...")
        await asyncio.sleep(2)

        logger.info("Closing browser...")
        await browser.close()
    finally:
        await pw.stop()
        chrome_process.terminate()
        logger.info("Done")


if __name__ == "__main__":
    asyncio.run(main())
