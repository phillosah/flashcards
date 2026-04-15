# Changelog

## v1.6.0 — 2026-04-15

### Fixed
- **Data loss on refresh** — save now uses `keepalive: true` so the POST completes even if the page is refreshed mid-flight. Every save also mirrors to `localStorage` instantly as a backup. A `sendBeacon` flush fires on `beforeunload` for an additional safety net.

---

## v1.5.0 — 2026-04-15

### Changed
- **Card size** reduced (max-width 360px → 280px) for a more compact layout.

---

## v1.4.0 — 2026-04-15

### Changed
- **Folder name** moved from the header bar into the card area, pinned above the card counter so it is always visible regardless of screen size.

---

## v1.3.0 — 2026-04-13

### Added
- **Card summary table** — new ⊞ button in the folder header (top left, next to back arrow) opens a full card list in table format with columns: #, Front, Pronunciation, Back.
- **Search in summary** — real-time search bar filters table rows by front or back text (case-insensitive); `#` always shows the card's original position.

### Changed
- **Storage** — data file renamed from `flashcards_data.json` to `data.json`. The file is now committed to git and served directly on Render (no persistent disk needed). Local edits → `git push` → Render redeploys with updated data.
- `render.yaml` `DATA_FILE` env var updated to `data.json`.
- Version number displayed on the main screen header.

---

## v1.2.1 — 2026-04-06

### Fixed
- Speaker icon missing in the card edit modal pronunciation row.

---

## v1.2.0 — 2026-04-06

### Added
- **Star button** on cards (front and back faces) — marks a card with a gold star for extra revision. State persists with the card.
- **Starred autoplay** (▶★ button) — plays only starred cards in random order. Counter shows ★ n / total.

---

## v1.1.0 — 2026-04-06

### Added
- **Shuffle autoplay** (⇄ button) — plays all cards in random order alongside the existing in-order autoplay (▶).

---

## v1.0.1 — 2026-04-06

### Fixed
- Use `ThreadingHTTPServer` to handle concurrent browser requests without blocking.
- Atomic file writes (write to `.tmp` then rename) to prevent corruption on crash.
- `DATA_FILE` env var now resolves relative paths against the script directory.
- Storage indicator (☁ server / ⚠ localStorage) added to the main header.

---

## v1.0.0 — 2026-04-06

### Initial release
- Single-file browser app (`web/index.html`) — no framework or build step.
- Folders with per-folder language pair (16 languages) and card colour settings.
- Flash cards with front/back text, 3D flip animation, and swipe navigation.
- Japanese kana → romaji pronunciation auto-generation (2 s after typing stops).
- Text-to-speech playback via Web Speech API.
- Autoplay mode — full-screen hands-free review at 3 s intervals.
- Export / import JSON backup.
- Python server (`web/server.py`) for persistent local file storage; `localStorage` fallback when opened as `file://`.
- Render deployment via `render.yaml` blueprint.
