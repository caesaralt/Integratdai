# app_gpt2.py
import os, sqlite3, json, uuid, datetime, io, base64
from flask import Flask, request, jsonify, send_from_directory, render_template, url_for
from werkzeug.utils import secure_filename

OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")
try:
    from openai import OpenAI
    openai_client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None
except Exception:
    openai_client = None

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
OUT_DIR = os.path.join(DATA_DIR, "outputs")
DB_PATH = os.path.join(DATA_DIR, "crm.sqlite3")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)

app = Flask(__name__, template_folder="templates", static_folder="static")

@app.route("/")
def home():
    return render_template("template_unified_gpt2.html")

@app.route("/quotes")
def quotes():
    return render_template("template_index_gpt2.html")

@app.route("/crm")
def crm():
    return render_template("template_crm_gpt2.html")

@app.route("/editor/latest")
@app.route("/canvas")
def editor_latest():
    project_id = str(uuid.uuid4())[:8]
    context = {
        "project_id": project_id,
        "project_name": "Untitled Project",
        "tier": "basic",
        "pricing": {
            "lighting": {"basic": 120, "premium": 160, "deluxe": 220},
            "shading": {"basic": 180, "premium": 230, "deluxe": 300},
            "security_access": {"basic": 220, "premium": 270, "deluxe": 350},
            "climate": {"basic": 250, "premium": 320, "deluxe": 400},
            "audio": {"basic": 300, "premium": 380, "deluxe": 500}
        },
        "initial_symbols": [],
        "floor_plan_image": url_for('static_file', path='placeholder_floorplan.png')
    }
    return render_template("canvas_gpt2.html", **context)

@app.route("/static/<path:path>")
def static_file(path):
    full = os.path.join(APP_DIR, "static", path)
    if os.path.exists(full):
        return send_from_directory(os.path.join(APP_DIR, "static"), path)
    # fallback simple PNG
    try:
        from PIL import Image, ImageDraw
        img = Image.new("RGB",(1200,800),(245,245,245))
        d = ImageDraw.Draw(img)
        d.rectangle((50,50,1150,750), outline=(120,120,120), width=4)
        d.text((70,60), "Floor Plan Placeholder", fill=(85,107,47))
        ph = os.path.join(OUT_DIR,"placeholder.png")
        img.save(ph, "PNG")
        return send_from_directory(OUT_DIR, "placeholder.png")
    except Exception:
        return ("", 204)

def openai_chat(messages, model="gpt-4.1-mini", tools=None):
    if not openai_client:
        return "AI is running in mock mode. Set OPENAI_API_KEY for real responses."
    try:
        resp = openai_client.chat.completions.create(model=model, messages=messages, tools=tools or None, temperature=0.2)
        return resp.choices[0].message.content or ""
    except Exception as e:
        return f"OpenAI error: {e}"

@app.route("/api/ai-chat", methods=["POST"])
def api_ai_chat():
    data = request.get_json(force=True)
    user_msg = data.get("message","")
    agent_mode = bool(data.get("agent_mode", False))
    page = (data.get("context") or {}).get("page","/")
    sys = "You are an expert assistant for an AV/electrical company. Be concise."
    messages=[{"role":"system","content":sys},
              {"role":"user","content":f"Page: {page}\nMessage: {user_msg}\nAgent mode: {agent_mode}"}]
    reply = openai_chat(messages, model=os.getenv("OPENAI_CHAT_MODEL","gpt-4.1-mini"))
    return jsonify({"success": True, "response": reply, "action_taken": None})

def _analyze_locally(pdf_path):
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(open(pdf_path,"rb"))
        pages = len(reader.pages)
    except Exception:
        pages = 1
    return {
        "rooms_detected": 6*pages,
        "doors_detected": 10*pages,
        "windows_detected": 14*pages,
        "method": "smart_grid",
        "ai_notes": "Local heuristic used. Provide OPENAI_API_KEY for vision."
    }

