#!/usr/bin/env python3
import json, os
from datetime import datetime, timezone
import requests

TS_TOKEN = os.environ["TS_API_TOKEN"]
TG_TOKEN = os.environ["TG_BOT_TOKEN"]
TG_CHAT  = os.environ["TG_CHAT_ID"]

WATCH = {"srv-1", "srv-2"}   # exact hostnames from step 0
OFFLINE_AFTER = 360          # fallback only if connectedToControl absent
STATE = "state.json"

def tg(msg):
    requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                  json={"chat_id": TG_CHAT, "text": msg}, timeout=10)

r = requests.get("https://api.tailscale.com/api/v2/tailnet/-/devices",
                 headers={"Authorization": f"Bearer {TS_TOKEN}"}, timeout=15)
r.raise_for_status()
now = datetime.now(timezone.utc)

def is_down(d):
    if "connectedToControl" in d:
        return not d["connectedToControl"]
    last = d.get("lastSeen")
    if not last:
        return True
    last = datetime.fromisoformat(last.replace("Z", "+00:00"))
    return (now - last).total_seconds() > OFFLINE_AFTER

down_now, seen = set(), {}
for d in r.json()["devices"]:
    h = d["hostname"]
    if WATCH and h not in WATCH:
        continue
    seen[h] = d.get("lastSeen", "?")
    if is_down(d):
        down_now.add(h)

try:
    down_before = set(json.load(open(STATE))["down"])
except (FileNotFoundError, json.JSONDecodeError, KeyError):
    down_before = set()

for h in sorted(down_now - down_before):
    tg(f"🔴 {h} DOWN — last seen {seen[h]}")
for h in sorted(down_before - down_now):
    tg(f"✅ {h} back online")

if down_now != down_before:
    json.dump({"down": sorted(down_now)}, open(STATE, "w"))
