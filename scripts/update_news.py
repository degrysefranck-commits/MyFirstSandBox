import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

OUTPUT = "news.json"
TRENDS_OUTPUT = "trends.json"
ARCHIVES_OUTPUT = "archives.json"
MAX_ITEMS = 3
MAX_WORDS = 30
MAX_ARCHIVE_DAYS = 30

TRENDS_SOURCES = [
    ("Google Trends FR (recherches)", "https://trends.google.com/trending/rss?geo=FR"),
    ("Google News FR (une)", "https://news.google.com/rss?hl=fr-FR&gl=FR&ceid=FR:fr"),
    ("France 24 (une)", "https://www.france24.com/fr/rss"),
    ("France Info (une)", "https://www.francetvinfo.fr/titres.rss"),
    ("Le Monde (une)", "https://www.lemonde.fr/rss/une.xml"),
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
vous je tu ne pas aussi comme si y en d l après avant depuis selon entre chez vers alors ainsi déjà
encore lors leur leurs peu chaque autres autre même mêmes jour jours an ans the a an and of to in
on for with at by from is are was were be been it its this that these those
""".split())

THEMES = {
    "art": {
        "label": "🎨 Art",
        "sources": [
            ("Beaux Arts", "https://www.beauxarts.com/feed/"),
            ("Connaissance des Arts", "https://www.connaissancedesarts.com/feed/"),
        ],
    },
    "auto": {
        "label": "🚗 Auto",
        "sources": [
            ("Auto Plus", "https://www.autoplus.fr/rss"),
            ("Auto Moto", "https://www.auto-moto.com/feed"),
        ],
    },
    "culture": {
        "label": "🎭 Culture",
        "sources": [
            ("Le Monde Culture", "https://www.lemonde.fr/culture/rss_full.xml"),
            ("France 24 Culture", "https://www.france24.com/fr/culture/rss"),
        ],
    },
    "high-tech": {
        "label": "💻 High-tech",
        "sources": [
            ("Numerama", "https://www.numerama.com/feed/"),
            ("01net", "https://www.01net.com/feed/"),
            ("Presse Citron", "https://www.presse-citron.net/feed/"),
        ],
    },
    "ia": {
        "label": "🤖 IA",
        "sources": [
            ("ActuIA", "https://www.actuia.com/feed/"),
            ("Numerama IA", "https://www.numerama.com/intelligence-artificielle/feed/"),
            ("01net IA", "https://www.01net.com/actualites/intelligence-artificielle/feed/"),
        ],
    },
    "monde": {
        "label": "🌍 Monde",
        "sources": [
            ("France 24 Monde", "https://www.france24.com/fr/monde/rss"),
            ("Le Monde International", "https://www.lemonde.fr/international/rss_full.xml"),
        ],
    },
    "nature": {
        "label": "🌿 Nature",
        "sources": [
            ("Futura Sciences", "https://www.futura-sciences.com/rss/actualites.xml"),
            ("SciencePost", "https://www.sciencepost.fr/feed/"),
        ],
    },
    "sante": {
        "label": "🏥 Santé",
        "sources": [
            ("Sciences et Avenir", "https://www.sciencesetavenir.fr/sante/rss.xml"),
            ("Santé Magazine", "https://www.santemagazine.fr/rss"),
        ],
    },
    "sport": {
        "label": "⚽ Sport",
        "sources": [
            ("Le Monde Sport", "https://www.lemonde.fr/sport/rss_full.xml"),
            ("France 24 Sport", "https://www.france24.com/fr/sport/rss"),
        ],
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


def fetch_items(feed_url, limit=8):
    req = urllib.request.Request(feed_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    root = ET.fromstring(data)
    items = []
    for item in root.findall("./channel/item")[:limit]:
        items.append({
            "title": (item.findtext("title") or "").strip(),
            "link": (item.findtext("link") or "").strip(),
            "published": (item.findtext("pubDate") or "").strip(),
            "image": extract_image(item),
        })
    return items


def normalize_title(title):
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def parse_pubdate(value):
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        return 0.0


def fetch_theme_items(theme):
    sources_ok = []
    merged = []
    for name, feed in theme["sources"]:
        try:
            for item in fetch_items(feed):
                if item["title"] and item["link"]:
                    merged.append((parse_pubdate(item["published"]), item, name))
            sources_ok.append(name)
        except Exception as exc:
            print(f"  [{name}] indisponible ({exc})")
    merged.sort(key=lambda t: -t[0])
    seen = set()
    deduped = []
    for score, item, name in merged:
        key = normalize_title(item["title"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append((score, item, name))
    max_per_source = MAX_ITEMS if len(sources_ok) <= 1 else 2
    count_per_source = {}
    selected = []
    for score, item, name in deduped:
        if len(selected) >= MAX_ITEMS:
            break
        if count_per_source.get(name, 0) >= max_per_source:
            continue
        count_per_source[name] = count_per_source.get(name, 0) + 1
        selected.append((score, item, name))
    items = []
    for score, item, name in selected:
        items.append({
            "title": item["title"],
            "link": item["link"],
            "published": item["published"],
            "image": item["image"],
            "source": name,
        })
    return items, sources_ok


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
    for item in root.findall("./channel/item")[:25]:
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


def update_archives(payload):
    try:
        with open(ARCHIVES_OUTPUT, encoding="utf-8") as f:
            archives = json.load(f)
    except (OSError, json.JSONDecodeError):
        archives = {}
    days = archives.get("days", {})
    day_key = payload["updated_at"][:10]
    days[day_key] = {"updated_at": payload["updated_at"], "themes": payload["themes"]}
    ordered = dict(sorted(days.items(), reverse=True)[:MAX_ARCHIVE_DAYS])
    with open(ARCHIVES_OUTPUT, "w", encoding="utf-8") as f:
        json.dump({"days": ordered}, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"{len(ordered)} jour(s) archive(s) dans {ARCHIVES_OUTPUT}")


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
        entry = {"label": theme["label"], "source": theme["sources"][0][1], "sources": [], "items": []}
        try:
            entry["items"], entry["sources"] = fetch_theme_items(theme)
            if not entry["items"]:
                raise ValueError("aucun item exploitable")
        except Exception as exc:
            entry["items"] = previous_themes.get(key, {}).get("items", [])
            entry["sources"] = previous_themes.get(key, {}).get("sources", [s[0] for s in theme["sources"]])
            print(f"[{key}] sources indisponibles ({exc}), anciennes donnees conservees")
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
    update_archives(payload)

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
