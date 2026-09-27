import asyncio
import json
import math
import os
import signal
import ssl
import sys
import time
import urllib.parse

import aiohttp

from utils.banner import show_banner

MY_PROJECT = "Gold Rush Miniapp"
BASE_URL = "https://goldrush-api.king7star.workers.dev"
REF_CODE = "6004380466"

RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"


def log_green(msg):
    print(f"{GREEN}{BOLD}{msg}{RESET}", flush=True)


def log_yellow(msg):
    print(f"{YELLOW}{BOLD}{msg}{RESET}", flush=True)


def log_red(msg):
    print(f"{RED}{BOLD}{msg}{RESET}", flush=True)


def signal_handler(sig, frame):
    print()
    log_red("Script stopped by user")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def clean_text(value, fallback):
    text = str(value)
    for symbol in "[]|#!@$%^&*()":
        text = text.replace(symbol, " ")
    text = " ".join(text.split())
    return text if text else str(fallback)


def shorten(value, fallback, limit):
    text = clean_text(value, fallback)
    if len(text) <= limit:
        return text
    cut = text[: limit + 1]
    space = cut.rfind(" ")
    return cut[:space].rstrip() if space > 0 else text[:limit].rstrip()


def number_of(value, fallback):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(fallback)


def format_duration(total):
    total = max(0, int(total))
    return f"{total // 3600:02d}:{(total % 3600) // 60:02d}:{total % 60:02d}"


def draw_frame(label, remaining, width):
    frame = f"{label} {format_duration(remaining)}"
    sys.stdout.write(f"\r{YELLOW}{BOLD}{frame}{RESET}")
    sys.stdout.flush()
    return max(width, len(frame))


def clear_frame(width):
    if width:
        sys.stdout.write("\r" + " " * width + "\r")
        sys.stdout.flush()


def countdown(seconds, label):
    deadline = time.monotonic() + max(0.0, float(seconds))
    width = 0
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        width = draw_frame(label, math.ceil(remaining), width)
        time.sleep(min(1.0, remaining))
    clear_frame(width)


def mask_proxy(proxy_url):
    try:
        value = proxy_url.split("://")[-1]
        after_at = value.split("@")[-1]
        host_part = after_at.split(":")[0]
        port_part = after_at.split(":")[1] if ":" in after_at else ""
        octets = host_part.split(".")
        if len(octets) == 4:
            masked_host = f"{octets[0]}*****{octets[3]}"
        elif len(host_part) > 4:
            masked_host = f"{host_part[:2]}*****{host_part[-2:]}"
        else:
            masked_host = "***"
        suffix = f":{port_part}" if port_part else ""
        return f"http://user:pass@{masked_host}{suffix}"
    except Exception:
        return "http://user:pass@***:***"


def normalize_proxy(raw):
    line = raw.strip()
    if not line:
        return None
    if "://" in line:
        return line
    parts = line.split(":")
    if len(parts) == 2:
        return f"http://{parts[0]}:{parts[1]}"
    if len(parts) == 4:
        return f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
    return None


def load_config():
    if not os.path.isfile("config.json"):
        with open("config.json", "w", encoding="utf-8") as handle:
            json.dump({"settings": {"sleep_seconds": 3600}}, handle, indent=2)
            handle.write("\n")
    try:
        with open("config.json", encoding="utf-8") as handle:
            data = json.load(handle)
        return int(data.get("settings", {}).get("sleep_seconds", 3600))
    except Exception:
        return 3600


def load_accounts():
    if not os.path.isfile("data.txt"):
        return []
    with open("data.txt", encoding="utf-8") as handle:
        lines = handle.read().splitlines()
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]


def load_proxies():
    if not os.path.isfile("proxy.txt"):
        return []
    with open("proxy.txt", encoding="utf-8") as handle:
        lines = handle.read().splitlines()
    proxies = []
    for line in lines:
        normalized = normalize_proxy(line)
        if normalized:
            proxies.append(normalized)
    return proxies


def init_param(init_data, name):
    try:
        for chunk in init_data.split("&"):
            if chunk.startswith(name + "="):
                return urllib.parse.unquote(chunk[len(name) + 1:])
    except Exception:
        return ""
    return ""


def telegram_user(init_data):
    raw = init_param(init_data, "user")
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def telegram_id_of(init_data):
    return int(number_of(telegram_user(init_data).get("id"), 0))


