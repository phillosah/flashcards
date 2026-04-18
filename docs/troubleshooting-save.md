# Save Troubleshooting — Knowledge Base

A record of every save-related error encountered, root cause, and fix applied.

---

## Issue 1 — Data lost on browser refresh

**Symptom:** Added a new card, refreshed the browser, card was gone.

**Root cause:** The save fetch was async. If the user refreshed before the
`POST /api/data` response completed, the request was abandoned mid-flight and
the file was never written. Data only existed in memory.

**Fix (v1.6.0):**
- Added `keepalive: true` to the fetch so the browser completes the request
  even after page unload.
- Mirrored every save to `localStorage` synchronously before the fetch fires.
- Added `sendBeacon` on `window.beforeunload` as an additional flush.

---

## Issue 2 — Brave browser not saving (`keepalive` blocked)

**Symptom:** Saves worked in Chrome but not in Brave, even with shields off.

**Root cause:** Brave treats `keepalive: true` on fetch as a tracking/beacon
technique and silently drops the request. No error was raised; the request
simply never reached the server.

**Fix (v1.7.0 → v1.8.0):**
- Removed `keepalive: true` from normal save fetches. Regular fetches do not
  need it — `keepalive` is only useful on page unload.
- `sendBeacon` on `beforeunload` (in `flushSync`) retained for unload
  coverage.

---

## Issue 3 — Page load shows incorrect data (304 on GET)

**Symptom:** Opening the app in Brave showed stale data that did not match
`data.json`. The server was never fetched — the browser served a cached
response.

**Root cause:** Brave cached the `GET /api/data` response and returned
`304 Not Modified` on subsequent page loads. The server's original
`Cache-Control: no-cache` header was insufficient — `no-cache` still allows
the browser to store a cached copy and revalidate it (which can result in 304).

**Fix (v1.8.0):**
- Changed server response headers to
  `Cache-Control: no-store, no-cache, must-revalidate, max-age=0`
  plus `Pragma: no-cache` and `Expires: 0`.
- Added `?_=Date.now()` timestamp to every GET and POST request URL so no
  cache layer can ever match a prior response.
- Added `cache: 'no-store'` to the fetch options on both GET and POST.

---

## Issue 4 — POST returning 304 (Brave caching saves)

**Symptom:** Saving a card in Brave showed no error but data was not written.
Network tab showed `POST /api/data` returning `304 Not Modified`.

**Root cause:** Brave (and in some configurations, Nginx proxy caching) cached
the first successful `POST /api/data` response and returned that cached 304
for subsequent POST requests — without sending the request body to the server.
The file was therefore never updated.

**Fix (v1.8.0):** Same as Issue 3 — `?_=Date.now()` on the POST URL and
`cache: 'no-store'` on the fetch.

---

## Issue 5 — 502 Bad Gateway on save

**Symptom:** Save toast showed `✗ Save failed (502)`. Data not written.

**Root cause:** Nginx received the POST but the Python backend crashed or
timed out while handling the request. Root cause was a
`PermissionError: [Errno 13] Permission denied: '/srv/flashcards/web/data.json.tmp'`.

The service user (`webapps`) did not have write permission on the
`/srv/flashcards/web/` directory. Creating the `.tmp` file requires write
permission on the directory itself, not just the file.

Additionally, the `DATA_FILE` environment variable was not being applied from
the systemd service, so the server was writing to the default path
(`/srv/flashcards/web/data.json`) instead of the intended persistent path
(`/var/lib/flashcards/data.json`).

**Fix:**
```bash
# Grant write access to the directory
sudo chown webapps:webapps /srv/flashcards/web
sudo chown webapps:webapps /srv/flashcards/web/data.json

# Or, preferred — use persistent path outside the repo
sudo mkdir -p /var/lib/flashcards
sudo chown webapps:webapps /var/lib/flashcards
sudo cp /srv/flashcards/web/data.json /var/lib/flashcards/data.json

# Set DATA_FILE in systemd service
sudo systemctl edit --full flashcards
# Add: Environment=DATA_FILE=/var/lib/flashcards/data.json
sudo systemctl daemon-reload && sudo systemctl restart flashcards
```

**Verify the active data file path:**
```bash
curl http://localhost:8000/api/ping
# "data_file" field shows what the server is actually using
```

---

## Issue 6 — Save failures were silent (no error feedback)

**Symptom:** Saves failed without any indication to the user. The `.catch()`
handler only fired on network errors; HTTP error responses (4xx, 5xx) resolved
the promise normally with `res.ok = false`, which was not checked.

**Fix (v1.7.0):**
- Added `res.ok` check in `.then()`.
- Added green `✓ Saved` toast on success and red `✗ Save failed (status)` on
  any error, visible immediately after every save attempt.
- Server error body logged to the browser console for diagnosis.

---

## Issue 7 — Inconsistent saves on both browsers

**Symptom:** Saving a card worked sometimes but not others, randomly, on both
Chrome and Brave.

**Root cause:** Two compounding issues:
1. No retry logic — any transient server hiccup (Nginx timeout, slow disk
   write, brief network blip) permanently dropped the save.
2. The `_saving` / `_pendingSave` flag approach only queued one pending save;
   rapid changes could race and overwrite each other.

**Fix (v1.9.0):**
- Replaced `_saving` flag with a **300 ms debounce** so rapid successive saves
  collapse into one request.
- Added **up to 3 retries** with **600 ms / 1200 ms backoff** on any failure
  (network error or non-200 response).
- Each retry logged to the browser console with attempt number and error.

---

## Issue 8 — localStorage shadowing server data after failed save

**Symptom:** After a failed save (card not in `data.json`), refreshing the
page still showed the new card. The app appeared correct but was lying —
it was displaying stale `localStorage` data, not real server data.

**Root cause:** `DataManager.save()` always wrote to `localStorage` before
the fetch, as a crash backup. `DataManager.init()` fell back to `localStorage`
whenever the server returned a non-200 response. After a failed save the
sequence was:

1. `save()` → `localStorage` updated, fetch fails → file NOT written
2. Refresh → `GET /api/data` returns server error → `init()` falls back to
   `localStorage` → user sees unsaved entry

The fallback was too broad — it triggered on any server error, not just
genuine network outages.

**Fix (v1.10.0):**
- After a successful `GET /api/data`, `localStorage` is immediately cleared
  (`localStorage.removeItem`). The server is the single source of truth.
- `localStorage` fallback in `init()` now only activates on a genuine network
  error (server completely unreachable). HTTP error responses result in empty
  data, not stale local data.

---

## Diagnostic commands (VPS)

```bash
# Watch live server logs while triggering a save
sudo journalctl -u flashcards -f

# Confirm which data file the server is using
curl http://localhost:8000/api/ping

# Check file permissions
ls -la /var/lib/flashcards/
ls -la /srv/flashcards/web/

# Check SELinux denials
sudo ausearch -m avc -ts recent | tail -30

# Check Nginx error log
sudo tail -50 /var/log/nginx/error.log
```
