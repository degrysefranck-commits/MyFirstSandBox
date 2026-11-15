const CORS = { "Access-Control-Allow-Origin": "*", "Content-Type": "application/json" };

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: CORS });
  }
  try {
    const feed = new URL(req.url).searchParams.get("feed");
    if (!feed || !feed.startsWith("http")) {
      return new Response(JSON.stringify({ error: "missing or invalid feed" }), { status: 400, headers: CORS });
    }
    const resp = await fetch(feed, { headers: { "User-Agent": "Mozilla/5.0" } });
    if (!resp.ok) throw new Error("feed HTTP " + resp.status);
    const xml = await resp.text();
    const items = [...xml.matchAll(/<item>([\s\S]*?)<\/item>/g)].slice(0, 3).map((m) => {
      const block = m[1];
      const pick = (tag: string): string => {
        const mm = block.match(new RegExp("<" + tag + "[^>]*>([\\s\\S]*?)</" + tag + ">"));
        return mm ? mm[1].replace(/<!\[CDATA\[|\]\]>/g, "").trim() : "";
      };
      const img =
        (block.match(/<media:content[^>]+url="([^"]+)"/) || [])[1] ||
        (block.match(/<enclosure[^>]+url="([^"]+)"[^>]*type="image/) || [])[1] ||
        null;
      return { title: pick("title"), link: pick("link"), published: pick("pubDate"), image: img };
    }).filter((i) => i.title && i.link);
    return new Response(JSON.stringify({ items }), { headers: CORS });
  } catch (e) {
    return new Response(JSON.stringify({ error: String(e) }), { status: 502, headers: CORS });
  }
});
