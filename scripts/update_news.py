import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

OUTPUT = "news.json"
MAX_ITEMS = 3

MEDIA_NS = "{http://search.yahoo.com/mrss/}"
CONTENT_NS = "{http://purl.org/rss/1.0/modules/content/}"
IMG_RE = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)

THEMES = {
    "monde": {
        "label": "🌍 Monde",
        "feed": "https://www.france24.com/fr/monde/rss",
    },
    "art": {
        "label": "🎨 Art",
        "feed": "https://www.beauxarts.com/feed/",
    },
    "culture": {
        "label": "🎭 Culture",
        "feed": "https://www.lemonde.fr/culture/rss_full.xml",
    },
    "high-tech": {
        "label": "💻 High-tech",
        "feed": "https://www.numerama.com/feed/",
    },
    "nature": {
        "label": "🌿 Nature",
        "feed": "https://www.futura-sciences.com/rss/actualites.xml",
    },
    "sante": {
        "label": "🏥 Santé",
        "feed": "https://www.sciencesetavenir.fr/sante/rss.xml",
    },
    "sport": {
        "label": "⚽ Sport",
        "feed": "https://www.lemonde.fr/sport/rss_full.xml",
    },
}


def extract_image(item):
    for media in item.findall(MEDIA_NS + "content"):
        url = (media.get("url") or "").strip()
        if url.startswith("http") and (
            (media.get("medium") or "").lower() == "image"
            or (media.get("type") or "").startswith("image")
        ):
            return url
    for media in item.findall(MEDIA_NS + "content"):
        url = (media.get("url") or "").strip()
        if url.startswith("http"):
            return url
    thumb = item.find(MEDIA_NS + "thumbnail")
    if thumb is not None and (thumb.get("url") or "").startswith("http"):
        return thumb.get("url").strip()
    for enc in item.findall("enclosure"):
        if (enc.get("type") or "").startswith("image") and (enc.get("url") or "").startswith("http"):
            return enc.get("url").strip()
    html = (item.findtext("description") or "") + (item.findtext(CONTENT_NS + "encoded") or "")
    match = IMG_RE.search(html)
    if match and match.group(1).startswith("http"):
        return match.group(1)
    return None


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
            "image": extract_image(item),
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
    with_img = sum(1 for t in themes.values() for i in t["items"] if i.get("image"))
    print(f"{total} actualites ({with_img} avec image) ecrites dans {OUTPUT} ({len(themes)} themes)")


if __name__ == "__main__":
    main()
