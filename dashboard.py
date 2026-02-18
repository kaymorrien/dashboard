import os, subprocess
import psutil
from flask import Flask, jsonify, send_from_directory, request

app = Flask(__name__)

HERE = os.path.dirname(os.path.abspath(__file__))

PROJECTS = [
    {
        "name": "SignalEdge",
        "description": "Live trading signals — ETH, XRP, ADA, SOL, LTC, BCH, DOGE",
        "service": "signaledge",
        "url": "http://89.167.67.39",
        "path": "/opt/signal-project",
    },
]

PROJECT_PATHS = {p["service"]: p["path"] for p in PROJECTS}

VIEWABLE_EXTENSIONS = {".py", ".html", ".js", ".css", ".txt", ".md", ".json", ".yaml", ".yml", ".sh", ".env.example"}

def service_status(name):
    try:
        r = subprocess.run(["systemctl", "is-active", name], capture_output=True, text=True)
        return r.stdout.strip()
    except:
        return "unknown"

@app.route("/")
def index():
    return send_from_directory(HERE, "dashboard.html")

@app.route("/api/status")
def api_status():
    projects = []
    for p in PROJECTS:
        s = service_status(p["service"])
        projects.append({**p, "status": s, "running": s == "active"})

    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    return jsonify({
        "projects": projects,
        "system": {
            "cpu":        psutil.cpu_percent(interval=0.5),
            "ram_pct":    mem.percent,
            "ram_used":   round(mem.used  / 1024**3, 1),
            "ram_total":  round(mem.total / 1024**3, 1),
            "disk_pct":   disk.percent,
            "disk_used":  round(disk.used  / 1024**3, 1),
            "disk_total": round(disk.total / 1024**3, 1),
        },
    })

@app.route("/api/service/<name>/<action>", methods=["POST"])
def service_action(name, action):
    allowed = {p["service"] for p in PROJECTS}
    if name not in allowed or action not in ("start", "stop", "restart"):
        return jsonify({"error": "not allowed"}), 403
    subprocess.run(["systemctl", action, name])
    return jsonify({"ok": True, "status": service_status(name)})

@app.route("/api/files/<service>")
def api_files(service):
    path = PROJECT_PATHS.get(service)
    if not path:
        return jsonify({"error": "unknown project"}), 404
    files = []
    for f in sorted(os.listdir(path)):
        full = os.path.join(path, f)
        if os.path.isfile(full) and os.path.splitext(f)[1] in VIEWABLE_EXTENSIONS:
            files.append(f)
    return jsonify({"files": files})

@app.route("/api/file/<service>")
def api_file(service):
    path = PROJECT_PATHS.get(service)
    if not path:
        return jsonify({"error": "unknown project"}), 404
    filename = request.args.get("name", "")
    # Security: no path traversal
    safe = os.path.basename(filename)
    full = os.path.join(path, safe)
    if not os.path.isfile(full) or os.path.splitext(safe)[1] not in VIEWABLE_EXTENSIONS:
        return jsonify({"error": "not allowed"}), 403
    with open(full, "r", errors="replace") as f:
        content = f.read()
    return jsonify({"filename": safe, "content": content})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
