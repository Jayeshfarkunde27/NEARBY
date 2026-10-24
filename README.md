# ⚡ Nearby: Emergency EV Charging Network

An AI-assisted platform that rescues EV drivers whose battery is about to die mid-journey. Locals with a parking space, a shop or a spare socket register as **charging hosts**. The driver enters their battery %, and the system finds only the hosts they can **safely reach**, ranked by trust, speed and fit.

> Hackathon build: original application, using open-source libraries and Google technologies with disclosure (see [Disclosure](#disclosure)).

---

## 1. The problem

Public chargers are sparse. A driver at 6% battery needs the best charger they can *actually reach*, not the nearest pin on a map. At the same time, thousands of homes and shops have electricity, parking and a place to rest, but no way to offer it.

## 2. The solution

| Side | What they do |
|---|---|
| **Driver** | Saves their vehicle(s) once. In an emergency, enters only battery % and gets reachable hosts ranked by score. |
| **Host** | Registers a charging point (electricity-only, own charger, or plans to invest in one). Team verifies before it goes live. |
| **Platform** | Estimates reachable range with uncertainty, ranks hosts, scores review trust with Gemini, and enforces security rules. |

### Host types
1. **Electricity only:** standard socket, slow top-ups, driver uses own cable.
2. **Host with charger:** AC charger with stated kW.
3. **Host who wants to invest:** platform can recommend a charger (roadmap).

## 3. Key features

- **Reachability model:** usable energy from battery %, battery capacity, battery health, consumption (Wh/km), AC load. Returns a *safe* range plus a low-high band, with a safety factor and a reserve.
- **Minimum-charge calculation:** if a destination distance is given, returns the minutes of charging needed to finish the trip, not a full charge.
- **Smart ranking:** weighted score of host trust rating (35%), charging speed (25%), proximity within safe range (25%), amenities (15%). Filters by connector compatibility and availability.
- **AI review trust scoring:** Gemini estimates the probability a review is fake or unsafe; the host's rating is a trust-weighted average. Only drivers with a *completed booking* can review.
- **Fallback path:** if no host is reachable, the API returns a clear fallback (mobile charging, or slow to extend range).
- **Saved vehicles:** captured at profile creation with "Add vehicle"; the backend loads the vehicle server-side so the client cannot spoof it.
- **Host verification:** hosts start as `pending`; only admins can set `verified`.

## 4. Architecture

```
 Driver / Host (browser, phone)
        │  Google sign-in (Firebase Auth)
        ▼
 Firebase Hosting (frontend/index.html)  ──►  Google Maps JS API
        │ HTTPS + Firebase ID token
        ▼
 Cloud Run: FastAPI (backend/main.py)
   ├─ /recommend  reachability + ranking engine
   ├─ /review     booking check + Gemini trust score
   │        │
   │        └──►  Gemini API (JSON-only classification)
   ▼
 Firestore  (hosts, users/{uid}/vehicles, bookings, reviews)
   rules: firestore.rules
```

## 5. Tech stack

- **Google:** Gemini API, Firebase Auth, Firestore, Firebase Hosting, Cloud Run, Maps JavaScript API
- **Backend:** Python 3.12, FastAPI, Pydantic, firebase-admin, google-genai
- **Frontend:** plain HTML/CSS/JavaScript (ES modules), no build step

## 6. Project structure

```
evcharge/
├── backend/
│   ├── main.py            API: /recommend, /review
│   ├── seed.py            Seeds 12 SIMULATED verified hosts
│   ├── requirements.txt
│   └── Dockerfile         Cloud Run container
├── frontend/
│   └── index.html         Login, vehicles, finder + map, host registration
├── firestore.rules        Security rules
├── firebase.json          Hosting + rules config
└── README.md
```

## 7. Data model

**hosts/{hostId}**: `ownerUid, name, lat, lng` (rounded to 3 decimals, about 110 m), `kw, pricePerKwh, connectors[], amenities[], available, status` (`pending | verified`), `trust_rating, createdAt`
**hosts/{hostId}/private/address**: exact address, readable only by the owner and admins
**users/{uid}/vehicles/{vehicleId}**: `nickname, model, type` (2W/3W/4W), `batteryKwh, whPerKm, healthPct, connectors[]`
**bookings/{id}**: `driverUid, hostUid, hostId, status` (written by backend only)
**reviews/{id}**: `hostId, rating, text, weight, fake_prob, toxic, safety_issue`

## 8. API

### `POST /recommend`
Headers: `Authorization: Bearer <Firebase ID token>`

```json
{ "lat": 18.63, "lng": 73.80, "soc": 8, "vehicleId": "abc123",
  "ac_on": false, "dest_km": 12 }
```
Response:
```json
{ "rangeKm": {"safe": 14.2, "low": 14.4, "high": 18.9},
  "hosts": [{"hostId":"...","name":"...","distKm":3.1,"kw":7.4,"rating":4.6,
             "minutesNeeded":18,"score":0.81,"approxLat":18.63,"approxLng":73.8}],
  "fallback": null }
```

### `POST /review`
Headers: `Authorization: Bearer <token>`. Body: `{ "bookingId", "rating": 1-5, "text" }`.
Rejected unless the caller is the driver of a **completed** booking.

## 9. Security design

- Firebase Auth on every API call; ID token verified server-side.
- Firestore rules: users read/write only their own vehicles; hosts are created as `pending`; only admins verify; bookings and reviews are backend-write-only.
- Exact host address is stored in a private subcollection and not shown publicly; public coordinates are rounded.
- Reviews gated by completed bookings; Gemini output is forced to JSON with a safe default; review text is wrapped as data to resist prompt injection.
- Input validation with Pydantic (ranges and lengths); frontend renders user text with `textContent` to avoid XSS.
- Host agreement and safety self-declaration at registration; human approval is mandatory before listing.

## 10. Setup

### Prerequisites
Python 3.12, Node.js, a Google account, `firebase-tools` (`npm i -g firebase-tools`), gcloud CLI.

### 1. Firebase and Google Cloud
1. Create a Firebase project. Enable **Authentication → Google**, create **Firestore**.
2. Add a **Web app**, copy its config into `CONFIG` in `frontend/index.html`.
3. In Google Cloud, enable **Maps JavaScript API**, create a key restricted to your domains, set `MAPS_KEY`.
4. Create a **Gemini API key** in Google AI Studio.
5. Download a **service account key** (Firebase → Project settings → Service accounts). Keep it private and never commit it.

### 2. Rules
```
firebase login
firebase use --add
firebase deploy --only firestore:rules
```

### 3. Run the backend locally
```
cd backend
pip install -r requirements.txt
export GEMINI_API_KEY=your_key
export GOOGLE_APPLICATION_CREDENTIALS=serviceAccount.json
uvicorn main:app --reload        # http://localhost:8000
python seed.py                   # simulated hosts
```

### 4. Run the frontend locally
Set `BACKEND` to `http://localhost:8000` in `frontend/index.html`, then:
```
cd frontend && python -m http.server 5000
```
Open http://localhost:5000, sign in, add a vehicle, press **Find chargers**.

### 5. Deploy
```
cd backend
gcloud run deploy evcharge --source . --region asia-south1 \
  --allow-unauthenticated --set-env-vars GEMINI_API_KEY=your_key
# put the printed URL in BACKEND (frontend/index.html)
cd .. && firebase deploy --only hosting
```
Use the HTTPS Hosting URL on a phone, since browsers only allow location on HTTPS or localhost.

### Approving a host (current process)
Open Firestore → `hosts` → set `status` to `verified`. An admin dashboard is on the roadmap.

## 11. Measuring performance and efficiency

Record these for the demo (do not quote numbers you have not measured):
- **Range prediction error:** simulate 50 trips with known consumption; report mean absolute error (km) and how often the true range fell within the low-high band.
- **API latency:** p50/p95 of `/recommend` (use `curl -w` or a short script).
- **Time to match:** seconds from pressing Find to a ranked list.
- **Host match rate:** share of requests returning at least one reachable host.

## 12. How it maps to the evaluation criteria

| Criterion | Where it shows |
|---|---|
| Security | Auth-verified API, locked Firestore rules, private addresses, verified hosts, booking-gated reviews, prompt-injection guard |
| Efficiency | Minimum-charge calculation, one query pipeline, lightweight no-build frontend |
| Technology implemented | Reachability model, weighted ranking, AI trust-weighted ratings, fallback path |
| Performance | Measured error and latency (section 11) |
| Google technology | Gemini, Firebase Auth/Firestore/Hosting, Cloud Run, Maps Platform |

## <a id="disclosure"></a>13. Disclosure

- **Original work:** application code written for this hackathon.
- **Open source:** FastAPI, Pydantic, Uvicorn, firebase-admin, google-genai.
- **APIs and services:** Gemini, Firebase, Cloud Run, Google Maps Platform.
- **Simulated data:** the 12 hosts from `seed.py` are simulated (`simulated: true`).
- **Assumptions:** vehicle consumption and battery values in the catalog are sample figures; verify against manufacturer specs. Distance uses straight-line × 1.3 until the Routes API is integrated.

## 14. Known limitations

- Booking flow, payments and check-in/out photos are not built yet, so `/review` has no frontend.
- Host verification is manual (Firestore console).
- Distance is estimated, not routed; no elevation or traffic yet.
- Home-socket safety is self-declared plus team review, not a certified electrical inspection.
- CORS is open for development; restrict it before real use. Keep keys in Secret Manager.

## 15. Roadmap

1. Booking flow with escrow, in-app photo check-in/out, dispute reports
2. Gemini pre-screening of host safety photos (AI recommends, human decides)
3. Google Routes and Elevation APIs for real reachability
4. Admin dashboard for host approval
5. Phone OTP login, FCM push alerts to hosts
6. BigQuery analytics: demand heatmaps and pricing hints for hosts
7. Charger recommendations for hosts who want to invest

## 16. Host agreement (summary)

Hosts sign terms before listing. Responsibility is split by cause: the host for the electrical setup and premises, the driver for their vehicle, cable and misuse. Have the final text reviewed by someone with legal knowledge before real launch.

