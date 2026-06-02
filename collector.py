#!/usr/bin/env python3
"""
collector.py — אוסף נתוני סקרים ממומנטום מבחירות 2026
מריץ כל 6 שעות ושומר תוצאה ב-data.json
"""
import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

DATA_FILE = Path(__file__).parent / "data.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
}

# מפלגות ומילות מפתח לזיהוי בטקסט
PARTIES = {
    "ליכוד":            ["ליכוד"],
    "יש עתיד":          ["יש עתיד"],
    "מחנה המדינה":      ["מחנה המדינה", "מחנה דמוקרטי"],
    "ישראל ביתנו":      ["ישראל ביתנו", "ביתנו"],
    'ש"ס':              ['ש"ס', "שס"],
    "יהדות התורה":      ["יהדות התורה", "אגודת ישראל", "דגל התורה"],
    "הציונות הדתית":    ["הציונות הדתית", "עוצמה יהודית", "סמוטריץ"],
    "עבודה":            ["עבודה"],
    "מרצ":              ["מרצ"],
    'רע"מ':             ['רע"מ', "רעם"],
    'חד"ש-תע"ל':       ['חד"ש', "תעל", "חדש תעל"],
}

THRESHOLD = 3.25  # מחסום בחירות (% מהקולות)
TOTAL_SEATS = 120


# ─── Fallback wrapper ────────────────────────────────────────────────────────

def fetch_with_fallback(source_name, fetch_func, weight):
    try:
        result = fetch_func()
        log.info("✅ %s — הצליח (משקל %.0f%%)", source_name, weight * 100)
        return result, weight
    except Exception as exc:
        log.warning("❌ %s — נכשל: %s", source_name, exc)
        return None, 0


# ─── עזר: חילוץ מנדטים מטקסט עברי ──────────────────────────────────────────

def extract_mandates_from_text(text: str) -> dict[str, float]:
    """חולץ מנדטים לפי דפוסי "ליכוד - 28" / "28 מנדטים לליכוד" וכד'."""
    found = {}
    for party, keywords in PARTIES.items():
        for kw in keywords:
            # דפוס: "ליכוד X" / "ליכוד - X" / "X לליכוד" / "X מנדטים ליכוד"
            patterns = [
                rf"{re.escape(kw)}\s*[:\-–|]?\s*(\d{{1,2}})",
                rf"(\d{{1,2}})\s*(?:מנדטים?)?\s*ל{re.escape(kw)}",
            ]
            for pat in patterns:
                m = re.search(pat, text)
                if m:
                    val = int(m.group(1) if m.lastindex == 1 else m.group(1))
                    # sanity: between 3 and 50 seats
                    if 3 <= val <= 50:
                        found[party] = val
                        break
            if party in found:
                break
    return found


# ─── מקור 1: RSS Feeds ──────────────────────────────────────────────────────

def fetch_rss() -> dict[str, float]:
    try:
        import feedparser
    except ImportError:
        raise RuntimeError("feedparser לא מותקן")

    rss_urls = [
        "https://www.ynet.co.il/Integration/StoryRss2.xml",
        "https://www.maariv.co.il/Rss/RssFeedsMivzakiChadashot",
        "https://rss.walla.co.il/feed/1",
        "https://www.n12.co.il/rss",
    ]
    poll_keywords = ["סקר", "מנדטים", "בחירות", "אחוזים"]
    all_mandates: dict[str, list[float]] = {}

    for url in rss_urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=12)
            feed = feedparser.parse(r.text)
            for entry in feed.entries:
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                combined = title + " " + summary
                if not any(k in combined for k in poll_keywords):
                    continue
                mandates = extract_mandates_from_text(combined)
                for party, val in mandates.items():
                    all_mandates.setdefault(party, []).append(val)
        except Exception as e:
            log.debug("RSS %s נכשל: %s", url, e)
        time.sleep(0.5)

    if not all_mandates:
        raise RuntimeError("לא נמצאו נתוני סקרים ב-RSS")

    return {p: sum(v) / len(v) for p, v in all_mandates.items()}


# ─── מקור 2: Scraping עמודי חדשות ───────────────────────────────────────────

