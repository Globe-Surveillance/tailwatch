#!/usr/bin/env python3
import json, os
from datetime import datetime, timezone
import requests

TS_TOKEN = os.environ["TS_API_TOKEN"]
TG_TOKEN = os.environ["TG_BOT_TOKEN"]
TG_CHAT  = os.environ["TG_CHAT_ID"]

WATCH = {"glb2026", "srv-backstage", "srv-bml", "srv-laayoune", "sysnology-nas"}
OFFLINE_AFTER = 360      # fallback only if connectedToControl is absent
STATE = "state.json"

def tg(msg):
    resp = requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                         json={"chat_id": TG_CHAT, "text": msg}, timeout=10)
    resp.raise_for_status()

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
    key = d["name"].split(".")[0].lower()
    if WATCH and key not in WATCH:
        continue
    seen[key] = d.get("lastSeen", "?")
    if is_down(d):
        down_now.add(key)

try:
    down_before = set(json.load(open(STATE))["down"])
except (FileNotFoundError, json.JSONDecodeError, KeyError):
    down_before = set()

for k in sorted(down_now - down_before):
    tg(f"🔴 {k} DOWN — last seen {seen[k]}")
for k in sorted(down_before - down_now):
    tg(f"✅ {k} back online")

if down_now != down_before:
    json.dump({"down": sorted(down_now)}, open(STATE, "w"))
