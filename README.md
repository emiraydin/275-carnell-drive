# 275 Carnell Drive — Self-Hosted Matterport 3D Tour

Self-hosted Matterport 3D tour for **275 Carnell Drive** (model ID `vUb5e71k91Q`), served from Cloudflare Workers + R2.

| | URL |
|---|---|
| **Live** | https://275.eaweb.fyi/?m=vUb5e71k91Q |
| **Worker** | https://carnell-drive-3d.emiraydin.workers.dev/?m=vUb5e71k91Q |
| **Original** | https://my.matterport.com/show/?m=vUb5e71k91Q |

---

## Architecture

```
Browser  →  Cloudflare Worker (worker.js)  →  R2 Bucket (275-carnell-drive)
                    ↓
        URL rewriting on-the-fly:
        - cdn-{1,2,3}.matterport.com  →  self
        - static.matterport.com       →  self
        - mp-app-prod.global.ssl...   →  self
        - 127.0.0.1:8080              →  self
```

**Key files:**
- `worker.js` — Cloudflare Worker that serves assets from R2 with dynamic URL rewriting
- `dev-server.py` — Python dev server for local testing (mirrors worker.js logic)
- `wrangler.toml` — Cloudflare deployment config
- `assets/` — All Matterport assets (JS, HTML, CSS, 3D meshes, textures, panoramic tiles, API responses)

---

## Prerequisites

