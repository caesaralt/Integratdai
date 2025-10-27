# app_gpt2_p3.py
# Adds the /ai-mapping page to the existing app_gpt2 app.
import os
from app_gpt2 import app
from flask import render_template

@app.get("/ai-mapping")
def ai_mapping():
    return render_template("aimapping_gpt3.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
