<div align="center">

<img width="100%" alt="header" src="https://capsule-render.vercel.app/api?type=waving&height=210&text=GoldRush%20Bot&fontAlign=50&fontAlignY=36&fontSize=56&desc=Auto%20Daily%20Check%20In%20%7C%20Auto%20Wheel%20Spin%20%7C%20Auto%20Ad%20Rewards%20%7C%20Auto%20Reward%20Boxes%20%7C%20Auto%20Cloud%20Mining&descAlign=50&descAlignY=58"/>

<img alt="typing" src="https://readme-typing-svg.demolab.com?font=Inter&size=18&duration=3000&pause=650&center=true&vCenter=true&width=900&lines=Auto+Daily+Check+In+%7C+Server+Paid+Streak;Auto+Wheel+Spin+%7C+Every+Free+Spin+Played;Auto+Ad+Rewards+%7C+Batched+Until+The+Server+Stops;Auto+Reward+Boxes+%7C+Opened+In+Order;Auto+Cloud+Mining+%7C+Sponsor+Ads+Then+Claim;Multi-Account+%7C+Proxy+Per+Account+%7C+Live+Countdown"/>

<p>
  <img alt="python" src="https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white"/>
  <img alt="platform" src="https://img.shields.io/badge/Platform-GoldRush%20Miniapp-111111"/>
  <img alt="multi-account" src="https://img.shields.io/badge/Multi--Account-Supported-111111"/>
  <img alt="proxy" src="https://img.shields.io/badge/Proxy-Supported-111111"/>
  <img alt="author" src="https://img.shields.io/badge/by-Yuurisandesu-111111"/>
</p>

<p>
  <b>GoldRush Bot</b> is a full automation bot for the GoldRush Telegram Miniapp.<br/>
  It handles the complete daily cycle: claiming the daily check in, playing every free wheel spin, draining the rewarded ad slots in server sized batches, opening price box milestones the server has already cleared, working the cloud mining sponsor ads into a session and settling its reward, collecting every account task the server reports as claimable, all running automatically across multiple accounts with proxy support per account and a live countdown between cycles.<br/>
  Built and distributed by <b>Yuurisandesu</b>.
</p>

</div>

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Bot](#running-the-bot)
- [Features](#features)
- [File Structure](#file-structure)
- [Disclaimer](#disclaimer)

---

## Requirements

- Python `3.12+`
- Git

---

## Installation

**Clone the repository:**

```bash
git clone https://github.com/Yuurisan-N1/Goldrush-Miniapp.git
cd Goldrush-Miniapp
```

**Install dependencies:**

```bash
pip install aiohttp yuurisan
```

---

## Configuration

### 1. Accounts (data.txt)

Fill `data.txt` with Telegram WebApp `initData` for each account, one per line:

```
user=%7B%22id%22...&hash=abc123
user=%7B%22id%22...&hash=def456
```

> `initData` can be obtained from the browser DevTools when opening GoldRush on Telegram Web.

### 2. Proxy (proxy.txt)

Fill `proxy.txt` with proxies, one per line (optional, leave empty to run without proxy):

```
host:port
host:port:user:pass
http://user:pass@host:port
```

Proxies are assigned to accounts by index in round-robin order.

### 3. Bot Settings (config.json)

`sleep_seconds` controls how many seconds the bot waits between cycles. If `config.json` is missing, it is created automatically with a default of `3600` seconds.

---

## Running the Bot

```bash
python bot.py
```

Press `Ctrl+C` at any time to stop the bot cleanly.

---

## Features

### Auto Daily Check In
The bot reads the check in date and the streak day the account already carries, then claims today's check in once. The reward the server actually paid is read from that same reply and logged together with the streak day the server assigned, so a day the account already claimed is reported as done instead of retried.

### Auto Wheel Spin
Every free wheel spin the account still holds is played one by one. Each spin logs the server's own prize label and the gold it credited, and the loop ends when the server reports no free spins left.

### Auto Ad Rewards
The bot reads the rewarded ad slots the server enables along with their slots and rewards, then drains them in server sized batches. Every batch logs the gold the server credited in that reply and the number of ads it accepted, and the phase ends when the server stops paying.

### Auto Reward Boxes
The price boxes are opened in order for the milestones the account has not opened yet. The server picks the payout, and every opened box logs the amount it credited together with the box number.

### Auto Cloud Mining
The bot works the sponsor ads the mining session requires, waits out the server cooldown between them, then opens the session. A claim that is not ready yet is reported with the time the server says is left, and a claim that lands logs the gold the server credited.

### Auto Account Tasks
The task list is read from the server and every entry that is not marked done is settled. Each task logs its own name and reward, and a task the server refuses is counted and reported instead of retried blindly.

### Multi Account
All accounts in `data.txt` are processed sequentially within every cycle. The account identifier, the starting balance and the referral parameter are logged at the start of each account, a blank line separates each account's output, and the cycle closes with the balance movement for that account. The cycle number is tracked and logged at the start of each round.

### Proxy Support
Proxies are loaded from `proxy.txt` and assigned to accounts by position in round-robin order. Proxy credentials are masked in log output. Running without proxies is fully supported.

### Auto Countdown
After all accounts complete a cycle, the bot displays a live `HH:MM:SS` countdown until the next cycle starts.

---

## File Structure

```text
GoldRush-Miniapp/
├── bot.py          # Main bot, full daily cycle automation
├── config.json     # Sleep duration between cycles
├── data.txt        # Account initData, one per line
├── proxy.txt       # Proxy list, one per line (optional)
├── LICENSE         # License file
└── utils/
    └── banner.py   # Banner using yuurisan module
```

---

## Disclaimer

This tool is built for educational and technical exploration purposes. Use it wisely and at your own responsibility.

---

<div align="center">
<img width="100%" alt="footer" src="https://capsule-render.vercel.app/api?type=waving&height=120&section=footer"/>
</div>