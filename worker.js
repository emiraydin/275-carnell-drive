export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    let pathname = decodeURIComponent(url.pathname);

    // Clean double slashes in pathname
    while (pathname.includes("//")) {
      pathname = pathname.replace("//", "/");
    }

    // 1. Handle CORS preflight OPTIONS requests
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type, Authorization, x-matterport-application-name, x-requested-with",
          "Access-Control-Max-Age": "86400",
        },
      });
    }

    // 2. Handle public-access token request
    if (pathname.includes("/public-access")) {
      return new Response(JSON.stringify({ token: "dummy_token_12345" }), {
        headers: {
          "content-type": "application/json; charset=utf-8",
          "Access-Control-Allow-Origin": "*",
          "Cache-Control": "no-cache, no-store, must-revalidate",
        },
      });
    }

    if (pathname === "/" || pathname === "") {
      pathname = "/index.html";
    }
    
    // Remove leading slash for R2 key lookup
    const rawKey = pathname.startsWith("/") ? pathname.slice(1) : pathname;

    // Helper to attempt fetch from R2 (checks raw key, then assets/ prefix if needed, then path rewrites)
    async function getFromBucket(key) {
      let obj = await env.BUCKET.get(key);
      if (obj) return obj;

      if (!key.startsWith("assets/")) {
        obj = await env.BUCKET.get(`assets/${key}`);
        if (obj) return obj;
      }

      // Handle tiles folder hyphen stripping
      if (key.includes("/tiles/")) {
        const parts = key.split("/");
        let modified = false;
        for (let i = 0; i < parts.length; i++) {
          if (parts[i].length === 36 && parts[i].split("-").length === 5) {
            parts[i] = parts[i].replaceAll("-", "");
            modified = true;
          }
        }
        if (modified) {
          const altKey = parts.join("/");
          obj = await env.BUCKET.get(altKey);
          if (!obj && !altKey.startsWith("assets/")) {
            obj = await env.BUCKET.get(`assets/${altKey}`);
          }
          if (obj) return obj;
        }
      }

      // Handle mesh_tiles tilde swaps
      if (key.includes("/~/mesh_tiles/")) {
        const altKey = key.replace("/~/mesh_tiles/", "/mesh_tiles/~/");
        obj = await env.BUCKET.get(altKey);
        if (!obj && !altKey.startsWith("assets/")) {
          obj = await env.BUCKET.get(`assets/${altKey}`);
        }
        if (obj) return obj;
      }

      if (key.includes("/mesh_tiles/~/")) {
        const altKey = key.replace("/mesh_tiles/~/", "/~/mesh_tiles/");
        obj = await env.BUCKET.get(altKey);
        if (!obj && !altKey.startsWith("assets/")) {
          obj = await env.BUCKET.get(`assets/${altKey}`);
        }
        if (obj) return obj;
      }

      // Handle removing /~/ if file exists without tilde
      if (key.includes("/~/")) {
        const altKey = key.replace("/~/", "/");
        obj = await env.BUCKET.get(altKey);
        if (!obj && !altKey.startsWith("assets/")) {
          obj = await env.BUCKET.get(`assets/${altKey}`);
        }
        if (obj) return obj;
      }

      return null;
    }

    // 3. Handle POST requests to /api/mp/models/graph
    if (request.method === "POST" && pathname === "/api/mp/models/graph") {
      try {
        const body = await request.json();
        const opName = body?.operationName;
        if (opName) {
          const graphKey = `api/mp/models/graph_${opName}.json`;
          const graphObj = await getFromBucket(graphKey);
          if (graphObj) {
            let text = await graphObj.text();
            text = text.replaceAll("http://127.0.0.1:8080/", `${url.origin}/`);
            text = text.replaceAll("http://127.0.0.1:8080", `${url.origin}`);
            text = text.replaceAll("\"purchased\"", "\"active\"");
            text = text.replaceAll("\"state\":null", "\"state\":\"active\"");
            return new Response(text, {
              headers: {
                "content-type": "application/json; charset=utf-8",
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "no-cache, no-store, must-revalidate",
              },
            });
          }
        }
      } catch (e) {
        // Fallback on JSON parse error
      }
      return new Response(JSON.stringify({ data: "empty" }), {
        headers: {
          "content-type": "application/json; charset=utf-8",
          "Access-Control-Allow-Origin": "*",
          "Cache-Control": "no-cache, no-store, must-revalidate",
        },
      });
    }

    // 4. Handle /api/player/models/{modelId}/files?type=N
    if (pathname.includes("/api/player/models/") && pathname.endsWith("/files")) {
      const typeParam = url.searchParams.get("type");
      if (typeParam) {
        const typeKey = `${rawKey}_type${typeParam}`;
        const typeObj = await getFromBucket(typeKey);
        if (typeObj) {
          return serveR2Object(typeObj, typeKey, url);
        }
      }
    }

    // 5. Handle showcase JS redirect
    if (pathname === "/js/showcase.js") {
      const internalJsObj = await getFromBucket("js/showcase-internal.js");
      if (internalJsObj) {
        return serveR2Object(internalJsObj, "js/showcase-internal.js", url);
      }
    }

    // 6. Handle JPG crop and width query parameter rewrites
    if (pathname.endsWith(".jpg") && url.searchParams.has("crop")) {
      const crop = url.searchParams.get("crop");
      const width = url.searchParams.get("width");

      const widthPart = width ? `width=${width}_` : "";
      const cropPart = `crop=${crop}`;
      const testKey = `${rawKey}${widthPart}${cropPart}.jpg`;

      const cropObj = await getFromBucket(testKey);
      if (cropObj) {
        return serveR2Object(cropObj, testKey, url);
      }
    }

    // 7. Default asset lookup in R2
    let object = await getFromBucket(rawKey);

    // 8. Handle locale fallback if requested locale is missing
    if (!object && pathname.startsWith("/locale/messages/strings_")) {
      object = await getFromBucket("locale/strings.json");
    }

    // Fallback 200 OK for harmless analytics / user API endpoints if missing
    if (!object && pathname.includes("/api/")) {
      return new Response(JSON.stringify({ status: "ok" }), {
        status: 200,
        headers: {
          "content-type": "application/json; charset=utf-8",
          "Access-Control-Allow-Origin": "*",
        },
      });
    }

    if (!object) {
      return new Response("Not Found", {
        status: 404,
        headers: { "Access-Control-Allow-Origin": "*" }
      });
    }

    return serveR2Object(object, rawKey, url);
  }
};

