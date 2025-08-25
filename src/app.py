import asyncio
import queue
import re
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
from tkinter.font import Font

from scraper import RobloxScraper, ScrapeResult


class ModernApp:
	def __init__(self, root: tk.Tk) -> None:
		self.root = root
		self.root.title("Roblox Community Scraper")
		self.root.geometry("1000x700")
		self.root.configure(bg="#f0f0f0")
		
		# Configure styles
		self.setup_styles()
		
		# Create main container
		self.main_frame = tk.Frame(root, bg="#f0f0f0")
		self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
		
		# Header
		self.create_header()
		
	# Input section
		self.create_input_section()
		
		# Progress section
		self.create_progress_section()
		
		# Results section
		self.create_results_section()
		
		# Live feed
		self.create_live_feed()
		
		# Initialize state
		self.message_queue: "queue.Queue[str]" = queue.Queue()
		self.worker_thread: threading.Thread | None = None
		self.is_scraping = False
		self.stats = {"processed": 0, "errors": 0, "discord_found": 0}
		
		self.root.after(100, self.drain_queue)

	def setup_styles(self):
		# Configure ttk styles
		style = ttk.Style()
		style.theme_use('clam')
		
		# Custom button style
		style.configure('Modern.TButton',
			background='#007bff',
			foreground='white',
			borderwidth=0,
			focuscolor='none',
			font=('Segoe UI', 10, 'bold')
		)
		
		style.map('Modern.TButton',
			background=[('active', '#0056b3'), ('pressed', '#004085')]
		)

	def create_header(self):
		header_frame = tk.Frame(self.main_frame, bg="#f0f0f0")
		header_frame.pack(fill="x", pady=(0, 20))
		
		title = tk.Label(header_frame, 
			text="Roblox Community Scraper", 
			font=Font(family="Segoe UI", size=24, weight="bold"),
			fg="#2c3e50",
			bg="#f0f0f0"
		)
		title.pack()
		
		subtitle = tk.Label(header_frame,
			text="Scrape inventory values and Discord information from Roblox communities",
			font=Font(family="Segoe UI", size=12),
			fg="#7f8c8d",
			bg="#f0f0f0"
		)
		subtitle.pack(pady=(5, 0))

	def create_input_section(self):
		input_frame = tk.Frame(self.main_frame, bg="white", relief="flat", bd=1)
		input_frame.pack(fill="x", pady=(0, 20))
		
		# URL input
		url_container = tk.Frame(input_frame, bg="white")
		url_container.pack(fill="x", padx=20, pady=20)
		
		url_label = tk.Label(url_container,
			text="Roblox Community URL:",
			font=Font(family="Segoe UI", size=11, weight="bold"),
			fg="#2c3e50",
			bg="white"
		)
		url_label.pack(anchor="w", pady=(0, 8))
		
		self.url_entry = tk.Entry(url_container,
			font=Font(family="Segoe UI", size=10),
			relief="solid",
			bd=1,
			highlightthickness=1,
			highlightcolor="#007bff",
			highlightbackground="#e1e8ed"
		)
		self.url_entry.pack(fill="x", pady=(0, 15))
		
		# Start button
		self.start_button = ttk.Button(url_container,
			text="🚀 Start Scraping",
			style='Modern.TButton',
			command=self.start_scrape
		)
		self.start_button.pack(pady=(0, 10))

	def create_progress_section(self):
		progress_frame = tk.Frame(self.main_frame, bg="white", relief="flat", bd=1)
		progress_frame.pack(fill="x", pady=(0, 20))
		
		progress_container = tk.Frame(progress_frame, bg="white")
		progress_container.pack(fill="x", padx=20, pady=20)
		
		progress_label = tk.Label(progress_container,
			text="Progress",
			font=Font(family="Segoe UI", size=11, weight="bold"),
			fg="#2c3e50",
			bg="white"
		)
		progress_label.pack(anchor="w", pady=(0, 15))
		
		# Progress bar
		self.progress_var = tk.DoubleVar()
		self.progress_bar = ttk.Progressbar(progress_container,
			variable=self.progress_var,
			maximum=100,
			length=400,
			mode='indeterminate'
		)
		self.progress_bar.pack(anchor="w")
		
		# Status label
		self.status_label = tk.Label(progress_container,
			text="Ready to start",
			font=Font(family="Segoe UI", size=10),
			fg="#7f8c8d",
			bg="white"
		)
		self.status_label.pack(anchor="w", pady=(10, 0))

	def create_results_section(self):
		results_frame = tk.Frame(self.main_frame, bg="white", relief="flat", bd=1)
		results_frame.pack(fill="x", pady=(0, 20))
		
		results_container = tk.Frame(results_frame, bg="white")
		results_container.pack(fill="x", padx=20, pady=20)
		
		results_label = tk.Label(results_container,
			text="Results Summary",
			font=Font(family="Segoe UI", size=11, weight="bold"),
			fg="#2c3e50",
			bg="white"
		)
		results_label.pack(anchor="w", pady=(0, 15))
		
		# Stats grid
		stats_frame = tk.Frame(results_container, bg="white")
		stats_frame.pack(fill="x")
		
		# Members processed
		self.processed_label = tk.Label(stats_frame,
			text="Members Processed: 0",
			font=Font(family="Segoe UI", size=10),
			fg="#27ae60",
			bg="white"
		)
		self.processed_label.grid(row=0, column=0, sticky="w", padx=(0, 30))
		
		# Errors
		self.errors_label = tk.Label(stats_frame,
			text="Errors: 0",
			font=Font(family="Segoe UI", size=10),
			fg="#e74c3c",
			bg="white"
		)
		self.errors_label.grid(row=0, column=1, sticky="w", padx=(0, 30))
		
		# Discord found
		self.discord_label = tk.Label(stats_frame,
			text="Discord Users Found: 0",
			font=Font(family="Segoe UI", size=10),
			fg="#3498db",
			bg="white"
		)
		self.discord_label.grid(row=0, column=2, sticky="w")
		
		# Group Discord
		self.group_discord_label = tk.Label(results_container,
			text="Group Discord: Not found",
			font=Font(family="Segoe UI", size=10),
			fg="#9b59b6",
			bg="white"
		)
		self.group_discord_label.pack(anchor="w", pady=(15, 0))

	def create_live_feed(self):
		feed_frame = tk.Frame(self.main_frame, bg="white", relief="flat", bd=1)
		feed_frame.pack(fill="both", expand=True)
		
		feed_container = tk.Frame(feed_frame, bg="white")
		feed_container.pack(fill="both", expand=True, padx=20, pady=20)
		
		feed_label = tk.Label(feed_container,
			text="Live Feed",
			font=Font(family="Segoe UI", size=11, weight="bold"),
			fg="#2c3e50",
			bg="white"
		)
		feed_label.pack(anchor="w", pady=(0, 15))
		
		# Feed text area
		self.feed = scrolledtext.ScrolledText(feed_container,
			height=15,
			state="disabled",
			font=Font(family="Consolas", size=9),
			bg="#f8f9fa",
			fg="#2c3e50",
			relief="solid",
			bd=1,
			insertbackground="#007bff"
		)
		self.feed.pack(fill="both", expand=True)

	def log(self, text: str) -> None:
		self.feed.configure(state="normal")
		self.feed.insert(tk.END, text + "\n")
		self.feed.see(tk.END)
		self.feed.configure(state="disabled")

	def update_stats(self, processed: int, errors: int, discord_found: int):
		self.processed_label.config(text=f"Members Processed: {processed}")
		self.errors_label.config(text=f"Errors: {errors}")
		self.discord_label.config(text=f"Discord Users Found: {discord_found}")

	def start_scrape(self) -> None:
		if self.is_scraping:
			messagebox.showinfo("Scraper", "Scrape already in progress.")
			return

		url = self.url_entry.get().strip()
		if not url:
			messagebox.showerror("Error", "Please enter a Roblox community URL.")
			return

		group_id = self.extract_group_id(url)
		if not group_id:
			messagebox.showerror("Error", "Could not parse community ID from URL.")
			return

		self.is_scraping = True
		self.start_button.config(state="disabled")
		self.progress_bar.start()
		self.status_label.config(text="Scraping in progress...")
		self.feed.configure(state="normal")
		self.feed.delete("1.0", tk.END)
		self.feed.configure(state="disabled")
		
		# Reset stats
		self.stats = {"processed": 0, "errors": 0, "discord_found": 0}
		self.update_stats(0, 0, 0)
		self.group_discord_label.config(text="Group Discord: Checking...")

		self.worker_thread = threading.Thread(target=self._run_scrape_thread, args=(group_id,), daemon=True)
		self.worker_thread.start()

	def _run_scrape_thread(self, group_id: int) -> None:
		asyncio.run(self._run_scrape_async(group_id))

	async def _run_scrape_async(self, group_id: int) -> None:
		self.message_queue.put(f"🚀 Starting scrape for community {group_id}...")
		scraper = RobloxScraper(message_cb=self.message_queue.put)
		try:
			result: ScrapeResult = await scraper.scrape_group(group_id)
			
			# Update final stats
			discord_count = sum(1 for m in result.members if m.discord_username_guess or m.discord_links)
			self.stats = {
				"processed": result.members_processed,
				"errors": result.errors,
				"discord_found": discord_count
			}
			
			self.message_queue.put("")
			self.message_queue.put("🎉 === SCRAPING COMPLETE ===")
			if result.group_discord_invite:
				self.message_queue.put(f"📱 Group Discord: {result.group_discord_invite}")
				self.group_discord_label.config(text=f"Group Discord: {result.group_discord_invite}")
			else:
				self.message_queue.put("❌ Group Discord: Not found")
				self.group_discord_label.config(text="Group Discord: Not found")
			
			self.message_queue.put(f"✅ Members processed: {result.members_processed}")
			self.message_queue.put(f"❌ Errors: {result.errors}")
			self.message_queue.put(f"🎯 Discord users found: {discord_count}")
			self.message_queue.put("================================")
			
			# Update stats display
			self.update_stats(result.members_processed, result.errors, discord_count)
			
		except Exception as exc:  # noqa: BLE001
			self.message_queue.put(f"💥 Fatal error: {exc}")
			self.status_label.config(text="Error occurred")
		finally:
			self.message_queue.put("🏁 Scrape finished.")
			self.is_scraping = False
			self.start_button.config(state="normal")
			self.progress_bar.stop()
			self.status_label.config(text="Ready to start")

	def extract_group_id(self, url: str) -> int | None:
		# Handle both old /groups/ and new /communities/ formats
		# Also handle URLs with #!/about or other fragments
		match = re.search(r"/(?:groups|communities)/(\d+)(?:/|#!/|$)", url)
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
	app = ModernApp(root)
	root.mainloop()