def start_param_of(init_data):
    return init_param(init_data, "start_param")


def account_label(init_data):
    user = telegram_user(init_data)
    name = user.get("username") or user.get("first_name") or "Unknown"
    return shorten(name, "Unknown", 24)


def today_stamp():
    return time.strftime("%Y-%m-%d", time.gmtime())


class RateLimited(Exception):
    pass


class GoldRushAccount:
    def __init__(self, init_data, proxy_url):
        self.init_data = init_data
        self.proxy_url = proxy_url
        self.telegram_id = telegram_id_of(init_data)
        self.profile_user = telegram_user(init_data)
        self.referrer = start_param_of(init_data)
        self.session = None
        self.connector = None
        self.last_write = 0.0

    def headers(self):
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "Authorization": f"tma {self.init_data}",
            "x-telegram-init-data": self.init_data,
            "x-device-id": f"grdevice{self.telegram_id}",
            "Origin": "https://goldrush-4kwg.onrender.com",
            "Referer": "https://goldrush-4kwg.onrender.com/",
            "User-Agent": ("Mozilla/5.0 (Linux; Android 13; SM-S901B) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36 "
                           "Telegram-Android/12.0.1"),
        }

    def payload(self, **extra):
        data = {
            "telegram_id": self.telegram_id,
            "username": self.profile_user.get("username"),
            "first_name": self.profile_user.get("first_name"),
            "photo_url": self.profile_user.get("photo_url"),
            "referrer_id": int(number_of(self.referrer, 0)) or int(number_of(REF_CODE, 0)) or None,
            "language_code": self.profile_user.get("language_code"),
        }
        data.update(extra)
        return data

    async def open(self):
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        self.connector = aiohttp.TCPConnector(ssl=context)
        self.session = aiohttp.ClientSession(connector=self.connector, headers=self.headers())

    async def close(self):
        if self.session is not None:
            await self.session.close()
        if self.connector is not None:
            await self.connector.close()

    async def pace(self):
        gap = 1.5 - (time.monotonic() - self.last_write)
        if gap > 0:
            await asyncio.sleep(gap)
        self.last_write = time.monotonic()

    async def request(self, method, path, payload=None):
        url = f"{BASE_URL}{path}"
        last_error = None
        throttled = False
        if method == "POST":
            await self.pace()
        for attempt in range(4):
            try:
                async with self.session.request(method, url, json=payload,
                                                proxy=self.proxy_url, timeout=45) as response:
                    body = await response.text()
                    if response.status == 429:
                        throttled = True
                        countdown(62, "Waiting out the server rate limit")
                        continue
                    if response.status == 401 or response.status == 403:
                        return response.status, {"error": "unauthorized"}
                    text = body.strip()
                    if not text:
                        return response.status, {}
                    try:
                        return response.status, json.loads(text)
                    except json.JSONDecodeError:
                        return response.status, {"_raw": text[:200]}
            except Exception as exc:
                last_error = exc
                countdown(2 * (attempt + 1), "Waiting before retrying the request")
        if throttled:
            raise RateLimited("rate limited")
        raise last_error if last_error else RuntimeError("request failed")

    async def get(self, path):
        return await self.request("GET", path)

    async def post(self, path, payload=None):
        return await self.request("POST", path, payload or {})

    async def sync(self):
        status, payload = await self.post("/api/user/sync", self.payload())
        return payload if status == 200 else {}

    def balance_of(self, profile):
        return number_of((profile.get("user") or {}).get("gold_balance"), 0)


async def run_streak(account, profile):
    streak = profile.get("streak") or {}
    if streak.get("last_checkin_date") == today_stamp():
        return "done", 0, int(number_of(streak.get("streak_day"), 0))
    day = int(number_of(streak.get("streak_day"), 0)) + 1
    code, body = await account.post("/api/daily-streak",
                                    {"telegram_id": account.telegram_id,
                                     "streak_day": day, "reward": 0})
    if code == 200 and body.get("success"):
        reward = int(number_of(body.get("reward"), 0))
        server_day = int(number_of(body.get("streak_day"), day))
        return "credited", reward, server_day
    detail = body.get("error") or body.get("message") or ""
    return "refused", 0, detail


