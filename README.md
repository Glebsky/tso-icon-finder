# TSO Icon Finder

A lightweight web application for instant search, high-res preview, and export of icons from **The Settlers Online (TSO)**.

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2FGlebsky%2Ftso-icon-finder)

## Deployment on Vercel

The project is fully optimized and ready for immediate deployment on [Vercel](https://vercel.com):
1. Import the repository `Glebsky/tso-icon-finder` in the Vercel Dashboard.
2. No build settings (`Build Command` / `Output Directory`) need to be adjusted — the project is a standalone static web application.
3. Includes `vercel.json` with pre-configured immutable CDN caching headers for all icon assets (`Cache-Control: public, max-age=31536000, immutable`) and recommended security headers.
4. Intermediate build caches and raw documents are excluded via `.vercelignore` for fast, lightweight deployments well within Vercel's Hobby tier file limits.

## Quick Local Start
- Double-click **`run.bat`** (or simply open **`index.html`** in any web browser).
- No web servers, Node.js, or Python installations required — runs entirely client-side in the browser.

## Project Structure
- `index.html` (and `icon_finder.html`) — Responsive UI with zoom controls, categories, fuzzy search, and pagination.
- `icons_data.js` — Optimized catalog containing **9,496 icons** with Russian & English titles, categories, and dimension metadata (~2.7 MB).
- `icons/` — Directory containing individual PNG files (9,500+ files).
- `vercel.json` — Vercel routing, CDN caching, and security header configuration.
- `.vercelignore` — Deployment exclusion list for Vercel.
- `.gitignore` — Git exclusion rules for `.hash_cache/` and local environment files.
- `build_catalog.py` — Python script for building and syncing the icon catalog from game client configs.
- `docs/` — Original game XML configuration schemas and decompiled client scripts.
- `run.bat` — Windows batch launcher for instant local viewing.

## Icon Database (9,496 items)
- **Buildings (BUI)**: 1,562 icons (Bakery, Forester, Smelters, Barracks, Mayor's House, skins, levels, etc.).
- **User Interface (GUI)**: 1,510 icons (Close crosses, action buttons, toolbars, star menu tabs, mail, checkboxes, frames, widgets).
- **Resources & Goods (RES)**: 1,451 icons (Bread, Brew, Pinewood, Granite, Titanium, Saltpeter, Gems, etc.).
- **Merchant Shop (SHI)**: 1,217 icons (Item packs, decorations, bundles, mystery boxes).
- **Achievements (ACH)**: 1,029 icons (Achievements and Facebook event badges).
- **Buffs & Boosters (BUFF)**: 887 icons (Fish Platter, Sushi, Baskets, Zone buffs).
- **Military Units & Settlers (UNI)**: 775 icons (Militia, Cavalry, Cannoneers, Bandits, battle unit icons, Settlers).
- **Adventures (ADN)**: 476 icons (Adventure maps, banners, event teasers, difficulty skull icons).
- **Avatars & Specialists (AVT)**: 464 icons (Generals, Geologists, Explorers, NPCs).
- **Skills (SKL)**: 125 icons (Skill trees for Geologists, Explorers, Generals).
- **Collections (COL)**: Collectibles and conversion recipes.

## Features
1. **Instant Search**:
   - By XML / ActionScript ID: `Bakery`, `Forester`, `Bread`, `DepositWood`, `ProductivityBuffLvl1`.
   - By Russian name: `Пекарня`, `Лесник`, `Хлеб`, `Квас`, `Золото`, `Рыбное блюдо`.
   - By English name: `Pinewood Forester`, `Fish Platter`, `Brew`.
   - By pasted XML snippets: `<Building name="Bakery">`, `<t id="Beer" text="Квас" />`, `iconfilename="icon_bakery.png"`.
   - By resource file path: `icons/buildings/icon_bakery.png`.
2. **Export & Copy**:
   - "Download PNG" button (or press `Enter`).
   - "Copy Image to Clipboard" button (paste directly via `Ctrl+V` into chats, Photoshop, Figma, etc.).
   - "Copy Name (ID)" and "Copy getImageTag code".
3. **Advanced Viewing**:
   - Pixelated crisp zoom from 1x up to 8x with pan support and mouse wheel zoom.
   - Configurable page sizes: 30, 60, 120, 240, 500 or "All icons" on a single page.
   - Quick page jump navigation.
   - Dark and Light theme toggle.
4. **Multilingual (i18n)**:
   - Full support for 4 languages: **English (default)**, **Russian**, **Ukrainian**, and **German**.
   - Quick header switcher with persistent preference (`localStorage`) and query string sync (`?lang=en|ru|uk|de`).
   - Preserves raw untranslated `XML Name / ID` for developer convenience.
5. **PWA & Offline Worker**:
   - Installable Progressive Web App (`manifest.webmanifest`) with thematic Settlers Online dark slate palette (`#0f172a`).
   - Service Worker (`sw.js`) enabling offline browsing, app shell caching, and immutable icon asset storage.
   - Multi-resolution favicons (`.ico`, `.svg`, `32x32`, `16x16`), maskable icons (192x192, 512x512), and Apple Touch Icon.
6. **SEO & Social Previews (Open Graph)**:
   - Full Open Graph and Twitter Cards meta tags.
   - Custom 1200×630 social preview card (`og-image.png`) with crisp icon montages and feature badges.
   - Schema.org `WebApplication` JSON-LD metadata.