async function serveR2Object(object, key, reqUrl) {
  const headers = new Headers();
  object.writeHttpMetadata(headers);
  headers.set("etag", object.httpEtag);
  headers.set("Access-Control-Allow-Origin", "*");
  
  const mime = getMimeType(key);
  if (!headers.has("content-type")) {
    headers.set("content-type", mime);
  }

  if (mime.includes("json") || mime.includes("html") || mime.includes("javascript")) {
    headers.set("Cache-Control", "no-cache, no-store, must-revalidate");
  }

  if (mime.includes("json") || mime.includes("html") || mime.includes("javascript") || key.includes("api/player/models/")) {
    let text = await object.text();
    if (text.includes("127.0.0.1:8080") || text.includes("cdn-1.matterport.com") || text.includes("cdn-2.matterport.com") || text.includes("static.matterport.com")) {
      const origin = reqUrl.origin;
      text = text.replaceAll("http://127.0.0.1:8080/", `${origin}/`);
      text = text.replaceAll("http://127.0.0.1:8080", `${origin}`);
      text = text.replaceAll("https://cdn-1.matterport.com/", `${origin}/`);
      text = text.replaceAll("https://cdn-2.matterport.com/", `${origin}/`);
      text = text.replaceAll("https://cdn-3.matterport.com/", `${origin}/`);
      text = text.replaceAll("https://static.matterport.com/", `${origin}/`);
      text = text.replaceAll("https://mp-app-prod.global.ssl.fastly.net/", `${origin}/`);
      text = text.replaceAll("\"purchased\"", "\"active\"");
      text = text.replaceAll("\"state\":null", "\"state\":\"active\"");
    }
    return new Response(text, { headers });
  }

  return new Response(object.body, { headers });
}

function getMimeType(path) {
  if (path.endsWith(".html")) return "text/html; charset=utf-8";
  if (path.endsWith(".js")) return "application/javascript; charset=utf-8";
  if (path.endsWith(".css")) return "text/css; charset=utf-8";
  if (path.endsWith(".json") || path.includes("api/player/models/")) return "application/json; charset=utf-8";
  if (path.endsWith(".jpg") || path.endsWith(".jpeg")) return "image/jpeg";
  if (path.endsWith(".png")) return "image/png";
  if (path.endsWith(".svg")) return "image/svg+xml";
  if (path.endsWith(".wasm")) return "application/wasm";
  if (path.endsWith(".woff")) return "font/woff";
  if (path.endsWith(".woff2")) return "font/woff2";
  if (path.endsWith(".ttf")) return "font/ttf";
  return "application/octet-stream";
}
