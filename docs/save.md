# Save Process

## Overview

Every mutation (add, edit, delete card or folder) calls `DataManager.save()`.
The save pipeline has five layers to ensure data is never lost.

---

## Step 1 — User taps Save

`DataManager.addCard()` (or `updateCard`, `deleteCard`, `addFolder`, etc.)
modifies the in-memory `_data` array then calls `save()`.

---

## Step 2 — `save()` — immediate backup + debounce

```
save() called
  │
  ├─ localStorage.setItem(...)      ← instant, synchronous backup
  │
  └─ clearTimeout + setTimeout 300ms ──→ _doSave()
```

- **localStorage** is written synchronously on every call — data is safe
  before any network request is made.
- **300 ms debounce** collapses rapid successive saves (e.g. star + edit
  in quick succession) into a single network request.

---

## Step 3 — `_doSave(attempt)` — fetch with retry

```
POST /api/data?_=<timestamp>   (cache: 'no-store')
  │
  ├─ 200 OK ──→ showToast("✓ Saved")            ✅ done
  │
  ├─ non-200 or network error
  │     ├─ attempt < 3 ──→ wait (600ms × attempt) ──→ retry _doSave()
  │     └─ attempt = 3 ──→ showToast("✗ Save failed")   ❌ give up
```

- `?_=Date.now()` cache-busts every request so no browser or proxy
  returns a cached 304 response.
- `cache: 'no-store'` is an additional fetch-level instruction to bypass
  the browser cache entirely.
- Up to **3 attempts** with **600 ms / 1200 ms backoff** handle transient
  server or network hiccups without user intervention.
- Each retry logs a warning to the browser console for debugging.

---

## Step 4 — Server writes the file (`server.py`)

```
Receive POST body
  │
  ├─ Parse JSON — return 400 if invalid
  │
  ├─ Acquire _file_lock (thread lock)
  │
  ├─ Write to data.json.tmp
  │
  └─ os.replace(tmp → data.json)    ← atomic rename, no corruption risk
```

- The thread lock prevents concurrent requests from corrupting the file.
- Writing to a `.tmp` file first and then renaming is atomic on Linux —
  the live `data.json` is never left in a partial state.

---

## Step 5 — Page unload / refresh

`window.beforeunload` fires `flushSync()`:

```
flushSync()
  │
  ├─ clearTimeout(_saveTimer)       ← cancel any pending debounce
  │
  └─ navigator.sendBeacon('/api/data?_=<timestamp>', blob)
```

`sendBeacon` is a fire-and-forget request the browser guarantees to
complete even as the page unloads, covering the case where the user
refreshes during the 300 ms debounce window.

---

## Safety net summary

| Layer | Protects against |
|---|---|
| localStorage (instant) | Page crash before fetch fires |
| Debounce 300 ms | Rapid changes causing request conflicts |
| Retry × 3 with backoff | Transient server / network hiccups |
| `sendBeacon` on unload | Refresh during the debounce window |
| Atomic `os.replace` on server | File corruption if server crashes mid-write |

---

## Data file location

| Environment | Path |
|---|---|
| Local (default) | `web/data.json` next to `server.py` |
| VPS (persistent) | `/var/lib/flashcards/data.json` (set via `DATA_FILE` env var) |
| Render | `web/data.json` baked into git, ephemeral on server |
