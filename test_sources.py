#!/usr/bin/env python3
"""
test_sources.py — הרץ על המחשב המקומי שלך לפני הפריסה על Render.
בודק כל מקור נתונים ומדפיס ✅ / ❌
"""
import sys, time, re, json

def check_pkg(name):
    try:
        __import__(name)
        return True
    except ImportError:
        print(f"  חסרה חבילה: {name}  → pip install {name}")
        return False

print("=" * 60)
print("בדיקת חבילות Python")
print("=" * 60)
for pkg in ["requests", "feedparser", "cloudscraper", "pytrends"]:
    ok = check_pkg(pkg)
    print(f"{'✅' if ok else '❌'}  {pkg}")

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
}

KEYWORDS = ["סקר", "בחירות", "מנדטים", "אחוזים", "ליכוד", "יש עתיד"]

# ─── RSS ────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("עדיפות 1 — RSS Feeds")
print("=" * 60)

RSS_SOURCES = {
    "ynet":   "https://www.ynet.co.il/Integration/StoryRss2.xml",
    "maariv": "https://www.maariv.co.il/Rss/RssFeedsMivzakiChadashot",
    "walla":  "https://rss.walla.co.il/feed/1",
    "n12":    "https://www.n12.co.il/rss",
}
try:
    import feedparser
    for name, url in RSS_SOURCES.items():
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            feed = feedparser.parse(r.text)
            political = [e.title for e in feed.entries
                         if any(k in e.get("title", "") for k in KEYWORDS)]
            print(f"✅ {name}: {len(feed.entries)} כתבות, {len(political)} פוליטיות")
            if political:
                print(f"   דוגמה: {political[0][:70]}")
        except Exception as e:
            print(f"❌ {name}: {e}")
        time.sleep(1)
except ImportError:
    print("feedparser לא מותקן — דלג")

# ─── Scraping ────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("עדיפות 2 — Scraping עמודי חדשות")
print("=" * 60)

SCRAPE = {
    "ynet_politics":   "https://www.ynet.co.il/news/politics",
    "maariv_politics": "https://www.maariv.co.il/politics",
    "walla_politics":  "https://news.walla.co.il/politics",
    "n12_politics":    "https://www.n12.co.il/politics",
}
for name, url in SCRAPE.items():
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            hits = sum(1 for k in KEYWORDS if k in r.text)
            print(f"✅ {name}: HTTP 200, {hits} מילות מפתח")
        elif r.status_code == 403:
            # נסה cloudscraper
            try:
                import cloudscraper
                cs = cloudscraper.create_scraper()
                r2 = cs.get(url, timeout=10)
                hits = sum(1 for k in KEYWORDS if k in r2.text)
                print(f"✅ {name}: cloudscraper הצליח ({r2.status_code}), {hits} מילות מפתח")
            except Exception as e2:
                print(f"❌ {name}: 403 + cloudscraper נכשל: {e2}")
        else:
            print(f"❌ {name}: HTTP {r.status_code}")
    except Exception as e:
        print(f"❌ {name}: {e}")
    time.sleep(1)

# ─── Google Trends ───────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("עדיפות 3א — Google Trends (pytrends)")
print("=" * 60)
try:
    from pytrends.request import TrendReq
    pt = TrendReq(hl="he-IL", tz=120)
    kw = ["ליכוד", "יש עתיד", "מחנה המדינה", "ישראל ביתנו"]
    pt.build_payload(kw[:4], cat=16, timeframe="now 7-d", geo="IL")
    time.sleep(2)
    df = pt.interest_over_time()
    if not df.empty:
        latest = df.iloc[-1][kw[:4]].to_dict()
        print(f"✅ google_trends: נתונים התקבלו")
        for k, v in latest.items():
            print(f"   {k}: {v}")
    else:
        print("⚠️  google_trends: תגובה ריקה")
except Exception as e:
    print(f"❌ google_trends: {e}")

time.sleep(2)

# ─── Polymarket ──────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("עדיפות 3ב — Polymarket API")
print("=" * 60)
try:
    r = requests.get(
        "https://gamma-api.polymarket.com/markets?q=israel+election",
        timeout=10,
    )
    if r.status_code == 200:
        data = r.json()
        print(f"✅ polymarket: {len(data)} שווקים")
        for m in data[:3]:
            print(f"   • {m.get('question','?')[:70]}")
    else:
        print(f"❌ polymarket: HTTP {r.status_code}")
except Exception as e:
    print(f"❌ polymarket: {e}")

# ─── Knesset Open Data ───────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("עדיפות 3ג — Knesset Open Data")
print("=" * 60)
try:
    r = requests.get(
        "https://knesset.gov.il/Odata/ParliamentInfo.svc/KNS_Party?$format=json",
        timeout=10,
    )
    if r.status_code == 200:
        parties = r.json().get("value", [])
        print(f"✅ knesset_odata: {len(parties)} מפלגות")
        for p in parties[:5]:
            print(f"   • {p.get('Name','?')}")
    else:
        print(f"❌ knesset_odata: HTTP {r.status_code}")
except Exception as e:
    print(f"❌ knesset_odata: {e}")

print("\n" + "=" * 60)
print("סיום בדיקה")
print("=" * 60)
