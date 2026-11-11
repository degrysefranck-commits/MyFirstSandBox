import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

OUTPUT = "news.json"
TRENDS_OUTPUT = "trends.json"
MAX_ITEMS = 3
MAX_WORDS = 30

TRENDS_SOURCES = [
    ("Google Trends FR", "https://trends.google.com/trending/rss?geo=FR"),
    ("Google Trends US", "https://trends.google.com/trending/rss?geo=US"),
]

WIKI_PREFIXES = ("spécial:", "special:", "fichier:", "catégorie:", "category:", "wikipédia:", "portail:", "discussion:", "modèle:", "template:", "aide:", "help:")

MEDIA_NS = "{http://search.yahoo.com/mrss/}"
CONTENT_NS = "{http://purl.org/rss/1.0/modules/content/}"
IMG_RE = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)
WORD_RE = re.compile(r"[a-zàâäéèêëîïôöùûüç]+")

STOPWORDS = set("""
le la les de des du un une et ou à a au aux en dans par pour sur sous avec sans mais donc or ni car
que qui quoi dont est sont était été être avoir fait faire plus moins tout tous toute toutes ce cet
cette ces son sa ses leur leurs mon ma mes ton ta tes notre nos votre vos il elle ils elles on nous
vous je tu ne pas aussi comme si y en d l the a an and of to in on for with at by from is are was were
be been it its this that these those
""".split())

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


def tokenize(text):
    tokens = []
    for token in WORD_RE.findall(text.lower().replace("_", " ")):
        if len(token) >= 3 and token not in STOPWORDS and not token.isdigit():
            tokens.append(token)
    return tokens


def trend_words_rss(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    root = ET.fromstring(data)
    tokens = []
    for item in root.findall("./channel/item"):
        tokens.extend(tokenize(item.findtext("title") or ""))
    return tokens


def trend_words_wiki():
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y/%m/%d")
    url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/top/fr.wikipedia/all-access/{yesterday}"
    req = urllib.request.Request(url, headers={"User-Agent": "MyFirstSandBox/1.0 (contact: local)"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    tokens = []
    for entry in data.get("items", []):
        for art in entry.get("articles", [])[:100]:
            name = art.get("article", "")
            if name.lower().startswith(WIKI_PREFIXES):
                continue
            tokens.extend(tokenize(name))
    return tokens


def fetch_trends():
    counts = {}
    sources_ok = []
    for name, url in TRENDS_SOURCES:
        try:
            for token in trend_words_rss(url):
                counts[token] = counts.get(token, 0) + 1
            sources_ok.append(name)
        except Exception as exc:
            print(f"[tendances] {name} indisponible ({exc})")
    try:
        for token in trend_words_wiki():
            counts[token] = counts.get(token, 0) + 1
        sources_ok.append("Wikipedia FR (top consultations)")
    except Exception as exc:
        print(f"[tendances] Wikipédia indisponible ({exc})")
    words = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:MAX_WORDS]
    return [{"word": w, "count": c} for w, c in words], sources_ok


def main():
    try:
        with open(OUTPUT, encoding="utf-8") as f:
            previous = json.load(f)
    except (OSError, json.JSONDecodeError):
        previous = {}

    try:
        with open(TRENDS_OUTPUT, encoding="utf-8") as f:
            previous_trends = json.load(f).get("words", [])
    except (OSError, json.JSONDecodeError, AttributeError):
        previous_trends = []

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

    try:
        trend_words, sources_ok = fetch_trends()
    except Exception as exc:
        trend_words = previous_trends
        sources_ok = []
        print(f"[tendances] indisponible ({exc}), anciennes donnees conservees")
    trends_payload = {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sources": sources_ok,
        "words": trend_words,
    }
    with open(TRENDS_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(trends_payload, f, ensure_ascii=False, indent=2)
    print(f"{len(trend_words)} mots de tendance ecrits dans {TRENDS_OUTPUT} ({len(sources_ok)} sources)")


if __name__ == "__main__":
    main()