def fetch_scraping() -> dict[str, float]:
    pages = [
        "https://www.ynet.co.il/news/politics",
        "https://www.maariv.co.il/politics",
    ]
    poll_keywords = ["סקר", "מנדטים"]
    all_mandates: dict[str, list[float]] = {}

    for url in pages:
        for attempt in range(2):
            try:
                if attempt == 0:
                    r = requests.get(url, headers=HEADERS, timeout=12)
                else:
                    import cloudscraper
                    cs = cloudscraper.create_scraper()
                    r = cs.get(url, timeout=12)

                if r.status_code != 200:
                    continue

                # חפש כל פסקה עם מילות מפתח
                paragraphs = re.findall(r"[^.!?]*(?:סקר|מנדטים)[^.!?]*", r.text)
                for para in paragraphs:
                    mandates = extract_mandates_from_text(para)
                    for party, val in mandates.items():
                        all_mandates.setdefault(party, []).append(val)
                break
            except Exception as e:
                log.debug("Scraping %s (ניסיון %d) נכשל: %s", url, attempt + 1, e)
        time.sleep(1)

    if not all_mandates:
        raise RuntimeError("לא נמצאו נתוני סקרים ב-scraping")

    return {p: sum(v) / len(v) for p, v in all_mandates.items()}


# ─── מקור 3: Google Trends ───────────────────────────────────────────────────

def fetch_google_trends() -> dict[str, float]:
    from pytrends.request import TrendReq

    # ממפים מפלגות לשמות חיפוש בגוגל
    kw_map = {
        "ליכוד":          "ליכוד",
        "יש עתיד":        "יש עתיד",
        "מחנה המדינה":    "מחנה המדינה",
        "ישראל ביתנו":    "ישראל ביתנו",
        'ש"ס':            "שס",
    }
    pt = TrendReq(hl="he-IL", tz=120, timeout=(10, 25))

    # pytrends מוגבל ל-5 מילות מפתח בבקשה
    kw_list = list(kw_map.values())[:5]
    pt.build_payload(kw_list, cat=16, timeframe="now 7-d", geo="IL")
    time.sleep(2)

    df = pt.interest_over_time()
    if df.empty:
        raise RuntimeError("Google Trends החזיר תגובה ריקה")

    # לוקחים ממוצע שבועי ומנרמלים ל-0-100
    avg = df[kw_list].mean().to_dict()
    max_val = max(avg.values()) or 1

    # ממירים עניין יחסי לאומדן מנדטים גס (קנה מידה לינארי)
    result = {}
    for party, kw in kw_map.items():
        if kw in avg:
            normalized = avg[kw] / max_val  # 0..1
            # מניחים שהמפלגה הגדולה ≈ 30 מנדטים
            result[party] = round(normalized * 30, 1)

    return result


# ─── מקור 4: Polymarket ──────────────────────────────────────────────────────

def fetch_polymarket() -> dict[str, float]:
    r = requests.get(
        "https://gamma-api.polymarket.com/markets?q=israel+election",
        timeout=12,
    )
    r.raise_for_status()
    markets = r.json()

    result = {}
    for market in markets:
        question = market.get("question", "")
        outcomes = market.get("outcomes", [])
        prices = market.get("outcomePrices", [])

        for party, keywords in PARTIES.items():
            if not any(k in question for k in keywords):
                continue
            for i, outcome in enumerate(outcomes):
                if any(k in outcome for k in keywords):
                    try:
                        prob = float(prices[i])
                        # הסתברות × 120 מנדטים כאומדן גס
                        result[party] = round(prob * TOTAL_SEATS, 1)
                    except (IndexError, ValueError):
                        pass

    if not result:
        raise RuntimeError("לא נמצאו שווקי בחירות ישראל ב-Polymarket")

    return result


# ─── מקור 5: Knesset Open Data (נתוני רקע היסטוריים) ────────────────────────

def fetch_knesset_baseline() -> dict[str, float]:
    r = requests.get(
        "https://knesset.gov.il/Odata/ParliamentInfo.svc/KNS_Party?$format=json",
        timeout=12,
    )
    r.raise_for_status()
    parties_data = r.json().get("value", [])

    # ממפים שמות כנסת לשמות ווידג'ט + מנדטים אחרונים (כנסת 25)
    knesset25 = {
        "הליכוד":          32,
        "יש עתיד":         24,
        "המחנה הממלכתי":   12,
        "ש\"ס":            11,
        "יהדות התורה":     7,
        "הציונות הדתית":   7,
        "עוצמה יהודית":    6,
        "ישראל ביתנו":     6,
        "עבודה":           4,
        "רע\"מ":           5,
        "חד\"ש-תע\"ל":    5,
        "מרצ":             4,
    }

    result = {}
    for party_widget, keywords in PARTIES.items():
        for kw in keywords:
            for k, seats in knesset25.items():
                if kw in k or k in kw:
                    result[party_widget] = float(seats)
                    break

    if not result:
        raise RuntimeError("לא הצלחנו למפות נתוני כנסת")

    return result


