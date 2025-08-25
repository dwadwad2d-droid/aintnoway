import asyncio
import queue
import re
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
from tkinter.font import Font

from scraper import RobloxScraper, ScrapeResult


class DarkRobloxScraper:
	def __init__(self, root: tk.Tk) -> None:
		self.root = root
		self.root.title("Roblox Community Scraper - Dark Theme")
		self.root.geometry("1000x700")
		self.root.configure(bg="#0d1117")
		
		# Configure dark theme styles
		self.setup_dark_styles()
		
		# Create main container
		self.main_frame = tk.Frame(root, bg="#0d1117")
		self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
		
		# Header
		self.create_header()
		
		# Input section
		self.create_input_section()
		
		# Progress section
		self.create_progress_section()
		
		# Results section
		self.create_results_section()
		
		# Create notebook for tabs
		self.notebook = ttk.Notebook(self.main_frame)
		self.notebook.pack(fill="both", expand=True, pady=(0, 20))
		
		# Live feed tab
		self.create_live_feed_tab()
		
		# Leaderboard tab
		self.create_leaderboard_tab()
		
		# Initialize state
		self.message_queue: "queue.Queue[str]" = queue.Queue()
		self.worker_thread: threading.Thread | None = None
		self.is_scraping = False
		self.stats = {"processed": 0, "errors": 0, "discord_found": 0}
		self.leaderboard_data = []
		
		# Performance settings
		self.high_performance_mode = True
		
		self.root.after(100, self.drain_queue)

	def setup_dark_styles(self):
		# Configure ttk styles for dark theme
		style = ttk.Style()
		style.theme_use('clam')
		
		# Configure notebook style
		style.configure('TNotebook', background='#0d1117', borderwidth=0)
		style.configure('TNotebook.Tab', 
			background='#21262d', 
			foreground='#f0f6fc',
			padding=[20, 10],
			font=('Segoe UI', 9)
		)
		style.map('TNotebook.Tab',
			background=[('selected', '#238636'), ('active', '#30363d')],
			foreground=[('selected', '#ffffff'), ('active', '#ffffff')]
		)
		
		# Configure treeview style
		style.configure('Treeview', 
			background='#21262d',
			foreground='#f0f6fc',
			fieldbackground='#21262d',
			borderwidth=0
		)
		style.configure('Treeview.Heading',
			background='#30363d',
			foreground='#f0f6fc',
			font=('Segoe UI', 9, 'bold')
		)
		style.map('Treeview',
			background=[('selected', '#238636')],
			foreground=[('selected', '#ffffff')]
		)
		
		# Custom button style
		style.configure('Dark.TButton',
			background='#238636',
			foreground='white',
			borderwidth=0,
			focuscolor='none',
			font=('Segoe UI', 10, 'bold')
		)
		
		style.map('Dark.TButton',
			background=[('active', '#2ea043'), ('pressed', '#1f6f3a')]
		)

	def create_header(self):
		header_frame = tk.Frame(self.main_frame, bg="#0d1117")
		header_frame.pack(fill="x", pady=(0, 20))
		
		title = tk.Label(header_frame, 
			text="Roblox Community Scraper", 
			font=Font(family="Segoe UI", size=24, weight="bold"),
			fg="#f0f6fc",
			bg="#0d1117"
		)
		title.pack()
		
		subtitle = tk.Label(header_frame,
			text="Scrape inventory values and Discord information from Roblox communities",
			font=Font(family="Segoe UI", size=12),
			fg="#8b949e",
			bg="#0d1117"
		)
		subtitle.pack(pady=(5, 0))

	def create_input_section(self):
		input_frame = tk.Frame(self.main_frame, bg="#21262d", relief="flat", bd=1)
		input_frame.pack(fill="x", pady=(0, 20))
		
		# URL input
		url_container = tk.Frame(input_frame, bg="#21262d")
		url_container.pack(fill="x", padx=20, pady=20)
		
		url_label = tk.Label(url_container,
			text="Roblox Community URL:",
			font=Font(family="Segoe UI", size=11, weight="bold"),
			fg="#f0f6fc",
			bg="#21262d"
		)
		url_label.pack(anchor="w", pady=(0, 8))
		
		self.url_entry = tk.Entry(url_container,
			font=Font(family="Segoe UI", size=10),
			relief="solid",
			bd=1,
			highlightthickness=1,
			highlightcolor="#238636",
			highlightbackground="#30363d",
			bg="#0d1117",
			fg="#f0f6fc",
			insertbackground="#238636"
		)
		self.url_entry.pack(fill="x", pady=(0, 15))
		
		# Start button
		self.start_button = ttk.Button(url_container,
			text="🚀 Start Scraping",
			style='Dark.TButton',
			command=self.start_scrape
		)
		self.start_button.pack(pady=(0, 10))

	def create_progress_section(self):
		progress_frame = tk.Frame(self.main_frame, bg="#21262d", relief="flat", bd=1)
		progress_frame.pack(fill="x", pady=(0, 20))
		
		progress_container = tk.Frame(progress_frame, bg="#21262d")
		progress_container.pack(fill="x", padx=20, pady=20)
		
		progress_label = tk.Label(progress_container,
			text="Progress",
			font=Font(family="Segoe UI", size=11, weight="bold"),
			fg="#f0f6fc",
			bg="#21262d"
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
			fg="#8b949e",
			bg="#21262d"
		)
		self.status_label.pack(anchor="w", pady=(10, 0))
		
		# Performance indicator
		perf_label = tk.Label(progress_container,
			text="🚀 High Performance Mode: 2560 concurrent requests",
			font=Font(family="Segoe UI", size=9),
			fg="#3fb950",
			bg="#21262d"
		)
		perf_label.pack(anchor="w", pady=(5, 0))

	def create_results_section(self):
		results_frame = tk.Frame(self.main_frame, bg="#21262d", relief="flat", bd=1)
		results_frame.pack(fill="x", pady=(0, 20))
		
		results_container = tk.Frame(results_frame, bg="#21262d")
		results_container.pack(fill="x", padx=20, pady=20)
		
		results_label = tk.Label(results_container,
			text="Results Summary",
			font=Font(family="Segoe UI", size=11, weight="bold"),
			fg="#f0f6fc",
			bg="#21262d"
		)
		results_label.pack(anchor="w", pady=(0, 15))
		
		# Stats grid
		stats_frame = tk.Frame(results_container, bg="#21262d")
		stats_frame.pack(fill="x")
		
		# Members processed
		self.processed_label = tk.Label(stats_frame,
			text="Members Processed: 0",
			font=Font(family="Segoe UI", size=10),
			fg="#3fb950",
			bg="#21262d"
		)
		self.processed_label.grid(row=0, column=0, sticky="w", padx=(0, 30))
		
		# Errors
		self.errors_label = tk.Label(stats_frame,
			text="Errors: 0",
			font=Font(family="Segoe UI", size=10),
			fg="#f85149",
			bg="#21262d"
		)
		self.errors_label.grid(row=0, column=1, sticky="w", padx=(0, 30))
		
		# Discord found
		self.discord_label = tk.Label(stats_frame,
			text="Discord Users Found: 0",
			font=Font(family="Segoe UI", size=10),
			fg="#58a6ff",
			bg="#21262d"
		)
		self.discord_label.grid(row=0, column=2, sticky="w")
		
		# Group Discord
		self.group_discord_label = tk.Label(results_container,
			text="Group Discord: Not found",
			font=Font(family="Segoe UI", size=10),
			fg="#bc8cff",
			bg="#21262d"
		)
		self.group_discord_label.pack(anchor="w", pady=(15, 0))

	def create_live_feed_tab(self):
		feed_frame = tk.Frame(self.notebook, bg="#0d1117")
		self.notebook.add(feed_frame, text="📊 Live Feed")
		
		feed_container = tk.Frame(feed_frame, bg="#0d1117")
		feed_container.pack(fill="both", expand=True, padx=20, pady=20)
		
		feed_label = tk.Label(feed_container,
			text="Live Feed",
			font=Font(family="Segoe UI", size=11, weight="bold"),
			fg="#f0f6fc",
			bg="#0d1117"
		)
		feed_label.pack(anchor="w", pady=(0, 15))
		
		# Feed text area
		self.feed = scrolledtext.ScrolledText(feed_container,
			height=15,
			state="disabled",
			font=Font(family="Consolas", size=9),
			bg="#21262d",
			fg="#f0f6fc",
			relief="solid",
			bd=1,
			insertbackground="#238636"
		)
		self.feed.pack(fill="both", expand=True)

	def create_leaderboard_tab(self):
		leaderboard_frame = tk.Frame(self.notebook, bg="#0d1117")
		self.notebook.add(leaderboard_frame, text="🏆 Leaderboard")
		
		leaderboard_container = tk.Frame(leaderboard_frame, bg="#0d1117")
		leaderboard_container.pack(fill="both", expand=True, padx=20, pady=20)
		
		# Header
		header_label = tk.Label(leaderboard_container,
			text="Richest Players Leaderboard",
			font=Font(family="Segoe UI", size=16, weight="bold"),
			fg="#f0f6fc",
			bg="#0d1117"
		)
		header_label.pack(pady=(0, 20))
		
		# Info text
		info_label = tk.Label(leaderboard_container,
			text="Players with limited items, sorted by total RAP value",
			font=Font(family="Segoe UI", size=10),
			fg="#8b949e",
			bg="#0d1117"
		)
		info_label.pack(pady=(0, 20))
		
		# Create Treeview for leaderboard
		columns = ("Rank", "Username", "Display Name", "RAP Value", "Discord Info")
		self.leaderboard_tree = ttk.Treeview(leaderboard_container, columns=columns, show="headings", height=20)
		
		# Configure columns
		self.leaderboard_tree.heading("Rank", text="Rank")
		self.leaderboard_tree.heading("Username", text="Username")
		self.leaderboard_tree.heading("Display Name", text="Display Name")
		self.leaderboard_tree.heading("RAP Value", text="RAP Value")
		self.leaderboard_tree.heading("Discord Info", text="Discord Info")
		
		# Column widths
		self.leaderboard_tree.column("Rank", width=60, anchor="center")
		self.leaderboard_tree.column("Username", width=150, anchor="w")
		self.leaderboard_tree.column("Display Name", width=150, anchor="w")
		self.leaderboard_tree.column("RAP Value", width=120, anchor="e")
		self.leaderboard_tree.column("Discord Info", width=200, anchor="w")
		
		# Add scrollbar
		scrollbar = ttk.Scrollbar(leaderboard_container, orient="vertical", command=self.leaderboard_tree.yview)
		self.leaderboard_tree.configure(yscrollcommand=scrollbar.set)
		
		# Pack tree and scrollbar
		self.leaderboard_tree.pack(side="left", fill="both", expand=True)
		scrollbar.pack(side="right", fill="y")
		
		# Export button
		export_button = ttk.Button(leaderboard_container,
			text="📥 Export to CSV",
			style='Dark.TButton',
			command=self.export_leaderboard
		)
		export_button.pack(pady=(20, 0))

	def log(self, text: str) -> None:
		self.feed.configure(state="normal")
		self.feed.insert(tk.END, text + "\n")
		self.feed.see(tk.END)
		self.feed.configure(state="disabled")

	def update_stats(self, processed: int, errors: int, discord_found: int):
		self.processed_label.config(text=f"Members Processed: {processed}")
		self.errors_label.config(text=f"Errors: {errors}")
		self.discord_label.config(text=f"Discord Users Found: {discord_found}")

	def update_leaderboard(self, members: list):
		"""Update the leaderboard with scraped member data"""
		# Clear existing items
		for item in self.leaderboard_tree.get_children():
			self.leaderboard_tree.delete(item)
		
		# Filter members with limited items and sort by RAP
		rich_members = [m for m in members if m.rap_total and m.rap_total > 0 and not m.inventory_private]
		rich_members.sort(key=lambda x: x.rap_total, reverse=True)
		
		# Store for export
		self.leaderboard_data = rich_members
		
		# Add to treeview
		for rank, member in enumerate(rich_members, 1):
			discord_info = member.discord_username_guess or ("; ".join(member.discord_links) if member.discord_links else "Not found")
			
			self.leaderboard_tree.insert("", "end", values=(
				rank,
				member.username,
				member.display_name,
				f"{member.rap_total:,}",
				discord_info
			))
		
		# Update stats
		self.discord_label.config(text=f"Discord Users Found: {len([m for m in members if m.discord_username_guess or m.discord_links])}")

	def export_leaderboard(self):
		"""Export leaderboard data to CSV"""
		if not self.leaderboard_data:
			messagebox.showinfo("Export", "No data to export. Run a scrape first.")
			return
		
		try:
			import csv
			from tkinter import filedialog
			
			filename = filedialog.asksaveasfilename(
				defaultextension=".csv",
				filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
				title="Save Leaderboard CSV"
			)
			
			if filename:
				with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
					writer = csv.writer(csvfile)
					writer.writerow(['Rank', 'Username', 'Display Name', 'RAP Value', 'Discord Info'])
					
					for rank, member in enumerate(self.leaderboard_data, 1):
						discord_info = member.discord_username_guess or ("; ".join(member.discord_links) if member.discord_links else "Not found")
						writer.writerow([
							rank,
							member.username,
							member.display_name,
							member.rap_total,
							discord_info
						])
				
				messagebox.showinfo("Export", f"Leaderboard exported to {filename}")
		except Exception as e:
			messagebox.showerror("Export Error", f"Failed to export: {e}")

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
		self.message_queue.put(f"⚡ High Performance Mode: Processing up to 2560 members concurrently")
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
			
			# Update leaderboard
			self.update_leaderboard(result.members)
			
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
	app = DarkRobloxScraper(root)
	root.mainloop()