async def run_spin(account, profile):
    spin = profile.get("spin") or {}
    left = int(number_of(spin.get("free_spins_left"), 0))
    credited = 0
    while left > 0:
        code, body = await account.post("/api/spin",
                                       {"telegram_id": account.telegram_id, "spin_type": "free"})
        if code != 200 or not body.get("success"):
            break
        left = int(number_of(body.get("free_spins_left"), left - 1))
        reward = int(number_of(body.get("reward"), 0))
        credited += reward
        prize = shorten(body.get("prize") or body.get("label") or "no prize", "no prize", 22)
        log_green(f"Wheel spin paid {clean_text(reward, 0)} GOLD with {clean_text(prize, 'a prize')}")
    return credited


async def run_ads(account, profile):
    config = profile.get("ad_config") or {}
    names = [str(key) for key, value in config.items()
             if isinstance(value, dict) and value.get("isEnabled")]
    if not names:
        return 0, 0, "empty"
    claimed = profile.get("milestone_claims") or []
    ceiling = (50, 150, 250)[-1]
    watched = int(number_of((profile.get("ads") or {}).get("watched_today"), 0))
    if len([box for box in (1, 2, 3) if box in claimed]) >= 3:
        return 0, 0, "done"
    credited = 0
    added = 0
    empty = 0
    while watched < ceiling and empty < 2:
        items = [{"network_id": names[index % len(names)], "duration_sec": 5,
                  "watched_at": int(time.time() * 1000) - 6000} for index in range(15)]
        code, body = await account.post("/api/ads/batch-watch",
                                        {"telegram_id": account.telegram_id, "items": items})
        if code != 200 or not body.get("success"):
            break
        processed = int(number_of(body.get("processed_count"), 0))
        reward = int(number_of(body.get("total_reward"), 0))
        if processed <= 0:
            empty += 1
            continue
        empty = 0
        watched += processed
        added += processed
        credited += reward
        log_green(f"Batch credited {clean_text(reward, 0)} GOLD for "
                  f"{clean_text(processed, 0)} watched ads")
    return credited, added, "ladder"


async def run_milestones(account, profile):
    claimed = profile.get("milestone_claims") or []
    credited = 0
    opened = 0
    for milestone in (1, 2, 3):
        if milestone in claimed:
            continue
        code, body = await account.post("/api/ads/milestone-claim",
                                       {"telegram_id": account.telegram_id,
                                        "milestone_id": milestone, "reward_amount": 0})
        if code != 200 or not body.get("success"):
            break
        reward = int(number_of(body.get("reward"), 0))
        credited += reward
        opened += 1
        log_green(f"Reward box {clean_text(milestone, 1)} opened and paid "
                  f"{clean_text(reward, 0)} GOLD")
    return credited, opened


async def run_mining(account, profile):
    mining = profile.get("mining") or {}
    watched = int(number_of(mining.get("ads_watched_today"), 0))
    while watched < 3:
        code, body = await account.post("/api/mining/ad", {"telegram_id": account.telegram_id})
        if code != 200 or not body.get("success"):
            break
        watched = int(number_of(body.get("ads_watched"), watched))
        countdown(6, "Waiting before the next sponsor ad")
    if watched < 3:
        return "short", 0, watched
    code, body = await account.post("/api/mining/start", {"telegram_id": account.telegram_id})
    if code != 200 or body.get("success") is False:
        return "refused", 0, watched
    code, body = await account.post("/api/mining/claim",
                                   {"telegram_id": account.telegram_id, "accumulated_gold": 0})
    if code == 200 and body.get("success"):
        reward = int(number_of(body.get("reward"), 0))
        return "claimed", reward, watched
    remaining = int(number_of(body.get("remaining_seconds"), 0))
    if remaining > 0:
        return "waiting", remaining, watched
    return "refused", 0, watched


async def run_tasks(account, profile):
    credited = 0
    refused = 0
    for entry in profile.get("tasks") or []:
        if not isinstance(entry, dict):
            continue
        task_id = entry.get("id")
        if task_id is None or entry.get("userStatus") == "done":
            continue
        name = shorten(entry.get("title"), clean_text(task_id, "task"), 26)
        code, body = await account.post("/api/tasks/complete",
                                       {"telegram_id": account.telegram_id, "task_id": task_id})
        if code == 200 and body.get("success"):
            reward = int(number_of(body.get("reward"), 0))
            credited += 1
            log_green(f"Task {clean_text(name, 'task')} paid {clean_text(reward, 0)} GOLD")
        else:
            refused += 1
            log_yellow(f"Task {clean_text(name, 'task')} was refused by the server")
    return credited, refused


