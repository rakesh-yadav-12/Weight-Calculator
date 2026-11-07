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
"""
import os
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# ---- constants from the formula sheet ----
K = 0.0246615          # weight constant (mild steel)
EQ = 0.6363             # converts (SideA + SideB) of a hollow section into an equivalent OD
DEFAULT_LENGTH_M = 6.0  # standard pipe length used for Total Weight when Length is blank


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
        "length_m": length or None,
        "weight_per_pipe": round(weight_per_pipe, 4) if weight_per_pipe is not None else None,
        "total_weight": round(total_weight, 4) if total_weight is not None else None,
    }


@app.after_request
def no_cache(resp):
    # always fetch fresh HTML/CSS/JS so UI updates show up immediately
    if request.path == "/" or request.path.startswith("/static/"):
        resp.headers["Cache-Control"] = "no-cache, must-revalidate"
    return resp


@app.get("/")
def index():
    return render_template("index.html")


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
    return jsonify(result)


@app.get("/healthz")
def healthz():
    return jsonify(ok=True)


if __name__ == "__main__":
    # host="0.0.0.0" so phones on the same Wi-Fi can open it via your PC's LAN IP
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=os.getenv("FLASK_DEBUG", "0") == "1")
