"""
Pipe Weight Calculator - standalone Flask app
-----------------------------------------------
Run:  python app.py
Then open:  http://127.0.0.1:5000        (on this PC)
        or  http://<YOUR-PC-LAN-IP>:5000 (on a phone / another device, same Wi-Fi)

All the weight math happens here in Python (see calc_weight below).
The web page just sends the numbers you type and shows back what this
function returns - nothing is calculated in JavaScript.

Formula (exactly as given):
    Round pipe     : (OD - Thk) x Thk x 0.0246615 = Kg/MTR
                      Weight/Pipe = Kg/MTR x 6.00

    Hollow section : (mm + mm) x 0.6363 => OD
                      [{(mm + mm) x 0.6363} - Thk] x Thk x 0.0246615 = Kg/MTR
                      Kg/MTR x 6.00 => Weight/Pipe

    Total Weight   : Weight/Pipe x No. of Pipes

Rate tab (see calc_rate below):
    Kg/MTR x Rate/Kg  => Rate/MTR
    Rate/MTR / 3.281  => Rate/Foot
"""
import os
from flask import Flask, send_from_directory, request, jsonify

# The whole page (HTML + CSS + JS) is one file: public/index.html.
# Calculation runs in the browser for instant results; the /api routes below are kept as a backup.
app = Flask(__name__, static_folder=None)
PUBLIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public")

# ---- constants from the formula sheet ----
K = 0.0246615          # weight constant (mild steel)
EQ = 0.6363             # converts (SideA + SideB) of a hollow section into an equivalent OD
DEFAULT_LENGTH_M = 6.0  # standard pipe length used for Total Weight when Length is blank
FT_PER_M = 3.281        # feet in one metre (Rate/MTR / 3.281 => Rate/Foot)


def to_float(v):
    """Safely turn whatever the browser sent into a positive float, else 0."""
    try:
        n = float(str(v).replace(",", "."))
        return n if n > 0 else 0.0
    except (TypeError, ValueError):
        return 0.0


def to_int(v):
    try:
        n = int(float(str(v).replace(",", ".")))
        return n if n > 0 else 0
    except (TypeError, ValueError):
        return 0


def calc_weight(mode, od, a, b, t, length, nos):
    """
    mode: 'round' or 'hollow'
    od, a, b, t, length: numbers in mm / mm / mm / mm / metres
    nos: whole number of pipes

    Results appear step by step, as the fields are filled:
      OD (or Side A + B) + Thickness  -> Kg/MTR
      ... + Length                    -> Weight/Pipe
      ... + No. of Pipes              -> Total Weight
    (If Length is blank but No. of Pipes is given, the standard 6.00 m is used for the total.)
    """
    ok = False
    msg = ""
    eq_od = 0.0

    if mode == "round":
        eq_od = od
        started = bool(od or t)
        if od and t:
            if t * 2 >= od:
                msg = "Thickness must be less than half of the OD"
            else:
                ok = True
        else:
            msg = "Enter OD and Thickness" if started else "Enter OD and Thickness - Kg/MTR appears instantly"
    else:  # hollow section (SHS / RHS)
        eq_od = (a + b) * EQ
        started = bool(a or b or t)
        if a and b and t:
            if t * 2 >= eq_od:
                msg = "Thickness is too large for this section"
            else:
                ok = True
        else:
            msg = "Enter Side A, Side B and Thickness" if started else "Enter Side A and Side B - OD appears instantly"

    kg_per_m = (eq_od - t) * t * K if ok else 0.0
    weight_per_pipe = kg_per_m * length if (ok and length) else None
    total_weight = kg_per_m * (length or DEFAULT_LENGTH_M) * nos if (ok and nos) else None

    return {
        "ok": ok,
        "message": msg,
        "mode": mode,
        "equivalent_od": round(eq_od, 2) if (mode == "hollow" and a and b) else None,
        "kg_per_metre": round(kg_per_m, 4),
        "_kg_raw": kg_per_m,   # unrounded, used by calc_rate (removed before sending to the browser)
        "length_m": length or None,
        "weight_per_pipe": round(weight_per_pipe, 4) if weight_per_pipe is not None else None,
        "total_weight": round(total_weight, 4) if total_weight is not None else None,
    }


def calc_rate(mode, od, a, b, t, rate_kg):
    """
    Rate tab:  Kg/MTR comes from calc_weight (same formulas as the Weight tab), then
        Kg/MTR x Rate/Kg  => Rate/MTR
        Rate/MTR / 3.281  => Rate/Foot
    Rate/MTR and Rate/Foot appear as soon as Rate/Kg is entered.
    """
    r = calc_weight(mode, od, a, b, t, 0.0, 0)
    kg = r.pop("_kg_raw")
    rate_m = kg * rate_kg if (r["ok"] and rate_kg) else None
    rate_ft = rate_m / FT_PER_M if rate_m is not None else None
    r["rate_per_metre"] = round(rate_m, 4) if rate_m is not None else None
    r["rate_per_foot"] = round(rate_ft, 4) if rate_ft is not None else None
    for k in ("length_m", "weight_per_pipe", "total_weight"):
        r.pop(k, None)
    return r


@app.after_request
def no_cache(resp):
    # browser keeps a copy but re-checks (ETag) so updates still show up; unchanged page = tiny 304 reply
    if request.path == "/":
        resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.get("/")
def index():
    return send_from_directory(PUBLIC, "index.html")


@app.post("/api/calculate")
def api_calculate():
    data = request.get_json(silent=True) or {}
    mode = "hollow" if data.get("mode") == "hollow" else "round"
    od = to_float(data.get("od"))
    a = to_float(data.get("a"))
    b = to_float(data.get("b"))
    t = to_float(data.get("t"))
    length = to_float(data.get("length"))
    nos = to_int(data.get("nos"))

    result = calc_weight(mode, od, a, b, t, length, nos)
    result.pop("_kg_raw", None)
    return jsonify(result)


@app.post("/api/rate")
def api_rate():
    data = request.get_json(silent=True) or {}
    mode = "hollow" if data.get("mode") == "hollow" else "round"
    od = to_float(data.get("od"))
    a = to_float(data.get("a"))
    b = to_float(data.get("b"))
    t = to_float(data.get("t"))
    rate_kg = to_float(data.get("rate"))
    return jsonify(calc_rate(mode, od, a, b, t, rate_kg))


@app.get("/healthz")
def healthz():
    return jsonify(ok=True)


if __name__ == "__main__":
    # host="0.0.0.0" so phones on the same Wi-Fi can open it via your PC's LAN IP
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=os.getenv("FLASK_DEBUG", "0") == "1")
