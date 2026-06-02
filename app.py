#!/usr/bin/env python3
"""
app.py — Flask server להגשת נתוני מדד המומנטום
מריץ collector בעת הפעלה ואז כל 6 שעות
"""
import json
import logging
from pathlib import Path

from flask import Flask, jsonify, send_file
from flask_cors import CORS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # CORS פתוח — חיוני להטמעה ב-WordPress

DATA_FILE = Path(__file__).parent / "data.json"


def _load_data() -> dict:
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"updated": "—", "sources_used": [], "sources_failed": [], "parties": []}


@app.route("/data.json")
def api_data():
    return jsonify(_load_data())


@app.route("/widget")
def widget():
    widget_path = Path(__file__).parent / "widget.html"
    return send_file(widget_path)


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


def start_scheduler():
    from apscheduler.schedulers.background import BackgroundScheduler
    import collector

    scheduler = BackgroundScheduler()
    # ריצה ראשונה מיד
    scheduler.add_job(collector.collect, "interval", hours=6, id="collect")
    scheduler.start()

    log.info("מריץ איסוף ראשוני...")
    try:
        collector.collect()
    except Exception as e:
        log.warning("איסוף ראשוני נכשל: %s", e)


if __name__ == "__main__":
    start_scheduler()
    app.run(host="0.0.0.0", port=10000, debug=False)
