const CORS = { "Access-Control-Allow-Origin": "*", "Content-Type": "application/json" };
const MAX_ITEMS = 3;

function normalizeTitle(t: string): string {
  return t.toLowerCase().replace(/[^a-z0-9à-ÿ]+/g, " ").trim();
}

function parseItems(xml: string) {
  return [...xml.matchAll(/<item>([\s\S]*?)<\/item>/g)].map((m) => {
    const block = m[1];
    const pick = (tag: string): string => {
      const mm = block.match(new RegExp("<" + tag + "[^>]*>([\\s\\S]*?)</" + tag + ">"));
      return mm ? mm[1].replace(/<!\[CDATA\[|\]\]>/g, "").trim() : "";
    };
    const img =
      (block.match(/<media:content[^>]+url="([^"]+)"/) || [])[1] ||
      (block.match(/<enclosure[^>]+url="([^"]+)"[^>]*type="image/) || [])[1] ||
      null;
    return {
      title: pick("title"),
      link: pick("link"),
      published: pick("pubDate"),
      image: img,
      ts: Date.parse(pick("pubDate")) || 0,
    };
  }).filter((i) => i.title && i.link);
}

async function mistralSummary(word: string, items: { title: string }[]): Promise<string | null> {
  const apiKey = Deno.env.get("MISTRAL_API_KEY");
  if (!apiKey || items.length === 0) return null;
  const prompt =
    "Tu es un journaliste francophone. Voici les " + items.length + " derniers titres d'actualité sur le sujet « " + word + " » :\n" +
    items.map((i, n) => (n + 1) + ". " + i.title).join("\n") +
    "\nRédige une synthèse courte en français (2 à 3 phrases maximum) qui relie ces sujets et dégage la tendance principale. Texte fluide, sans liste à puces.";
  const r = await fetch("https://api.mistral.ai/v1/chat/completions", {
    method: "POST",
    headers: { "Authorization": "Bearer " + apiKey, "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "mistral-small-latest",
      messages: [{ role: "user", content: prompt }],
      max_tokens: 220,
      temperature: 0.4,
    }),
  });
  if (!r.ok) return null;
  const d = await r.json();
  return d.choices && d.choices[0] && d.choices[0].message ? d.choices[0].message.content.trim() : null;
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: CORS });
  }
  try {
    const word = (new URL(req.url).searchParams.get("word") || "").trim();
    if (!word) {
      return new Response(JSON.stringify({ error: "missing word" }), { status: 400, headers: CORS });
    }
    const q = encodeURIComponent(word);
    const feeds: [string, string][] = [
      ["Google News FR", "https://news.google.com/rss/search?q=" + q + "&hl=fr-FR&gl=FR&ceid=FR:fr"],
      ["Bing News FR", "https://www.bing.com/news/search?q=" + q + "&format=rss&setlang=fr-fr&cc=fr"],
    ];
    const merged: any[] = [];
    const sources: string[] = [];
    for (const [name, url] of feeds) {
      try {
        const r = await fetch(url, { headers: { "User-Agent": "Mozilla/5.0" } });
        if (!r.ok) throw new Error("HTTP " + r.status);
        for (const it of parseItems(await r.text())) merged.push({ ...it, source: name });
        sources.push(name);
      } catch (e) {
        console.error(name, e);
      }
    }
    merged.sort((a, b) => b.ts - a.ts);
    const seen = new Set<string>();
    const deduped: any[] = [];
    for (const it of merged) {
      const k = normalizeTitle(it.title);
      if (seen.has(k)) continue;
      seen.add(k);
      deduped.push(it);
    }
    const cap = sources.length > 1 ? 2 : MAX_ITEMS;
    const per: Record<string, number> = {};
    const selected: any[] = [];
    for (const it of deduped) {
      if (selected.length >= MAX_ITEMS) break;
      if ((per[it.source] || 0) >= cap) continue;
      per[it.source] = (per[it.source] || 0) + 1;
      selected.push(it);
    }
    const items = selected.map(({ ts, ...it }) => it);
    let summary: string | null = null;
    try {
      summary = await mistralSummary(word, items);
    } catch (e) {
      console.error("mistral", e);
    }
    return new Response(
      JSON.stringify({
        label: word.charAt(0).toUpperCase() + word.slice(1),
        sources,
        items,
        summary,
      }),
      { headers: CORS }
    );
  } catch (e) {
    return new Response(JSON.stringify({ error: String(e) }), { status: 502, headers: CORS });
  }
});
