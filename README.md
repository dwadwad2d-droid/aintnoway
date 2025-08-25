## Roblox Community Scraper (Python)

### Features
- Tkinter GUI with URL input and live feed
- Async scraping with aiohttp for high throughput
- Inventory RAP calculation via Roblox Collectibles API
- Discord username/link discovery from profile description
- Group Discord invite extraction from group social links
- Robust retries, backoff, and error handling

### Run locally
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m src.app
```

### Build Windows .exe (PyInstaller)
On Windows:
```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
pyinstaller --noconfirm --onefile --windowed --name RobloxScraper src/app.py
```
The executable will be in `dist/RobloxScraper.exe`.

If certificate/network errors occur behind proxies, add `--collect-all certifi` and ensure network access is allowed.

### Usage
- Paste a Roblox group URL like `https://www.roblox.com/groups/123456/My-Group`
- Click Start Scraping
- Watch live feed; results section summarizes totals and the group Discord invite.

### Notes
- Throughput is constrained by Roblox rate limits. The scraper uses concurrency, retries, and backoff to maximize speed while respecting limits.
- Inventory value uses RAP (recentAveragePrice) of collectibles. Private inventories are detected and reported.
- Discord usernames are best-effort guesses from profile descriptions; there is no official Roblox API for user social profiles beyond text.