# app_gpt2_phase2.py (FIXED)
import os, json, uuid
from flask import request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

from app_gpt2 import app  # import the existing Flask app

from agents.schema_gpt2 import FLOORPLAN_SCHEMA
from agents.router_gpt2 import route_circuit, to_svg

try:
    from openai import OpenAI
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY","")) if os.getenv("OPENAI_API_KEY") else None
except Exception:
    openai_client = None

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
OUT_DIR = os.path.join(DATA_DIR, "outputs")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)

def _mock_floorplan():
    return {
        "units":"mm","scale":1.0,
        "rooms":[{"id":"r1","name":"Room","polygon":[{"x":100,"y":100},{"x":500,"y":100},{"x":500,"y":400},{"x":100,"y":400}]}],
        "panels":[{"id":"p1","type":"panel","point":{"x":120,"y":120}}],
        "symbols":[
            {"id":"s1","type":"light","label":"Light 1","room_id":"r1","bbox":{"x":200,"y":180,"w":12,"h":12},"port":{"x":206,"y":186}},
            {"id":"s2","type":"light","label":"Light 2","room_id":"r1","bbox":{"x":360,"y":220,"w":12,"h":12},"port":{"x":366,"y":226}},
            {"id":"s3","type":"switch","label":"SW1","room_id":"r1","bbox":{"x":120,"y":210,"w":10,"h":10},"port":{"x":125,"y":215}}
        ]
    }

@app.post("/api/plan/understand")
def plan_understand():
    f = request.files.get("file")
    if not f:
        return jsonify(success=False, error="No file"), 400
    name = secure_filename(f.filename or f"plan-{uuid.uuid4()}.pdf")
    path = os.path.join(UPLOAD_DIR, name)
    f.save(path)

    # TODO: real vision with OpenAI Structured Outputs; fallback for now
    result = _mock_floorplan()

    pid = str(uuid.uuid4())[:8]
    out_json = os.path.join(OUT_DIR, f"{pid}-floorplan.json")
    with open(out_json, "w") as fh:
        json.dump(result, fh)

    return jsonify(success=True, project_id=pid, floorplan=result, floorplan_url=f"/phase2/download/{os.path.basename(out_json)}")

@app.post("/api/plan/route")
def plan_route():
    data = request.get_json(force=True)
    floorplan = data.get("floorplan") or _mock_floorplan()
    panels = floorplan.get("panels") or []
    syms = floorplan.get("symbols") or []
    if not panels or not syms:
        return jsonify(success=False, error="Missing panels or symbols"), 400

    src = panels[0]["point"]
    targets = [s["port"] for s in syms if s.get("type","").startswith("light")]
    circuits = route_circuit(src, targets, wire="14/2")
    markup = {"circuits": circuits, "symbols": syms}
    svg = to_svg(markup)
    svg_name = f"{uuid.uuid4().hex[:8]}.svg"
    with open(os.path.join(OUT_DIR, svg_name), "w") as fh:
        fh.write(svg)
    return jsonify(success=True, markup=markup, svg_url=f"/phase2/download/{svg_name}")

@app.get("/phase2/download/<path:fname>")
def phase2_download(fname):
    return send_from_directory(OUT_DIR, fname, as_attachment=False)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
