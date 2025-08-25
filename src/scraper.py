import asyncio
import random
import re
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

import aiohttp


MessageCallback = Callable[[str], None]


@dataclass
class MemberInventory:
	user_id: int
	username: str
	display_name: str
	rap_total: Optional[int]
	inventory_private: bool
	has_limiteds: bool
	discord_username_guess: Optional[str]
	discord_links: List[str]


@dataclass
class ScrapeResult:
	members_processed: int
	errors: int
	group_discord_invite: Optional[str]
	members: List[MemberInventory]


class RobloxScraper:
	BASE_HEADERS = {
		"accept": "application/json",
		"accept-language": "en-US,en;q=0.9",
		"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
	}

	def __init__(self, message_cb: MessageCallback | None = None, *, max_concurrency: int = 2560) -> None:
		self.message_cb = message_cb or (lambda _msg: None)
		self.max_concurrency = max_concurrency
		self.semaphore = asyncio.Semaphore(self.max_concurrency)

	async def scrape_group(self, group_id: int) -> ScrapeResult:
		connector = aiohttp.TCPConnector(
			limit=0,  # No connection limit
			ssl=False,  # Disable SSL verification for speed
			limit_per_host=1000,  # Allow more connections per host
			keepalive_timeout=30,  # Keep connections alive longer
			enable_cleanup_closed=True  # Clean up closed connections
		)
		timeout = aiohttp.ClientTimeout(total=30, connect=10, sock_read=20)
		async with aiohttp.ClientSession(
			headers=self.BASE_HEADERS, 
			connector=connector, 
			trust_env=True,
			timeout=timeout
		) as session:
			group_discord = await self._get_group_discord_link(session, group_id)
			self._say(f"Group Discord link: {group_discord or 'Not found'}")

			self._say("Fetching group members...")
			members = await self._get_all_group_members(session, group_id)
			self._say(f"Found {len(members)} members. Starting per-user scraping...")

			results: List[MemberInventory] = []
			errors = 0

			async def handle(member: Dict[str, Any]) -> None:
				uid = int(member["user"]["userId"]) if isinstance(member.get("user"), dict) else int(member.get("userId"))
				try:
					info = await self._scrape_member(session, uid)
					results.append(info)
					self._say(self._format_member_line(info))
				except Exception as exc:  # noqa: BLE001
					nonlocal errors
					errors += 1
					self._say(f"Error processing user {uid}: {exc}")

			await self._bounded_gather([handle(m) for m in members])

			return ScrapeResult(
				members_processed=len(results),
				errors=errors,
				group_discord_invite=group_discord,
				members=results,
			)

	def _say(self, text: str) -> None:
		self.message_cb(text)

	async def _bounded_gather(self, coros: List[Awaitable[None]]) -> None:
		async def run(c: Awaitable[None]) -> None:
			async with self.semaphore:
				await c

		await asyncio.gather(*[run(c) for c in coros])

		async def _rbx_get(self, session: aiohttp.ClientSession, url: str, *, params: Dict[str, Any] | None = None) -> Any:
		for attempt in range(5):  # Reduced retries for speed
			try:
				async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
					if resp.status in (429, 500, 502, 503, 504):
						# Faster backoff for high performance mode
						backoff = min(1.5 ** attempt + random.random() * 0.5, 5.0)
						self._say(f"Backoff {resp.status} on {url}: sleeping {backoff:.2f}s")
						await asyncio.sleep(backoff)
						continue
					if resp.status == 403:
						raise PermissionError("Forbidden")
					resp.raise_for_status()
					return await resp.json()
			except PermissionError:
				raise
			except Exception as exc:  # noqa: BLE001
				if attempt == 4:
					raise RuntimeError(f"GET failed for {url}: {url}: {exc}")
				await asyncio.sleep(0.1 * (attempt + 1))  # Faster retry delays

	async def _get_group_discord_link(self, session: aiohttp.ClientSession, group_id: int) -> Optional[str]:
		try:
			url = f"https://groups.roblox.com/v1/groups/{group_id}/social-links"
			data = await self._rbx_get(session, url)
			links = data.get("data", []) if isinstance(data, dict) else []
			for link in links:
				label = (link.get("title") or "").lower()
				href = (link.get("url") or "").strip()
				if "discord" in label or "discord.gg" in href or "discord.com/invite" in href:
					return href
		except Exception:
			return None
		return None

	async def _get_all_group_members(self, session: aiohttp.ClientSession, group_id: int) -> List[Dict[str, Any]]:
		members: List[Dict[str, Any]] = []
		cursor: Optional[str] = None
		while True:
			params = {"limit": 100}
			if cursor:
				params["cursor"] = cursor
			url = f"https://groups.roblox.com/v1/groups/{group_id}/users"
			data = await self._rbx_get(session, url, params=params)
			items = data.get("data", []) if isinstance(data, dict) else []
			members.extend(items)
			cursor = data.get("nextPageCursor") if isinstance(data, dict) else None
			self._say(f"Fetched {len(members)} members...")
			if not cursor:
				break
		return members

	async def _scrape_member(self, session: aiohttp.ClientSession, user_id: int) -> MemberInventory:
		user = await self._get_user_profile(session, user_id)
		rap_total, inventory_private, has_limiteds = await self._get_user_collectibles(session, user_id)
		discord_guess, discord_links = self._find_discord_in_description(user.get("description") or "")
		return MemberInventory(
			user_id=user_id,
			username=user.get("name") or str(user_id),
			display_name=user.get("displayName") or user.get("name") or str(user_id),
			rap_total=rap_total,
			inventory_private=inventory_private,
			has_limiteds=has_limiteds,
			discord_username_guess=discord_guess,
			discord_links=discord_links,
		)

	async def _get_user_profile(self, session: aiohttp.ClientSession, user_id: int) -> Dict[str, Any]:
		url = f"https://users.roblox.com/v1/users/{user_id}"
		return await self._rbx_get(session, url)

	async def _get_user_collectibles(self, session: aiohttp.ClientSession, user_id: int) -> Tuple[Optional[int], bool, bool]:
		total_rap = 0
		has_any = False
		cursor: Optional[str] = None
		try:
			while True:
				params = {"limit": 100}
				if cursor:
					params["cursor"] = cursor
				url = f"https://inventory.roblox.com/v1/users/{user_id}/assets/collectibles"
				data = await self._rbx_get(session, url, params=params)
				items = data.get("data", []) if isinstance(data, dict) else []
				for it in items:
					has_any = True
					price = it.get("recentAveragePrice") or 0
					if isinstance(price, (int, float)):
						total_rap += int(price)
				cursor = data.get("nextPageCursor") if isinstance(data, dict) else None
				if not cursor:
					break
			return (total_rap if has_any else 0, False, has_any)
		except PermissionError:
			return (None, True, False)

	def _find_discord_in_description(self, text: str) -> Tuple[Optional[str], List[str]]:
		links: List[str] = []
		for m in re.finditer(r"https?://(?:www\.)?(?:discord\.gg|discord\.com/invite)/[\w-]+", text, flags=re.IGNORECASE):
			links.append(m.group(0))

		# Old discriminator style e.g., Name#1234 (Discord removed new discriminator sign-ups, but many remain)
		m1 = re.search(r"\b([A-Za-z0-9._]{2,32})#(\d{4})\b", text)
		if m1:
			return (m1.group(0), links)

		# New Discord username style: lowercase letters, numbers, underscore, dot, 2-32 chars
		m2 = re.search(r"\b[a-z0-9._]{2,32}\b", text)
		if m2 and "discord" in text.lower():
			return (m2.group(0), links)

		return (None, links)

	def _format_member_line(self, inv: MemberInventory) -> str:
		inv_part = (
			"Inventory private"
			if inv.inventory_private
			else ("No limiteds" if not inv.has_limiteds else f"RAP: {inv.rap_total}")
		)
		discord_part = (
			inv.discord_username_guess
			if inv.discord_username_guess
			else ("; ".join(inv.discord_links) if inv.discord_links else "No Discord user found")
		)
		return f"{inv.display_name} (@{inv.username}) [{inv.user_id}] -> {inv_part} | Discord: {discord_part}"