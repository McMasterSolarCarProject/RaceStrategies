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

- [`solarcar_phone_app`](https://github.com/McMasterSolarCarProject/solarcar_phone_app) integrates with this API, caches profiles, offline lookup, and driver-facing status fields. See [phone app PR #1](https://github.com/McMasterSolarCarProject/solarcar_phone_app/pull/1) for the navigation MVP client work.

## Not included yet

- Real rolling reoptimization from position/velocity/SOC.
- SOC/microcontroller fields in sync contract.
- Durable session persistence.
- Production race-day UI polish.

## Setup

### Backend (this repo)

1. Create and activate a Python venv, then install dependencies:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate          # Windows
   pip install -r requirements.txt
   ```

2. Start the navigation API (keep this terminal open while testing):

   ```bash
   python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
   ```

   Stop with **Ctrl+C** when running offline-fallback tests.

3. **Windows firewall (LAN / physical phone):** allow inbound TCP **8000** on the host running uvicorn (Private network profile is usually enough). Find the host LAN IP with `ipconfig` (e.g. `192.168.1.42`).

### Phone client (sibling repo)

- Clone/build [`solarcar_phone_app`](https://github.com/McMasterSolarCarProject/solarcar_phone_app) per [PR #1](https://github.com/McMasterSolarCarProject/solarcar_phone_app/pull/1).

**Physical phone on the same Wi‑Fi as the backend host** — rebuild with the host LAN IP:

```powershell
./gradlew assembleDebug -PraceStrategiesBaseUrl=http://<LAN-IP>:8000/
```

**Emulator / BlueStacks** — use the Android emulator loopback or the host LAN IP:

- Android emulator: `http://10.0.2.2:8000/`
- BlueStacks or emulator on same PC: `http://10.0.2.2:8000/` or `http://<LAN-IP>:8000/`

## Testing

### Automated

```bash
pytest tests/test_navigation_mvp.py
```

Covers route mapping, advice, profile bundles, session/telemetry flow, sync placeholder, rolling demo sync, and GPS sync-count behavior.

### API smoke (backend running)

```bash
curl http://localhost:8000/api/health

curl -X POST http://localhost:8000/api/sessions ^
  -H "Content-Type: application/json" ^
  -d "{\"route_name\": \"A. Independence to Topeka\"}"

curl -X POST http://localhost:8000/api/sessions/<SESSION_ID>/sync ^
  -H "Content-Type: application/json" ^
  -d "{\"telemetry\": {\"lat\": 39.092185, \"lon\": -94.417077, \"speed_mps\": 10, \"source\": \"demo\"}}"
```

(On bash/macOS, use `\` line continuations and single-quoted JSON.)

### Manual — phone app

- [ ] **Start logging** — session created, telemetry/advice updates.
- [ ] **Test Route Replay** — demo positions advance along the route.
- [ ] **Next** — each tap triggers a demo sync; recommended speeds on current-and-future profile points bump (e.g. **32.19 → 32.20 → 32.21** km/h per sync with the MVP +0.01 km/h placeholder increment).
- [ ] **Rolling sync** — repeated syncs at the same point accumulate the bump on future points.

### Manual — offline fallback

- [ ] With a cached profile on the phone, **stop the backend** (Ctrl+C in the uvicorn terminal).
- [ ] Confirm guidance continues from the last cached profile (no crash; status reflects offline).

### Manual — BlueStacks

- [ ] Use BlueStacks **HD-Adb.exe** (not the standalone Android SDK `adb`) when sideloading or debugging.
- [ ] Point base URL at `http://10.0.2.2:8000/` (or host LAN IP); run create session → sync → offline steps above.

## Future: any-network access (Option B — not in this PR)

Long-term plan: expose a home/race-day PC over the public internet so the phone works off-LAN (cellular, other Wi‑Fi):

1. **DDNS** on the home router (stable hostname → public IP).
2. **Port forward** (e.g. external 443 → host running RaceStrategies API).
3. **HTTPS** termination (reverse proxy or uvicorn TLS) — do not ship plain HTTP over the internet.
4. **In-app backend URL** in `solarcar_phone_app` (build-time or settings) pointing at `https://<your-hostname>/`.

This PR and the current phone MVP target **same-LAN / emulator** only; Option B is a follow-up across infra + phone app configuration.
