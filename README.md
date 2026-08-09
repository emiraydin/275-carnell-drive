# 275 Carnell Drive — Self-Hosted Matterport 3D Tour

Self-hosted Matterport 3D tour for **275 Carnell Drive** (model ID `vUb5e71k91Q`), served globally using Cloudflare Workers + Cloudflare R2.

| | URL |
|---|---|
| **Live** | https://275.eaweb.fyi/?m=vUb5e71k91Q |
| **Worker** | https://carnell-drive-3d.emiraydin.workers.dev/?m=vUb5e71k91Q |
| **Original** | https://my.matterport.com/show/?m=vUb5e71k91Q |

---

## System Architecture

```
Browser  →  Cloudflare Worker (worker.js)  →  R2 Bucket (275-carnell-drive)
                    ↓
        URL rewriting on-the-fly:
        - cdn-{1,2,3}.matterport.com  →  self
        - static.matterport.com       →  self
        - mp-app-prod.global.ssl...   →  self
        - 127.0.0.1:8080              →  self
```

**Core Components:**
- **Cloudflare Worker (`worker.js`)**: Serverless function at Cloudflare edge nodes handling CORS, request routing, header injection, and URL rewriting.
- **Cloudflare R2 Bucket (`275-carnell-drive`)**: Object storage containing the full static site assets (~500 MB of 3D mesh tiles, skybox images, textures, JS bundles, and JSON metadata).
- **GitHub Actions (`.github/workflows/deploy.yml`)**: CI/CD pipeline automatically deploying worker code & updated static assets to Cloudflare on every `git push origin main`.

---

## Initial Setup From Scratch

Follow these step-by-step instructions to set up and deploy this project from scratch:

### 1. Prerequisites

