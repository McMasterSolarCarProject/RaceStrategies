## Summary

This PR adds a FastAPI navigation MVP on RaceStrategies so the native Android phone client (`solarcar_phone_app`, sibling repo) can create sessions, sync GPS telemetry, and download route profile bundles for offline target-speed lookup.

Product model:

- Backend/computer owns route/profile generation and future reoptimization.
- Phone stores the full profile locally and maps GPS to target speed from cache when offline.
- When online, phone calls `/sync` for advice and refreshed profiles; connection loss falls back to the last cached profile.

**This repo (RaceStrategies):**

- FastAPI app: health, routes, profile download, sessions, telemetry, and `/api/sessions/{id}/sync`.
- Navigation layer: route mapping from KML/route data, advice builder, static/placeholder profile bundles.
- Rolling sync **placeholder** (not real reoptimization): demo syncs bump `sync_count` and raise recommended/target speeds from the current position forward; live GPS syncs reuse the count without incrementing; `profile_current=false` so the phone always accepts MVP test updates.
- In-memory session store, CORS for dev, readme + dependencies for running uvicorn.
- Removed Capacitor/PWA prototype direction from this repo; phone UI lives only in `solarcar_phone_app`.
- Minor kinematics helpers (`Speed.rps`, `Coordinate` repr) used by navigation/tests.

**Phone client (separate repo — not in this commit):**

- `C:\Code\solarcarnew\solarcar_phone_app` integrates with this API, caches profiles, offline lookup, and driver-facing status fields.

## Not included yet

- Real rolling reoptimization from position/velocity/SOC.
- SOC/microcontroller fields in sync contract.
- Durable session persistence.
- Production race-day UI polish.

## Test plan

- [ ] `pytest tests/test_navigation_mvp.py` — route mapping, advice, profile bundles, session/telemetry flow, sync placeholder and rolling demo sync, GPS sync count behavior.
- [ ] Run backend: `python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000`
- [ ] In `solarcar_phone_app`, point API base URL at host (e.g. `http://10.0.2.2:8000` on BlueStacks/emulator).
- [ ] Manual BlueStacks: create session, online sync, confirm advice and profile cache update.
- [ ] Offline mode: disable network, confirm guidance from last cached profile.
- [ ] Rolling sync demo: repeated demo syncs at same point show cumulative speed bump on current-and-future profile points.
