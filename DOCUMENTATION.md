# FlashCards — Documentation

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Deploying to Render](#deploying-to-render)
4. [VPS Deployment](#vps-deployment)
5. [Project Structure](#project-structure)
6. [Architecture](#architecture)
7. [Data Models](#data-models)
8. [Data Storage](#data-storage)
9. [Speech & Pronunciation](#speech--pronunciation)
10. [Views](#views)
11. [User Guide](#user-guide)
12. [Backup & Restore](#backup--restore)
13. [Extending the App](#extending-the-app)
14. [Troubleshooting](#troubleshooting)

---

## Overview

FlashCards is a browser-based vocabulary study app. Cards are organised into folders. Each folder has its own language pair and colour settings. Cards support text entry, automatic pronunciation generation, text-to-speech playback, 3D flip animation, and an autoplay mode for hands-free review.

The app is a single self-contained HTML file (`web/index.html`) with no framework, build step, or external dependencies. A lightweight Python server (`web/server.py`) enables persistent local file storage.

---

## Quick Start

### With local server (recommended)

Double-click `web/start.bat`, or run manually:

```bash
cd web
python server.py
```

Opens `http://localhost:8000` in your browser. Data is saved to `web/data.json` on disk.

**Options:**

```bash
python server.py --port 3000
python server.py --file "C:\Users\Philip\OneDrive\data.json"
```

### Without the server

Open `web/index.html` directly in a browser (double-click). Data is stored in the browser's `localStorage`. Note that `localStorage` data is separate from server-file data — use Export/Import to transfer between them.

---

## Deploying to Render

Render is a cloud hosting platform that can run the Python server publicly. A `render.yaml` blueprint at the project root automates the entire setup.

Data is stored in `web/data.json`, which is committed to git. The web version always reflects whatever was last pushed — no persistent disk required.

> **Running on a VPS?** See the [VPS Deployment](#vps-deployment) section below for persistent storage setup.

### Prerequisites

- A [Render](https://render.com) account (free tier works).
- The project pushed to a GitHub or GitLab repository.

### Steps

1. **Push to GitHub**

   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/YOUR_USERNAME/flashcards.git
   git push -u origin main
   ```

2. **Create a new Web Service on Render**
   - Go to [dashboard.render.com](https://dashboard.render.com) → **New** → **Web Service**.
   - Connect your GitHub repo.
   - Render detects `render.yaml` automatically and pre-fills all settings.

3. **Deploy**
   - Click **Create Web Service**.
   - Render installs Python and starts `python server.py`.
   - Your app is live at `https://flashcards.onrender.com` (or similar).

### What `render.yaml` configures

| Setting | Value | Notes |
|---|---|---|
| Runtime | Python | Auto-detected from `requirements.txt` |
| Root directory | `web/` | Server and HTML files |
| Start command | `python server.py` | Reads `PORT` env var from Render |
| `DATA_FILE` env var | `data.json` | Resolved relative to `web/` — comes from git |

### Data sync workflow

Enter data locally, then push to sync the web version:

```bash
# After adding/editing cards locally:
git add web/data.json
git commit -m "update data"
git push
```

Render automatically redeploys on push. The web version then serves the updated `data.json` from git. Any edits made directly on the web version are ephemeral — they are lost on the next deploy. Treat the local copy as the source of truth.

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `PORT` | Set by Render | Server listen port — do not override |
| `DATA_FILE` | `data.json` | Path to the JSON data file (relative to `web/`) |

To change the data file path, edit `DATA_FILE` in the Render dashboard under **Environment**.

---

## VPS Deployment

For a Rocky Linux (or similar) VPS with persistent storage, the data file lives **outside** the git repo so that `git pull` never overwrites live data.

### Data file setup (one time)

```bash
sudo mkdir -p /var/lib/flashcards
sudo chown webapps:webapps /var/lib/flashcards
# Seed with the repo's starting data
sudo cp /srv/flashcards/web/data.json /var/lib/flashcards/data.json
```

### systemd service

Set `DATA_FILE` to the persistent path in `/etc/systemd/system/flashcards.service`:

```ini
[Service]
Environment=DATA_FILE=/var/lib/flashcards/data.json
```

Reload after editing:

```bash
sudo systemctl daemon-reload
sudo systemctl restart flashcards
```

### Updating the app

`scripts/update.sh` pulls code and restarts the service. Because the data file is outside the repo, it is never touched by `git pull`.

```bash
bash /srv/flashcards/scripts/update.sh
```

### Backup live data

```bash
cp /var/lib/flashcards/data.json ~/flashcards_backup_$(date +%F).json
```

### Environment variables

| Variable | Value | Description |
|---|---|---|
| `PORT` | Set by Render / systemd | Server listen port |
| `DATA_FILE` | `/var/lib/flashcards/data.json` | Persistent data path outside git repo |

---

## Project Structure

```
FlashCards/
├── web/
│   ├── index.html              ← The entire app (HTML + CSS + JS)
│   ├── server.py               ← Python server (local + Render)
│   ├── data.json               ← All card data (committed to git, synced to Render)
│   └── start.bat               ← Double-click to launch locally
├── render.yaml                 ← Render deploy blueprint
├── requirements.txt            ← Python deps (stdlib only; signals Python to Render)
└── DOCUMENTATION.md
```

---

## Architecture

The app is a single-page application with no framework. All logic is vanilla JavaScript.

```
index.html
├── DataManager          ← Load/save folders and cards
│   ├── Server mode      ← GET/POST /api/data → data.json
│   └── Fallback mode    ← localStorage (file:// or server unreachable)
├── Speech               ← Web Speech API (TTS)
├── Router               ← state.view drives which screen renders
└── Views (render fns)
    ├── renderMain()     ← Folder list
    └── renderFolder()   ← Card navigation
        └── Modals
            ├── showCardEdit()        ← Add / edit a single card
            ├── showCardEditList()    ← Bulk card management
            ├── showFolderSettings()  ← Language & colour config
            ├── showAutoplay()        ← Full-screen autoplay
            └── showBackupDialog()    ← Export / import
```

**State flow:**

1. `DataManager` holds the in-memory array of folders as the single source of truth.
2. Every mutation (add, update, delete) calls `DataManager.save()` immediately.
3. In server mode, `save()` POSTs the full JSON to `/api/data` (debounced, with `localStorage` fallback on failure).
4. After any mutation the active view re-renders by calling `render()`.

---

## Data Models

All data is stored as plain JSON objects.

### `FlashCard`

| Property | Type | Default | Description |
|---|---|---|---|
| `id` | string (UUID) | auto | Unique identifier |
| `front` | string | `""` | Text shown on the front of the card |
| `back` | string | `""` | Translation / meaning shown on the back |
| `frontPronunciation` | string | `""` | Cached romaji for the front text |
| `starred` | boolean | `false` | Marks the card for additional revision |
| `createdAt` | ISO 8601 string | now | Creation timestamp |

### `FolderSettings`

| Property | Type | Default | Description |
|---|---|---|---|
| `frontLanguage` | string (BCP-47) | `"ja-JP"` | Language for card fronts |
| `backLanguage` | string (BCP-47) | `"en-US"` | Language for card backs |
| `frontColorHex` | string | `"#1B4F72"` | Hex colour for the front face |
| `backColorHex` | string | `"#1E8449"` | Hex colour for the back face |

### `Folder`

| Property | Type | Default | Description |
|---|---|---|---|
| `id` | string (UUID) | auto | Unique identifier |
| `name` | string | — | Display name |
| `cards` | `FlashCard[]` | `[]` | Ordered list of flash cards |
| `settings` | `FolderSettings` | defaults above | Language and colour configuration |
| `createdAt` | ISO 8601 string | now | Creation timestamp |

---

## Data Storage

The app automatically detects how it was opened and chooses the right storage backend.

### Server mode (`http://localhost`)

When opened via `server.py`, all reads and writes go through the server API:

| Endpoint | Method | Description |
|---|---|---|
| `/api/data` | `GET` | Returns the full JSON file contents |
| `/api/data` | `POST` | Validates and writes the JSON file |

The default data file is `web/data.json`. Override with `--file`:

```bash
python server.py --file "C:\Users\Philip\Dropbox\data.json"
```

Placing the file in a cloud-synced folder (OneDrive, Dropbox, etc.) syncs data across machines.

If the server becomes unreachable mid-session, saves automatically fall back to `localStorage` so no data is lost.

### Standalone mode (`file://`)

When `index.html` is opened directly, data is stored in `localStorage` under the key `flashcards_data`. Limit is ~5 MB per browser origin, which is sufficient for thousands of text cards.

**Important:** `localStorage` is scoped to the origin. Data from `file://` is not visible at `http://localhost:8000` and vice versa.

### JSON format

```json
[
  {
    "id": "...",
    "name": "JLPT N5",
    "createdAt": "2026-03-26T10:00:00Z",
    "settings": {
      "frontLanguage": "ja-JP",
      "backLanguage": "en-US",
      "frontColorHex": "#1B4F72",
      "backColorHex": "#1E8449"
    },
    "cards": [
      {
        "id": "...",
        "front": "みず",
        "back": "water",
        "frontPronunciation": "mizu",
        "starred": false,
        "createdAt": "2026-03-26T10:05:00Z"
      }
    ]
  }
]
```

---

## Speech & Pronunciation

### Text-to-speech

Uses the browser's `window.speechSynthesis` (Web Speech API). Speech rate is 0.8x. Voice selection is automatic based on the folder's BCP-47 language code. Voice availability varies by OS and browser.

### Supported languages

| Code | Language |
|---|---|
| `ja-JP` | Japanese |
| `en-US` | English (US) |
| `en-GB` | English (UK) |
| `zh-CN` | Chinese (Simplified) |
| `zh-TW` | Chinese (Traditional) |
| `ko-KR` | Korean |
| `fr-FR` | French |
| `de-DE` | German |
| `es-ES` | Spanish |
| `it-IT` | Italian |
| `pt-BR` | Portuguese |
| `ru-RU` | Russian |
| `ar-SA` | Arabic |
| `hi-IN` | Hindi |
| `th-TH` | Thai |
| `vi-VN` | Vietnamese |

### Pronunciation generation

A built-in kana-to-romaji converter runs automatically 2 seconds after you stop typing on a Japanese card front. It covers:

- All basic hiragana and katakana
- Dakuten / handakuten variants (ga, za, da, ba, pa series)
- Combination characters (kya, sha, cha, nya, etc.)
- Double consonants (っ/ッ)
- Long vowel mark (ー)

**Limitation:** Kanji is not converted to romaji — use the speaker button to hear the pronunciation via TTS. Chinese pinyin generation is also not available; use TTS.

---

## Views

### Main view (folder list)

- Lists all folders with coloured icon, name, language pair, and card count.
- **Search bar** filters folders by name.
- **Folder+ button** (top right) creates a new folder.
- **Backup button** (top left) opens the export/import dialog.
- **Trash icon** on each row deletes the folder.
- **Gear icon** on each row opens Folder Settings.

### Folder view (card navigation)

- Shows cards one at a time with a counter (`1 / 10`) above the card.
- **Left/right arrow buttons** on either side navigate between cards.
- **Swipe** left or right (touch or mouse drag, 80 px threshold) to navigate.
- **Navigation dots** at the bottom show position (capped at 20).
- **Tap the card** to flip it (3D CSS animation, 0.4 s).
- **Left header buttons:** ← back to folder list, ⊞ open card summary table.
- **Right toolbar buttons:**

| Icon | Action |
|---|---|
| ▶ | Autoplay in card order |
| ⇄ | Autoplay in random/shuffled order |
| ▶★ | Autoplay starred cards only (random order) |
| ✏ | Open card edit list |
| + | Add a new card |

- **Keyboard:** ← / → arrow keys navigate cards.

### Card flip

Both card faces are rendered in a CSS 3D flip container:

- **Front face** — language badge, card text, optional pronunciation row with speaker button, ★ star button (bottom left), "tap to flip" hint (bottom right).
- **Back face** — language badge, translation text, ★ star button (bottom left), speaker button (bottom right).

The star button marks the card for additional revision. Tapping it toggles between an outline star (not starred) and a filled gold star (starred). The star state is the same on both faces and persists with the card.

Card resets to front side whenever you navigate to a different card.

### Autoplay

Full-screen mode for hands-free review. Three entry points from the folder toolbar:

| Button | Cards played |
|---|---|
| ▶ | All cards in folder order |
| ⇄ | All cards in random order |
| ▶★ | Starred cards only, random order |

**Playback flow:**
1. First card's front text is spoken aloud on entry.
2. Timer fires every **3 seconds**.
3. First tick: card flips to back, back text is spoken.
4. Second tick: advances to next card.

The counter shows **★ 1 / 5** when playing starred cards only.

| Control | Action |
|---|---|
| ← | Previous card |
| ▶ / ⏸ | Play / pause |
| → | Next card |
| ⇄ | Re-shuffle and restart |

Tap the card to flip manually. Swipe left/right (60 px threshold) to navigate.

### Folder Settings modal

- Edit folder name.
- Front and back language pickers (16 languages).
- Front and back colour pickers with live preview.
- Cancel / Save.

### Card Edit modal

Used for both adding and editing a card:

- Front text area (label shows the front language).
- Pronunciation row (appears automatically after 2 s idle for Japanese kana): shows the romaji text and a speaker button to hear it aloud.
- Back text area (label shows the back language).
- Cancel / Save (Save disabled if front is empty).

### Card Summary modal

Opened via the ⊞ button in the folder header (top left, next to the back arrow).

- Displays all cards in a scrollable table with columns: **#**, **Front**, **Pronunciation**, **Back**.
- **Search bar** at the top filters rows by matching text in the front or back column (case-insensitive). The `#` column always shows the card's original position in the folder.
- Tap **Done** to close.

### Card Edit List modal

- Scrollable list of all cards showing front and back text.
- Tap any row to open the Card Edit modal for that card.
- Trash icon on each row deletes the card.

---

## User Guide

### Create a folder

1. Tap the **folder+ icon** (top right of main screen).
2. Type a name and tap **Create**.

### Configure a folder

Tap the **gear icon** on any folder row:
- Set the **front language** (the language you are learning; default: Japanese).
- Set the **back language** (your reference language; default: English US).
- Choose colours for the front and back card faces.
- Tap **Save**.

### Add a card

1. Open a folder, then tap **+** in the header.
2. Enter the front text.
3. Wait 2 seconds — romaji appears automatically for Japanese kana. Tap the speaker to hear it.
4. Enter the back text (translation / meaning).
5. Tap **Save**.

### Study cards

- Open a folder.
- **Tap the card** to flip between front and back.
- Use the **← → buttons** (or swipe, or arrow keys) to move between cards.
- Tap the **speaker icon** on either face to hear the text read aloud.
- Tap the **★ star button** (bottom of card) to mark a card for extra revision. Tap again to unstar.

### Edit or delete a card

- Tap the **pencil icon** in the folder header to see all cards.
- Tap a card row to edit it.
- Tap the trash icon on a row to delete it.

### Autoplay

| To play… | Tap… |
|---|---|
| All cards in order | **▶** in the folder header |
| All cards shuffled | **⇄** in the folder header |
| Starred cards only | **▶★** in the folder header |

During autoplay, cards auto-flip every 3 seconds. Use the bottom controls to pause, skip forward/back, or re-shuffle. Tap **Done** to exit.

### Mark cards for revision (starring)

Tap the **★** button on the bottom of any card (front or back face) to star it — the star turns gold. Star cards you find difficult or want to review again. Use the **▶★** toolbar button to play only your starred cards in a focused session.

---

## Backup & Restore

Tap the **backup icon** (top left of main screen):

- **Export Backup** — downloads all data as a `.json` file.
- **Import Backup** — opens a file picker; selecting a `.json` file **replaces all current data**.

The JSON format is human-readable and can be opened in any text editor. Always export a backup before importing.

In server mode the live data file (`web/data.json`) is itself a backup-compatible JSON file and can be copied or opened directly.

---

## Extending the App

### Add a language

In `index.html`, add an entry to the `LANGUAGES` array near the top of the `<script>` block:

```js
{ code: 'pl-PL', name: 'Polish' },
```

If the language needs custom pronunciation logic, add a branch in the `getPronunciation` function.

### Change the autoplay interval

Search for `INTERVAL = 3000` in `index.html` and change the value (milliseconds):

```js
const INTERVAL = 5000; // 5 seconds
```

### Change the pronunciation trigger delay

Search for `setTimeout` inside `schedulePron` in `index.html`:

```js
pronTimer = setTimeout(() => { ... }, 2000); // change 2000 ms
```

### Change the server port

```bash
python server.py --port 3000
```

Or edit the default in `server.py`:

```python
parser.add_argument("--port", type=int, default=8000)
```

---

## Troubleshooting

### `start.bat` opens but the browser shows a 404

Ensure Python is on your PATH: open a terminal and run `python --version`. If not found, install Python 3 from [python.org](https://www.python.org).

### Port already in use

```bash
python server.py --port 3001
```

### Data entered via file:// not visible on localhost

Expected — they use separate storage. Export from one and import into the other via the backup button.

### No sound from TTS

- Check system volume.
- Some browsers block audio until the first user interaction — tap the speaker icon manually once.
- Voice availability varies by OS. If a language has no matching voice the utterance is silently skipped.

### Cards not saving (standalone mode)

`localStorage` has a ~5 MB limit. Export a backup, delete unused folders, then reload. This limit does not apply in server mode.

### Server data file location

The server prints the full file path on startup. Default is `web/data.json` next to `server.py`. On Render it is the same `data.json` baked in from git.

### Data edited on the web version not persisting after redeploy

The web version's filesystem is ephemeral — changes survive until the next Render deploy, then reset to whatever is in git. The intended workflow is to enter data locally, then push `web/data.json` to git to update the web version. If you made changes on the web that you want to keep, use **Export Backup** to download the JSON, copy it to your local `web/data.json`, then commit and push.

### Render service crashes on startup

Check the Render logs for the error. The most common cause is the `PORT` env var not being an integer — this is set automatically by Render and should not be overridden manually.

### VPS: save shows "✗ Save failed (502)"

502 means Nginx reached the Python server but the request failed. Check the service logs while triggering a save:

```bash
sudo journalctl -u flashcards -f
```

Common causes:

**Permission denied writing `data.json.tmp`** — the service user lacks write access to the data directory:

```bash
# If using /srv/flashcards/web/data.json
sudo chown webapps:webapps /srv/flashcards/web
sudo chown webapps:webapps /srv/flashcards/web/data.json

# If using /var/lib/flashcards/data.json (recommended)
sudo chown webapps:webapps /var/lib/flashcards
sudo chown webapps:webapps /var/lib/flashcards/data.json
```

Note: the directory itself needs to be owned by the service user because saving creates a `.tmp` file in the same directory before renaming it.

**`DATA_FILE` env var not applied** — verify the running service is using the correct path:

```bash
curl http://localhost:8000/api/ping
# "data_file" field shows the active path
```

If it shows `/srv/flashcards/web/data.json` instead of `/var/lib/flashcards/data.json`, the env var is not set. Edit the service and reload:

```bash
sudo systemctl edit --full flashcards
# Add under [Service]: Environment=DATA_FILE=/var/lib/flashcards/data.json
sudo systemctl daemon-reload && sudo systemctl restart flashcards
```

**SELinux blocking the write** — check for AVC denials:

```bash
sudo ausearch -m avc -ts recent | tail -30
# Fix with:
sudo chcon -t httpd_sys_rw_content_t /var/lib/flashcards/data.json
```
