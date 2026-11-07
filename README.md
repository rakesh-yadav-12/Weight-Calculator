# Pipe Weight Calculator

A small Flask web app for **Shreeji SteelTubes Pvt. Ltd.** that calculates
pipe weight for **Round Pipes** and **Hollow Sections (SHS/RHS)**. All
calculations run on the server in Python (`app.py` -> `calc_weight()`); the
browser only sends the numbers and shows the result.

## Features
- Round Pipe and Hollow Section modes (tap to switch)
- Results appear step by step: OD (or Side A / B) + Thickness -> **Kg/MTR**; add Length -> **Weight/Pipe**; add No. of Pipes -> **Total Weight**
- If Length is blank but No. of Pipes is given, the standard **6.00 m** is used for Total Weight
- Results update live while typing
- Responsive, mobile-friendly UI with an animated background
- Ready to deploy on Render (`render.yaml`, `Procfile`, `gunicorn`)

## Formula
```
Round Pipe     : (OD - Thk) x Thk x 0.0246615 = Kg/MTR
                 Weight/Pipe = Kg/MTR x 6.00

Hollow Section : (mm + mm) x 0.6363 => OD
                 [{(mm + mm) x 0.6363} - Thk] x Thk x 0.0246615 = Kg/MTR
                 Kg/MTR x 6.00 => Weight/Pipe

Total Weight   : Weight/Pipe x No. of Pipes
```

## Run locally
Requires Python 3.9+.
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000 (on the same Wi-Fi, other devices can use `http://<your-PC-IP>:5000`).

## Deploy on Render
1. Push this repo to GitHub (files at the repo root).
2. In Render choose **New + -> Blueprint** and select the repo (reads `render.yaml`),
   or **New + -> Web Service** with:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app --bind 0.0.0.0:$PORT`
   - Health Check Path: `/healthz`
3. Every `git push` to the connected branch redeploys automatically.

Free instances sleep when idle, so the first request after a while can take ~30 s.

## Project structure
```
.
├── app.py             Flask server + calculation logic
├── requirements.txt   Flask, gunicorn
├── render.yaml        Render blueprint
├── Procfile            start command (gunicorn)
├── templates/
│   └── index.html     page markup
└── static/
    ├── style.css      styling and animated background
    └── script.js      reads inputs, calls the API, shows results
```

## API
`POST /api/calculate` (JSON). `mode` is `"round"` (default) or `"hollow"`.
`length` is optional and defaults to 6.00 m when omitted or blank.

Round:
```json
{ "mode": "round", "od": "60", "t": "3.2", "nos": "10" }
```
Hollow:
```json
{ "mode": "hollow", "a": "20", "b": "20", "t": "1.6", "nos": "10" }
```
returns
```json
{ "ok": true, "message": "", "mode": "hollow", "equivalent_od": 25.45,
  "kg_per_metre": 0.9412, "length_m": 6.0, "weight_per_pipe": 5.647, "total_weight": 56.4697 }
```

`GET /healthz` returns `{"ok": true}` for health checks.

## Customizing
- Colours: CSS variables at the top of `static/style.css`
- Title / company name: `templates/index.html`
