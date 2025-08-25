import asyncio
import queue
import re
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox

from scraper import RobloxScraper, ScrapeResult


class App:
	def __init__(self, root: tk.Tk) -> None:
		self.root = root
		self.root.title("Roblox Community Scraper")
		self.root.geometry("900x600")

		self.url_label = tk.Label(root, text="Roblox Group URL:")
		self.url_label.pack(anchor="w", padx=10, pady=(10, 0))

		self.url_entry = tk.Entry(root, width=100)
		self.url_entry.pack(fill="x", padx=10, pady=5)

		self.start_button = tk.Button(root, text="Start Scraping", command=self.start_scrape)
		self.start_button.pack(padx=10, pady=5)

		self.feed = scrolledtext.ScrolledText(root, height=25, state="disabled")
		self.feed.pack(fill="both", expand=True, padx=10, pady=10)

		self.message_queue: "queue.Queue[str]" = queue.Queue()
		self.worker_thread: threading.Thread | None = None
		self.is_scraping = False

		self.root.after(100, self.drain_queue)

	def log(self, text: str) -> None:
		self.feed.configure(state="normal")
		self.feed.insert(tk.END, text + "\n")
		self.feed.see(tk.END)
		self.feed.configure(state="disabled")

	def start_scrape(self) -> None:
		if self.is_scraping:
			messagebox.showinfo("Scraper", "Scrape already in progress.")
			return

		url = self.url_entry.get().strip()
		if not url:
			messagebox.showerror("Error", "Please enter a Roblox group URL.")
			return

		group_id = self.extract_group_id(url)
		if not group_id:
			messagebox.showerror("Error", "Could not parse group ID from URL.")
			return

		self.is_scraping = True
		self.start_button.config(state="disabled")
		self.feed.configure(state="normal")
		self.feed.delete("1.0", tk.END)
		self.feed.configure(state="disabled")

		self.worker_thread = threading.Thread(target=self._run_scrape_thread, args=(group_id,), daemon=True)
		self.worker_thread.start()

	def _run_scrape_thread(self, group_id: int) -> None:
		asyncio.run(self._run_scrape_async(group_id))

	async def _run_scrape_async(self, group_id: int) -> None:
		self.message_queue.put(f"Starting scrape for group {group_id}...")
		scraper = RobloxScraper(message_cb=self.message_queue.put)
		try:
			result: ScrapeResult = await scraper.scrape_group(group_id)
			self.message_queue.put("")
			self.message_queue.put("=== Results ===")
			if result.group_discord_invite:
				self.message_queue.put(f"Group Discord: {result.group_discord_invite}")
			else:
				self.message_queue.put("Group Discord: Not found")
			self.message_queue.put(f"Members processed: {result.members_processed}")
			self.message_queue.put(f"Errors: {result.errors}")
			self.message_queue.put("================")
		except Exception as exc:  # noqa: BLE001
			self.message_queue.put(f"Fatal error: {exc}")
		finally:
			self.message_queue.put("Scrape finished.")
			self.is_scraping = False
			self.start_button.config(state="normal")

	def extract_group_id(self, url: str) -> int | None:
		match = re.search(r"/groups/(\d+)/", url)
		if match:
			try:
				return int(match.group(1))
			except ValueError:
				return None
		return None

	def drain_queue(self) -> None:
		try:
			while True:
				msg = self.message_queue.get_nowait()
				self.log(msg)
		except queue.Empty:
			pass
		finally:
			self.root.after(100, self.drain_queue)


if __name__ == "__main__":
	root = tk.Tk()
	app = App(root)
	root.mainloop()