# ─── שילוב משוקלל ────────────────────────────────────────────────────────────

def weighted_merge(sources: list[tuple[dict | None, float]]) -> dict[str, float]:
    """ממזג מקורות עם שקלול דינמי — מקור שנפל מחלק את משקלו לאחרים."""
    active = [(data, w) for data, w in sources if data is not None]
    if not active:
        return {}

    total_w = sum(w for _, w in active)
    merged: dict[str, list[tuple[float, float]]] = {}

    for data, w in active:
        norm_w = w / total_w
        for party, val in data.items():
            merged.setdefault(party, []).append((val, norm_w))

    result = {}
    for party, items in merged.items():
        total = sum(v * w for v, w in items)
        weight_sum = sum(w for _, w in items)
        result[party] = round(total / weight_sum, 1)

    return result


def compute_trend(current: float, previous: float | None) -> str:
    if previous is None:
        return "stable"
    diff = current - previous
    if diff > 1.0:
        return "up"
    if diff < -1.0:
        return "down"
    return "stable"


# ─── פונקציה ראשית ───────────────────────────────────────────────────────────

def collect() -> dict:
    log.info("מתחיל איסוף נתונים...")

    # טוען נתונים קודמים לחישוב מגמה
    previous: dict[str, float] = {}
    if DATA_FILE.exists():
        try:
            old = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            previous = {p["name"]: p["score"] for p in old.get("parties", [])}
        except Exception:
            pass

    # ─── שלב 1: RSS (משקל 30%)
    rss_data, rss_w = fetch_with_fallback("ynet/maariv/walla RSS", fetch_rss, 0.30)

    # ─── שלב 2: Scraping (משקל 20%)
    scrape_data, scrape_w = fetch_with_fallback("scraping חדשות", fetch_scraping, 0.20)

    # ─── שלב 3: Google Trends (משקל 20%)
    trends_data, trends_w = fetch_with_fallback("google_trends", fetch_google_trends, 0.20)

    # ─── שלב 4: Polymarket (משקל 20%)
    poly_data, poly_w = fetch_with_fallback("polymarket", fetch_polymarket, 0.20)

    # ─── שלב 5: Knesset baseline (משקל 10% — fallback אחרון)
    knesset_data, knesset_w = fetch_with_fallback("knesset_baseline", fetch_knesset_baseline, 0.10)

    sources_used = []
    sources_failed = []
    for name, data, w in [
        ("ynet_rss",      rss_data,      rss_w),
        ("scraping",      scrape_data,   scrape_w),
        ("google_trends", trends_data,   trends_w),
        ("polymarket",    poly_data,     poly_w),
        ("knesset",       knesset_data,  knesset_w),
    ]:
        (sources_used if data is not None else sources_failed).append(name)

    merged = weighted_merge([
        (rss_data,     rss_w),
        (scrape_data,  scrape_w),
        (trends_data,  trends_w),
        (poly_data,    poly_w),
        (knesset_data, knesset_w),
    ])

    if not merged:
        log.error("כל המקורות נכשלו — שומר נתונים ריקים")
        merged = {}

    # בנה רשימת מפלגות מעל מחסום (≥3.25%)
    total_seats = sum(merged.values()) or TOTAL_SEATS
    parties_out = []
    for party, score in sorted(merged.items(), key=lambda x: -x[1]):
        pct = (score / total_seats) * 100
        if pct < THRESHOLD and score < 4:
            continue
        parties_out.append({
            "name":  party,
            "score": score,
            "trend": compute_trend(score, previous.get(party)),
        })

    result = {
        "updated":        datetime.now().strftime("%d/%m/%Y %H:%M"),
        "sources_used":   sources_used,
        "sources_failed": sources_failed,
        "parties":        parties_out,
    }

    DATA_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("✅ data.json עודכן — %d מפלגות", len(parties_out))
    return result


if __name__ == "__main__":
    collect()