- [Node.js](https://nodejs.org/) (v22 LTS)
- [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/) (`npm install -g wrangler`)
- A [Cloudflare](https://dash.cloudflare.com/) account with R2 enabled
- Git and GitHub account

### 2. Clone the Repository

```bash
git clone https://github.com/emiraydin/275-carnell-drive.git
cd 275-carnell-drive
```

### 3. Cloudflare Authentication & R2 Creation

Log in to Wrangler on your local machine:

```bash
npx wrangler login
```

Create the R2 bucket for the project:

```bash
npx wrangler r2 bucket create 275-carnell-drive
```

### 4. Populate R2 with 3D Assets & Model Data

Upload the initial asset directory to R2. For initial setup (large ~500 MB upload), upload key directories recursively:

```bash
# Upload JS engine files
for f in assets/js/*.js; do
  npx wrangler r2 object put "275-carnell-drive/assets/js/$(basename $f)" --file "$f" --content-type "application/javascript; charset=utf-8" --remote
  npx wrangler r2 object put "275-carnell-drive/js/$(basename $f)" --file "$f" --content-type "application/javascript; charset=utf-8" --remote
done

# Upload HTML entry point
npx wrangler r2 object put 275-carnell-drive/index.html --file assets/index.html --content-type "text/html; charset=utf-8" --remote
npx wrangler r2 object put 275-carnell-drive/assets/index.html --file assets/index.html --content-type "text/html; charset=utf-8" --remote

# Upload WebGL vendors (Draco/Basis decoders)
npx wrangler r2 object put 275-carnell-drive/webgl-vendors/three/0.151.3/libs/basis/basis_transcoder.js --file assets/webgl-vendors/three/0.151.3/libs/basis/basis_transcoder.js --content-type "application/javascript" --remote
npx wrangler r2 object put 275-carnell-drive/webgl-vendors/three/0.151.3/libs/basis/basis_transcoder.wasm --file assets/webgl-vendors/three/0.151.3/libs/basis/basis_transcoder.wasm --content-type "application/wasm" --remote
npx wrangler r2 object put 275-carnell-drive/webgl-vendors/three/0.151.3/libs/draco/gltf/draco_wasm_wrapper.js --file assets/webgl-vendors/three/0.151.3/libs/draco/gltf/draco_wasm_wrapper.js --content-type "application/javascript" --remote
npx wrangler r2 object put 275-carnell-drive/webgl-vendors/three/0.151.3/libs/draco/gltf/draco_decoder.wasm --file assets/webgl-vendors/three/0.151.3/libs/draco/gltf/draco_decoder.wasm --content-type "application/wasm" --remote
```

### 5. Configure GitHub Repository Secrets

To enable automated deployments via GitHub Actions, add these two secrets in your GitHub repository (**Settings → Secrets and variables → Actions → New repository secret**):

1. **`CLOUDFLARE_API_TOKEN`**:
   - Go to [Cloudflare API Tokens](https://dash.cloudflare.com/profile/api-tokens).
   - Create a token with **Edit Cloudflare Workers** and **R2 Storage Write** permissions.
2. **`CLOUDFLARE_ACCOUNT_ID`**:
   - Found in your Cloudflare Dashboard URL or right sidebar on the Workers & Pages page.

---

## Deployment Workflow

### Automatic Deployment (Recommended)

Deployment is **100% automated via GitHub Actions**. You do not need to run manual deploy commands.

Simply push your changes to `main`:

```bash
git add -A
git commit -m "Update site feature"
git push origin main
```

The GitHub Action workflow will automatically:
1. Validate Node 22 environment & checkout code
2. Deploy the updated `worker.js` script to Cloudflare Worker
3. Sync updated `index.html` and `showcase-internal.js` code files to R2 in **~10 seconds**

### Manual Deployment (CLI Fallback)

If you ever need to manually deploy from your local terminal:

```bash
# Deploy worker script
npx wrangler deploy

# Upload updated code files to R2
npx wrangler r2 object put 275-carnell-drive/index.html --file assets/index.html --content-type "text/html; charset=utf-8" --remote
npx wrangler r2 object put 275-carnell-drive/assets/index.html --file assets/index.html --content-type "text/html; charset=utf-8" --remote
npx wrangler r2 object put 275-carnell-drive/assets/js/showcase-internal.js --file assets/js/showcase-internal.js --content-type "application/javascript; charset=utf-8" --remote
```

---

## Local Development

For instant local testing without deploying:

```bash
# Start local Python dev server (runs on http://127.0.0.1:8080)
python3 dev-server.py

# Open in browser
open "http://127.0.0.1:8080/?m=vUb5e71k91Q"
```

---

## Engine Patches & Fixes

The static Matterport Showcase JS engine was patched to operate self-hosted without contacting `my.matterport.com`:

| Patch / Fix | Description & Rationale |
|:---|:---|
| **URL Rewriting (`worker.js`)** | Rewrites CDN URLs (`cdn-*.matterport.com`, `static.matterport.com`) to origin to prevent CORS blocking. |
| **Location-Specific Links (`ss`, `sr`)** | Patched `getStartingPose()` in `showcase-internal.js` to lazy-evaluate starting sweep parameters when `sweepData` is ready, preserving custom deep links (e.g. `?m=vUb5e71k91Q&sr=-1.91,1&ss=40`). |
| **Sweep Activation Tagging** | Added `"showcase"` and `"vr"` tags to sweeps so all 66 camera panoramas are enabled and navigation works seamlessly. |
| **Floor Height Null Safety** | Patched `getClosestFloorAtHeight` in `showcase-internal.js` to prevent renderer crashes on boundary transitions. |
| **GraphQL State Override** | Overrode model publication state to `"active"` to bypass registration checks. |

---

## File Structure Overview

```
275-carnell-drive/
├── .github/
│   └── workflows/
│       └── deploy.yml      # Automated GitHub Actions deployment workflow
├── worker.js              # Cloudflare Worker script (URL rewriting + routing)
├── wrangler.toml           # Cloudflare deployment & custom domain config
├── dev-server.py           # Local Python dev server
├── package.json
└── assets/
    ├── index.html          # Main HTML entry point
    ├── css/                # Stylesheets
    ├── js/                 # Patched Showcase 3D Engine JS
    │   ├── showcase-internal.js  # Main engine logic
    │   ├── 65.js                 # TiledPanoRenderer
    │   └── 321.js                # Camera navigation
    ├── webgl-vendors/      # Draco/Basis decoders
    ├── api/                # Cached GraphQL & player API responses
    └── models/             # 3D mesh tiles, textures, panoramic tiles
```
