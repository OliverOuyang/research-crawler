#!/usr/bin/env python3
"""Staged Apify helper (stdlib only).
Usage:
  apify_stage.py whoami
  apify_stage.py find "<keywords>"               # search Store, show price/success/users
  apify_stage.py schema <user~actor>             # print input schema of default build
  apify_stage.py run <user~actor> <input.json> <out.json> --max-usd 0.5
  apify_stage.py check <out.json> --expect N --fields a,b,c [--text-field title] [--must "kw1|kw2"]
Token: env APIFY_TOKEN, or none if a proxy injects Authorization for api.apify.com.
"""
import json, os, re, sys, urllib.request, urllib.parse, collections, time

try:  # repo: read .env if present
    from _env import load_env; load_env()
except ImportError:
    pass

API = "https://api.apify.com/v2"

def req(path, data=None, timeout=330):
    h = {"Content-Type": "application/json"}
    if os.environ.get("APIFY_TOKEN"):
        h["Authorization"] = "Bearer " + os.environ["APIFY_TOKEN"]
    r = urllib.request.Request(API + path, data=json.dumps(data).encode() if data is not None else None,
                               headers=h, method="POST" if data is not None else "GET")
    with urllib.request.urlopen(r, timeout=timeout) as f:
        return json.loads(f.read() or b"null")

def whoami():
    me = req("/users/me")["data"]; lim = req("/users/me/limits")["data"]
    print("user:", me.get("username"), "| plan:", (me.get("plan") or {}).get("id"))
    print("monthly usage USD:", round(lim["current"].get("monthlyUsageUsd", 0), 3),
          "/ cap", lim["limits"].get("maxMonthlyUsageUsd"))

def find(q):
    items = req("/store?" + urllib.parse.urlencode({"search": q, "limit": 10, "sortBy": "popularity"}))["data"]["items"]
    for a in items:
        s = a.get("stats") or {}; p = a.get("currentPricingInfo") or {}
        runs = s.get("publicActorRunStats30Days") or {}
        tot = runs.get("TOTAL") or 0; ok = runs.get("SUCCEEDED") or 0
        print(f'{a["username"]}~{a["name"]:<40} users={s.get("totalUsers")} '
              f'rating={a.get("actorReviewRating")} success30d={(ok/tot*100 if tot else 0):.1f}% '
              f'pricing={p.get("pricingModel")} modified={str(a.get("modifiedAt"))[:10]}')

def schema(actor):
    d = req(f"/acts/{actor}/builds/default")["data"]
    s = d.get("inputSchema") or (d.get("actorDefinition") or {}).get("input") or {}
    if isinstance(s, str): s = json.loads(s)
    for k, v in s.get("properties", {}).items():
        print(f'{k:<32} {v.get("type"):<8} default={str(v.get("default", v.get("prefill", "")))[:50]} '
              f'{("enum=" + str(v["enum"])[:70]) if "enum" in v else ""}')

def run(actor, inp, out, max_usd):
    t = time.time()
    data = req(f"/acts/{actor}/run-sync-get-dataset-items?timeout=300&maxTotalChargeUsd={max_usd}",
               json.load(open(inp)))
    json.dump(data, open(out, "w"), ensure_ascii=False, indent=1)
    print(f"{actor}: {len(data)} items in {time.time()-t:.0f}s -> {out}")

def check(out, expect, fields, text_field=None, must=None):
    d = json.load(open(out)); n = len(d)
    print(f"items={n} expected={expect} -> {'OK' if n >= 0.9*expect else 'PARTIAL (<90%)'}")
    for f in fields:
        miss = sum(1 for x in d if x.get(f) in (None, "", []))
        print(f"  field {f:<22} missing {miss}/{n}")
    ids = [x.get("id") or x.get("cid") for x in d]
    print("  duplicate ids:", n - len(set(ids)))
    if text_field:
        txt = [str(x.get(text_field) or "") for x in d]
        print("  deleted/removed:", sum(t in ("[deleted]", "[removed]") for t in txt))
        print("  with links:", sum("http" in t for t in txt))
        if must:
            rel = sum(bool(re.search(must, t, re.I)) for t in txt)
            print(f"  relevance (matches /{must}/): {rel}/{n} = {rel/max(n,1):.0%}")
    if d: print("  sample keys:", sorted(d[0].keys())[:25])

if __name__ == "__main__":
    a = sys.argv[1:]
    opt = lambda k, dflt=None: a[a.index(k)+1] if k in a else dflt
    if a[0] == "whoami": whoami()
    elif a[0] == "find": find(a[1])
    elif a[0] == "schema": schema(a[1])
    elif a[0] == "run": run(a[1], a[2], a[3], opt("--max-usd", "0.5"))
    elif a[0] == "check":
        check(a[1], int(opt("--expect", "0")), [f for f in opt("--fields", "").split(",") if f],
              opt("--text-field"), opt("--must"))