@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    file = request.files.get("floorplan")
    project_name = request.form.get("project_name","Untitled Project")
    tier = request.form.get("tier","basic")
    types = request.form.getlist("automation_types")
    if not file:
        return jsonify({"success": False, "error": "No file"}), 400
    filename = secure_filename(file.filename or f"plan-{uuid.uuid4()}.pdf")
    save_path = os.path.join(UPLOAD_DIR, filename)
    file.save(save_path)

    analysis = _analyze_locally(save_path)

    # Costing
    pricing = {
        "lighting": {"basic": 120, "premium": 160, "deluxe": 220},
        "shading": {"basic": 180, "premium": 230, "deluxe": 300},
        "security_access": {"basic": 220, "premium": 270, "deluxe": 350},
        "climate": {"basic": 250, "premium": 320, "deluxe": 400},
        "audio": {"basic": 300, "premium": 380, "deluxe": 500}
    }
    items=[]; subtotal=0.0
    for t in types:
        qty = max(1, analysis["rooms_detected"]//3)
        unit = pricing.get(t,{}).get(tier,100)
        total = qty*unit
        items.append({"type":t,"quantity":qty,"unit":unit,"total":total})
        subtotal+=total
    markup=round(subtotal*0.2,2); grand=round(subtotal+markup,2)

    # Simple files
    preview_name=f"preview-{uuid.uuid4().hex[:8]}.png"
    preview_path=os.path.join(OUT_DIR, preview_name)
    try:
        from PIL import Image, ImageDraw
        img = Image.new("RGB",(1200,800),(255,255,255))
        d = ImageDraw.Draw(img)
        d.rectangle((50,50,1150,750), outline=(85,107,47), width=5)
        d.text((70,60), f"{project_name} - Annotated Preview", fill=(0,0,0))
        img.save(preview_path)
    except Exception:
        preview_name=None

    quote_pdf=f"quote-{uuid.uuid4().hex[:8]}.pdf"
    quote_path=os.path.join(OUT_DIR, quote_pdf)
    with open(quote_path,"wb") as f:
        f.write(b"%PDF-1.4\n%EOF")

    editor_url = url_for('editor_latest')
    return jsonify({
        "success": True,
        "project_id": str(uuid.uuid4())[:8],
        "analysis": analysis,
        "costs": {"items": items, "subtotal": subtotal, "markup": markup, "grand_total": grand},
        "files": {
            "floor_plan_preview": f"/download/{preview_name}" if preview_name else None,
            "annotated_pdf": f"/download/{quote_pdf}",
            "quote_pdf": f"/download/{quote_pdf}"
        },
        "editor_url": editor_url
    })

@app.route("/download/<path:filename>")
def download(filename):
    return send_from_directory(OUT_DIR, filename, as_attachment=False)

@app.route("/api/generate-final-quote", methods=["POST"])
def api_generate_final_quote():
    quote_pdf=f"final-{uuid.uuid4().hex[:8]}.pdf"
    with open(os.path.join(OUT_DIR,quote_pdf),"wb") as f:
        f.write(b"%PDF-1.4\n%EOF")
    return jsonify({"success": True, "filename": quote_pdf})

@app.route("/api/upload-placement-knowledge", methods=["POST"])
def api_upload_placement_knowledge():
    return jsonify({"success": True})

# ---- CRM (SQLite) ----
def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def ensure_schema():
    con = db(); cur = con.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS customers(
        id TEXT PRIMARY KEY, name TEXT, company TEXT, email TEXT, phone TEXT, address TEXT, notes TEXT,
        total_projects INTEGER DEFAULT 0, total_revenue REAL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS projects(
        id TEXT PRIMARY KEY, customer_id TEXT, title TEXT, description TEXT, status TEXT, priority TEXT,
        quote_amount REAL, due_date TEXT
    );
    CREATE TABLE IF NOT EXISTS events(
        id TEXT PRIMARY KEY, title TEXT, date TEXT, time TEXT, type TEXT, description TEXT, status TEXT DEFAULT 'pending'
    );
    CREATE TABLE IF NOT EXISTS technicians(
        id TEXT PRIMARY KEY, name TEXT, email TEXT, phone TEXT, skills TEXT, status TEXT DEFAULT 'active'
    );
    CREATE TABLE IF NOT EXISTS inventory(
        id TEXT PRIMARY KEY, name TEXT, sku TEXT, category TEXT, quantity INTEGER, unit_cost REAL
    );
    CREATE TABLE IF NOT EXISTS suppliers(
        id TEXT PRIMARY KEY, name TEXT, email TEXT, phone TEXT, website TEXT
    );
    CREATE TABLE IF NOT EXISTS communications(
        id TEXT PRIMARY KEY, customer_id TEXT, type TEXT, subject TEXT, content TEXT, created_at TEXT, created_by TEXT
    );
    """)
    con.commit(); con.close()
ensure_schema()

def row_to_dict(r): return {k:r[k] for k in r.keys()}

@app.route("/api/crm/stats")
def crm_stats():
    con = db(); cur = con.cursor()
    stats = {
        "customers": {"total": cur.execute("SELECT count(*) c FROM customers").fetchone()["c"]},
        "projects": {"total": cur.execute("SELECT count(*) c FROM projects").fetchone()["c"],
                     "active": cur.execute("SELECT count(*) c FROM projects WHERE status='in_progress'").fetchone()["c"]},
        "revenue": {"total": float(cur.execute("SELECT COALESCE(sum(quote_amount),0) s FROM projects").fetchone()["s"]),
                    "pending": float(cur.execute("SELECT COALESCE(sum(quote_amount),0) s FROM projects WHERE status!='completed'").fetchone()["s"])},
        "inventory": {"low_stock": cur.execute("SELECT count(*) c FROM inventory WHERE quantity<3").fetchone()["c"]}
    }
    con.close(); return jsonify({"success": True, "stats": stats})

def list_table(table):
    con = db(); rows=[row_to_dict(r) for r in con.execute(f"SELECT * FROM {table}")]; con.close(); return rows

def save_row(table, values):
    con=db(); cur=con.cursor()
    if values.get("id"):
        keys=[k for k in values.keys() if k!="id"]
        cur.execute(f"UPDATE {table} SET "+",".join([f"{k}=?" for k in keys])+" WHERE id=?",
                    [values[k] for k in keys]+[values["id"]])
        rid=values["id"]
    else:
        rid=str(uuid.uuid4())[:8]; values["id"]=rid
        keys=", ".join(values.keys()); qmarks=", ".join(["?"]*len(values))
        cur.execute(f"INSERT INTO {table}({keys}) VALUES({qmarks})", list(values.values()))
    con.commit(); con.close(); return rid

def delete_row(table, rid):
    con=db(); con.execute(f"DELETE FROM {table} WHERE id=?", (rid,)); con.commit(); con.close()

@app.route("/api/crm/customers", methods=["GET","POST"])
def customers_api():
    if request.method=="GET": return jsonify({"success": True, "customers": list_table("customers")})
    data=request.get_json(force=True)
    rid=save_row("customers",{
        "id": data.get("id",""), "name": data.get("name",""), "company": data.get("company",""),
        "email": data.get("email",""), "phone": data.get("phone",""),
        "address": data.get("address",""), "notes": data.get("notes","")
    }); return jsonify({"success": True, "id": rid})

@app.route("/api/crm/customers/<rid>", methods=["PUT","DELETE"])
def customers_item(rid):
    if request.method=="DELETE": delete_row("customers", rid); return jsonify({"success": True})
    data=request.get_json(force=True); data["id"]=rid; save_row("customers", data); return jsonify({"success": True})

@app.route("/api/crm/projects", methods=["GET","POST"])
def projects_api():
    if request.method=="GET": return jsonify({"success": True, "projects": list_table("projects")})
    data=request.get_json(force=True)
    rid=save_row("projects",{
        "id": data.get("id",""), "customer_id": data.get("customer_id",""), "title": data.get("title",""),
        "description": data.get("description",""), "status": data.get("status","pending"),
        "priority": data.get("priority","medium"), "quote_amount": float(data.get("quote_amount",0) or 0),
        "due_date": data.get("due_date","")
    }); return jsonify({"success": True, "id": rid})

@app.route("/api/crm/projects/<rid>", methods=["PUT"])
def projects_item(rid):
    data=request.get_json(force=True); data["id"]=rid; save_row("projects", data); return jsonify({"success": True})

@app.route("/api/crm/calendar", methods=["GET","POST"])
def calendar_api():
    if request.method=="GET": return jsonify({"success": True, "events": list_table("events")})
    data=request.get_json(force=True)
    rid=save_row("events",{
        "id": data.get("id",""), "title": data.get("title",""), "date": data.get("date",""),
        "time": data.get("time",""), "type": data.get("type","appointment"), "description": data.get("description","")
    }); return jsonify({"success": True, "id": rid})

@app.route("/api/crm/technicians", methods=["GET","POST"])
def tech_api():
    if request.method=="GET": return jsonify({"success": True, "technicians": list_table("technicians")})
    data=request.get_json(force=True)
    rid=save_row("technicians",{
        "id": data.get("id",""), "name": data.get("name",""), "email": data.get("email",""),
        "phone": data.get("phone",""), "skills": ",".join(data.get("skills",[]))
    }); return jsonify({"success": True, "id": rid})

@app.route("/api/crm/inventory", methods=["GET","POST"])
def inv_api():
    if request.method=="GET": return jsonify({"success": True, "inventory": list_table("inventory")})
    data=request.get_json(force=True)
    rid=save_row("inventory",{
        "id": data.get("id",""), "name": data.get("name",""), "sku": data.get("sku",""),
        "category": data.get("category","other"), "quantity": int(data.get("quantity",0) or 0),
        "unit_cost": float(data.get("unit_cost",0) or 0)
    }); return jsonify({"success": True, "id": rid})

@app.route("/api/crm/suppliers", methods=["GET","POST"])
def suppliers_api():
    if request.method=="GET": return jsonify({"success": True, "suppliers": list_table("suppliers")})
    data=request.get_json(force=True)
    rid=save_row("suppliers",{
        "id": data.get("id",""), "name": data.get("name",""), "email": data.get("email",""),
        "phone": data.get("phone",""), "website": data.get("website","")
    }); return jsonify({"success": True, "id": rid})

@app.route("/api/crm/communications", methods=["GET","POST"])
def comm_api():
    if request.method=="GET": return jsonify({"success": True, "communications": list_table("communications")})
    data=request.get_json(force=True)
    rid=save_row("communications",{
        "id": data.get("id",""), "customer_id": data.get("customer_id",""), "type": data.get("type","note"),
        "subject": data.get("subject",""), "content": data.get("content",""),
        "created_at": datetime.datetime.utcnow().isoformat(), "created_by": "system"
    }); return jsonify({"success": True, "id": rid})

@app.route("/api/crm/integrations")
def integrations():
    return jsonify({"success": True, "integrations": {"simpro": {"enabled": False}}})

SIMPRO_CFG = {}
@app.route("/api/simpro/config", methods=["GET","POST"])
def simpro_cfg():
    global SIMPRO_CFG
    if request.method=="GET": return jsonify(SIMPRO_CFG or {"connected": False, "base_url":"", "company_id":"0"})
    SIMPRO_CFG = request.get_json(force=True); return jsonify({"success": True})

@app.route("/api/simpro/connect", methods=["POST"])
def simpro_connect(): return jsonify({"success": True})

@app.route("/api/simpro/<dtype>")
def simpro_data(dtype): return jsonify({"success": True, "data": []})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