- [Node.js](https://nodejs.org/) (v18+)
- [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/) (`npm install -g wrangler`)
- A Cloudflare account with R2 enabled
- Python 3 (for local dev server)

---

## Local Development

```bash
# Start the local dev server on http://127.0.0.1:8080
python3 dev-server.py

# Open in browser
open "http://127.0.0.1:8080/?m=vUb5e71k91Q"
```

The dev server (`dev-server.py`) handles:
- Serving all assets from the `assets/` directory
- GraphQL POST request routing (`/api/mp/models/graph`)
- Tile folder UUID hyphen stripping (disk uses unhyphenated UUIDs)
- CORS headers
- Public access token endpoint

---

## Deploying to Cloudflare

### 1. Authenticate with Cloudflare

```bash
npx wrangler login
```

### 2. Create the R2 Bucket (first time only)

```bash
npx wrangler r2 bucket create 275-carnell-drive
```

### 3. Upload All Assets to R2

The assets must be uploaded to the remote R2 bucket. Use the bulk upload script:

```bash
# Upload entire assets directory to R2
# This uses rclone or a loop — wrangler doesn't have a bulk upload command,
# so we upload key directories individually:

# Upload all files recursively (may take a while — ~35,000 files)
find assets -type f | while read f; do
  key="${f#assets/}"
  npx wrangler r2 object put "275-carnell-drive/${key}" --file "${f}" --remote
done
```

**Or upload by category** (faster for incremental updates):

```bash
# JS files (critical — includes patched showcase engine)
for f in assets/js/*.js; do
  npx wrangler r2 object put "275-carnell-drive/js/$(basename $f)" \
    --file "$f" --content-type "application/javascript" --remote
done

# WebGL vendor files (Draco decoder + Basis transcoder)
npx wrangler r2 object put 275-carnell-drive/webgl-vendors/three/0.151.3/libs/basis/basis_transcoder.js \
  --file assets/webgl-vendors/three/0.151.3/libs/basis/basis_transcoder.js \
  --content-type "application/javascript" --remote

npx wrangler r2 object put 275-carnell-drive/webgl-vendors/three/0.151.3/libs/basis/basis_transcoder.wasm \
  --file assets/webgl-vendors/three/0.151.3/libs/basis/basis_transcoder.wasm \
  --content-type "application/wasm" --remote

npx wrangler r2 object put 275-carnell-drive/webgl-vendors/three/0.151.3/libs/draco/gltf/draco_wasm_wrapper.js \
  --file assets/webgl-vendors/three/0.151.3/libs/draco/gltf/draco_wasm_wrapper.js \
  --content-type "application/javascript" --remote

npx wrangler r2 object put 275-carnell-drive/webgl-vendors/three/0.151.3/libs/draco/gltf/draco_decoder.wasm \
  --file assets/webgl-vendors/three/0.151.3/libs/draco/gltf/draco_decoder.wasm \
  --content-type "application/wasm" --remote

# GraphQL API responses
for f in assets/api/mp/models/graph_*.json; do
  npx wrangler r2 object put "275-carnell-drive/api/mp/models/$(basename $f)" \
    --file "$f" --content-type "application/json" --remote
done

# HTML
npx wrangler r2 object put 275-carnell-drive/index.html \
  --file assets/index.html --content-type "text/html" --remote
```

### 4. Deploy the Worker

```bash
npx wrangler deploy
```

This deploys to:
- `https://carnell-drive-3d.emiraydin.workers.dev`
- `https://275.eaweb.fyi` (custom domain, configured in `wrangler.toml`)

### 5. Update Custom Domain (optional)

To change the custom domain, edit `wrangler.toml`:

```toml
routes = [
  { pattern = "your-subdomain.yourdomain.com", custom_domain = true }
]
```

Then run `npx wrangler deploy` again. Cloudflare will automatically provision DNS and SSL.

---

## What Was Patched (and Why)

The Matterport Showcase JS engine expects to run on `my.matterport.com` with live API access. To make it work self-hosted, the following patches were applied:

### Worker-Level Fixes (`worker.js`)
| Fix | Why |
|-----|-----|
| URL rewriting (`cdn-*.matterport.com`, `static.matterport.com` → self) | All asset URLs in JS/JSON point to Matterport CDNs which block CORS from third-party origins |
| GraphQL POST handler (`/api/mp/models/graph`) | Showcase fetches model data via GraphQL; we serve cached JSON responses |
| Tile UUID hyphen stripping | On-disk tile folders use unhyphenated UUIDs but the JS requests hyphenated ones |
| `/public-access` token endpoint | Showcase expects a token endpoint; we return a dummy token |
| API fallback (200 OK for missing `/api/` routes) | Prevents errors from analytics/tracking endpoints |

### JS-Level Fixes
| File | Fix | Why |
|------|-----|-----|
| `showcase-internal.js` | `a.enabled = !0` override | Sweeps were disabled because `tags` didn't include `"showcase"` |
| `showcase-internal.js` | `getClosestFloorAtHeight` null check | Returned `undefined` causing `TypeError`, triggering "Oops, model not available" |
| `showcase-internal.js` | `setError`/`showError` suppression | Non-critical errors (analytics, missing endpoints) were killing the renderer |
| `65.js` | `activateSweep` fallback | `TiledPanoRenderer` threw when sweep ID wasn't in its map |
| `321.js` | Default sweep ID in `doStandardStart` | Camera fly-in needed a valid starting sweep ID |

### Data Fixes
| File | Fix |
|------|-----|
| `sweeps` | Added `tags: ["showcase", "vr"]` and dual camelCase/snake_case property mappings for all 66 sweeps |
| `graph_*.json` | Set `state` to `"active"` (was `"purchased"` or `null`) |

---

## Troubleshooting

### Black screen after loading spinner
The WebGL vendor files (Draco/Basis) are missing or CORS-blocked. Make sure these 4 files are uploaded to R2:
- `webgl-vendors/three/0.151.3/libs/basis/basis_transcoder.js`
- `webgl-vendors/three/0.151.3/libs/basis/basis_transcoder.wasm`
- `webgl-vendors/three/0.151.3/libs/draco/gltf/draco_wasm_wrapper.js`
- `webgl-vendors/three/0.151.3/libs/draco/gltf/draco_decoder.wasm`

### "Oops, model not available"
Usually means a JS error crashed the renderer. Check browser console. Common causes:
- `updateSpatialSortMap` floor height crash (fixed in `showcase-internal.js`)
- Sweep data missing `tags` (fixed in `sweeps` file)
- Model state not `"active"` (fixed in GraphQL JSON responses)

### 404 errors on tile images
The tile folder UUIDs on disk don't have hyphens but the JS requests them with hyphens. The worker/dev-server handles this automatically via hyphen stripping. If you re-download the model, make sure `worker.js` and `dev-server.py` have the hyphen-stripping logic.

### Custom domain not resolving
After adding a custom domain in `wrangler.toml` and deploying, it can take a few minutes for Cloudflare to provision DNS. The domain must be on a Cloudflare-managed zone.

---

## File Structure

```
275-carnell-drive/
├── worker.js              # Cloudflare Worker (serves assets from R2)
├── wrangler.toml           # Cloudflare deployment config
├── dev-server.py           # Local Python dev server
├── package.json
└── assets/
    ├── index.html          # Main HTML entry point
    ├── css/                # Stylesheets
    ├── js/                 # Patched Matterport Showcase JS
    │   ├── showcase-internal.js  # Core 3D engine (patched)
    │   ├── showcase.js           # Entry point (patched)
    │   ├── 65.js                 # TiledPanoRenderer (patched)
    │   ├── 321.js                # Camera start logic (patched)
    │   └── *.js                  # Other chunk files
    ├── webgl-vendors/      # Three.js + Draco/Basis decoders
    ├── api/                # Cached API/GraphQL responses
    ├── models/             # 3D mesh tiles, textures, panoramic tiles
    ├── images/             # UI images
    ├── fonts/              # Web fonts
    └── locale/             # Localization strings
```

---

## License

This is a personal archive of a Matterport 3D tour. The Matterport Showcase engine is © Matterport, Inc.