async def run_account(init_data, proxy_url):
    account = GoldRushAccount(init_data, proxy_url)
    await account.open()
    try:
        profile = await account.sync()
        if not profile or profile.get("success") is False:
            log_red("Account data was not returned by the server")
            return None
        if (profile.get("user") or {}).get("is_banned"):
            log_red("This account is marked as restricted by the server")
            return None
        start_balance = account.balance_of(profile)
        if proxy_url is not None:
            log_yellow(f"Using proxy {mask_proxy(proxy_url)}")
        log_green(f"Account {clean_text(account_label(account.init_data), 'Unknown')} started with "
                  f"{clean_text(int(start_balance), 0)} GOLD")
        outcome, streak_reward, detail = await run_streak(account, profile)
        if outcome == "credited":
            log_green(f"Daily check in completed on day {clean_text(detail, 1)} and "
                      f"{clean_text(streak_reward, 0)} GOLD was credited")
        elif outcome == "refused":
            log_yellow(f"Daily check in was refused by the server with "
                       f"{clean_text(shorten(detail, 'no reason given', 34), 'no reason given')}")
        else:
            log_green("Daily check in was already completed for this account")
        spin_reward = await run_spin(account, profile)
        if spin_reward > 0:
            log_green(f"Free wheel spins credited {clean_text(spin_reward, 0)} GOLD in total")
        else:
            log_green("Every free wheel spin was already used for this account")
        ad_reward, ads_watched, ad_state = await run_ads(account, profile)
        if ads_watched > 0:
            log_green(f"{clean_text(ads_watched, 0)} ads were watched and "
                      f"{clean_text(ad_reward, 0)} GOLD was credited")
        elif ad_state == "done":
            log_green("Every ad milestone was already opened for this account")
        else:
            log_yellow("No ad reward could be credited from the server on this run")
        box_reward, boxes = await run_milestones(account, profile)
        if boxes > 0:
            log_green(f"{clean_text(boxes, 0)} reward boxes paid {clean_text(box_reward, 0)} GOLD")
        else:
            log_green("Every reward box was already opened for this account")
        mining_state, mining_value, mining_ads = await run_mining(account, profile)
        if mining_state == "claimed":
            log_green(f"Mining session was claimed and paid {clean_text(mining_value, 0)} GOLD")
        elif mining_state == "waiting":
            log_yellow(f"Mining session is still running for "
                       f"{clean_text(format_duration(mining_value), '00:00:00')}")
        elif mining_state == "short":
            log_yellow(f"Mining sponsor ads reached {clean_text(mining_ads, 0)} of 3 for this account")
        else:
            log_yellow("Mining session could not be started by the server on this run")
        credited, refused = await run_tasks(account, profile)
        if credited > 0:
            log_green(f"{clean_text(credited, 0)} account tasks were completed and rewarded")
        elif refused > 0:
            log_yellow(f"{clean_text(refused, 0)} account tasks were refused by the server on this run")
        else:
            log_green("Every available account task was already completed")
        end_profile = await account.sync()
        end_balance = account.balance_of(end_profile or profile)
        gained = end_balance - start_balance
        if gained > 0:
            log_green(f"Cycle closed with a balance of {clean_text(int(end_balance), 0)} GOLD")
        else:
            log_yellow(f"Cycle closed with a balance of {clean_text(int(end_balance), 0)} GOLD "
                       f"and no change")
        return end_balance
    finally:
        await account.close()


async def main():
    show_banner(MY_PROJECT)
    sleep_seconds = load_config()
    accounts = load_accounts()
    proxies = load_proxies()
    if not accounts:
        log_red("No account was found in data.txt")
        sys.exit(1)
    cycle = 0
    while True:
        cycle += 1
        log_yellow(f"Starting automation cycle number {clean_text(cycle, 0)}")
        for index, init_data in enumerate(accounts):
            if index > 0:
                print()
            proxy_url = proxies[index % len(proxies)] if proxies else None
            try:
                await run_account(init_data, proxy_url)
            except RateLimited:
                log_yellow("The server rate limit was reached for this account")
            except Exception as exc:
                log_red(f"Request to the server failed with {clean_text(type(exc).__name__, 'error')}")
        countdown(sleep_seconds, "Next cycle starts in")
        print()
        show_banner(MY_PROJECT)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        signal_handler(None, None)
