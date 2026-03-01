# Playwright Bot Template

A minimal Python template for launching a real Google Chrome instance and automating it via CDP (Chrome DevTools Protocol) using Playwright.

This connects to your actual Chrome profile, retaining all your sessions, cookies, and login state. No need to log in again -- it works just like your regular browser, but automated. Use this as a starting point to automate any workflow you normally do by hand in Chrome.

## What It Does

1. Quits any running Chrome instance gracefully
2. Creates a CDP wrapper directory (symlinks + profile copy for cookie decryption)
3. Launches Chrome with remote debugging enabled
4. Connects Playwright over CDP
5. Navigates to Google, searches for "playwright", clicks the first result
6. Verifies a heading is visible on the page
7. Waits briefly, then closes the browser

## Setup

```bash
pip install -e .
```

Playwright browsers must be installed:

```bash
playwright install chromium
```

## Usage

```bash
bash app.sh
```

Or run directly:

```bash
python main.py
```

## Configuration

All settings are defined as constants at the top of `main.py`:

| Constant         | Description                          | Default                              |
|------------------|--------------------------------------|--------------------------------------|
| `CHROME_PATH`    | Path to Chrome executable            | `/Applications/Google Chrome.app/...`|
| `USER_DATA_DIR`  | Chrome user data directory           | `~/Library/Application Support/Google/Chrome` |
| `PROFILE`        | Chrome profile directory name        | `Default`                            |
| `CDP_PORT`       | Remote debugging port                | `9222`                               |

## Requirements

- Python 3.12+
- Google Chrome installed
- macOS (uses AppleScript for Chrome lifecycle management)

## Disclaimer

This tool is provided as-is for educational and personal use. Use it responsibly and in compliance with the terms of service of any website you automate. You are solely responsible for any actions performed using this tool. The author assumes no liability for any consequences resulting from its use.
