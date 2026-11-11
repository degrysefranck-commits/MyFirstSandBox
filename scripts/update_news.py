import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

OUTPUT = "news.json"
MAX_ITEMS = 3

THEMES = {
    "monde": {
        "label": "🌍 Monde",
        "feed": "https://feeds.bbci.co.uk/news/world/rss.xml",
    },
    "art": {
        "label": "🎨 Art",
        "feed": "https://www.theguardian.com/artanddesign/rss",
    },
    "culture": {
        "label": "🎭 Culture",
        "feed": "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
    },
    "high-tech": {
        "label": "💻 High-tech",
        "feed": "https://feeds.bbci.co.uk/news/technology/rss.xml",
    },
    "nature": {
        "label": "🌿 Nature",
        "feed": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
    },
    "sante": {
        "label": "🏥 Santé",
        "feed": "https://feeds.bbci.co.uk/news/health/rss.xml",
    },
    "sport": {
        "label": "⚽ Sport",
        "feed": "https://feeds.bbci.co.uk/sport/rss.xml",
    },
}


def fetch_items(feed_url):
    req = urllib.request.Request(feed_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    root = ET.fromstring(data)
    items = []
    for item in root.findall("./channel/item")[:MAX_ITEMS]:
        items.append({
            "title": (item.findtext("title") or "").strip(),
            "link": (item.findtext("link") or "").strip(),
            "published": (item.findtext("pubDate") or "").strip(),
        })
    return items


def main():
    try:
        with open(OUTPUT, encoding="utf-8") as f:
            previous = json.load(f)
    except (OSError, json.JSONDecodeError):
        previous = {}

    previous_themes = previous.get("themes", {})
    themes = {}
    for key, theme in THEMES.items():
        entry = {"label": theme["label"], "source": theme["feed"], "items": []}
        try:
            entry["items"] = fetch_items(theme["feed"])
        except Exception as exc:
            entry["items"] = previous_themes.get(key, {}).get("items", [])
            print(f"[{key}] flux indisponible ({exc}), anciennes donnees conservees")
        themes[key] = entry

    payload = {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "themes": themes,
    }
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    total = sum(len(t["items"]) for t in themes.values())
    print(f"{total} actualites ecrites dans {OUTPUT} ({len(themes)} themes)")


if __name__ == "__main__":
    main()
