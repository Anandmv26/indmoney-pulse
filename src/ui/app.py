import os
import glob
import json
import logging
from threading import Lock
from flask import Flask, render_template, jsonify, request

from src.mcp.doc_appender import append_to_doc
from src.mcp.email_drafter import create_draft

app = Flask(__name__)

# Reduce Flask logging spam
log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)

# In-memory pipeline state
state_lock = Lock()
app_state = {
    "payload": None,
    "status": "Initializing...",
    "action_taken": False
}


def start_ui(payload: dict):
    """
    Entry point called by main.py
    Stores the payload in memory and launches the Flask server.
    """
    with state_lock:
        app_state["payload"] = payload
        app_state["status"] = "Ready for Review"
        app_state["action_taken"] = False

    print("\nStarting Web UI Dashboard...")
    print("Open http://127.0.0.1:5000 in your browser to approve/reject.")
    
    # We run Flask in development mode for local visualization.
    app.run(host="127.0.0.1", port=5000, debug=False)


# --- HTML Route ---

@app.route("/")
def index():
    """Serves the main dashboard HTML."""
    return render_template("dashboard.html")


# --- API Routes ---

@app.route("/api/status", methods=["GET"])
def get_status():
    """Returns the current pipeline status."""
    with state_lock:
        return jsonify({
            "status": app_state["status"],
            "action_taken": app_state["action_taken"]
        })


def load_latest_payload() -> dict | None:
    """Finds and loads the latest saved payload JSON from outputs/."""
    outputs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "outputs")
    files = glob.glob(os.path.join(outputs_dir, "full_payload_*.json"))
    if not files:
        return None
    latest_file = max(files, key=os.path.getmtime)
    try:
        with open(latest_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {latest_file}: {e}")
        return None


@app.route("/api/payload", methods=["GET"])
def get_payload():
    """Returns the assembled payload for the frontend to render."""
    with state_lock:
        if not app_state["payload"]:
            latest_payload = load_latest_payload()
            if latest_payload:
                app_state["payload"] = latest_payload
                app_state["status"] = "Ready (Loaded from recent cron run)"
            else:
                return jsonify({"error": "No payload available"}), 404
        return jsonify(app_state["payload"])


@app.route("/api/approve", methods=["POST"])
def approve_payload():
    """
    Triggered when user clicks Approve.
    Expects JSON: {"recipients": ["email1@test.com", ...]}
    Triggers MCP actions and updates status.
    """
    with state_lock:
        if app_state["action_taken"]:
            return jsonify({"error": "Action already taken."}), 400
        
        payload = app_state["payload"]
        if not payload:
            return jsonify({"error": "No payload to approve."}), 400

    # Parse recipients
    data = request.json or {}
    recipients = data.get("recipients", [])
    
    # Temporarily inject recipients into env or payload for email_drafter
    # Since email_drafter.py reads from os.getenv("DRAFT_RECIPIENT"), 
    # we can temporarily set it here to support the UI's dynamic list.
    import os
    if recipients:
        os.environ["DRAFT_RECIPIENT"] = ", ".join(recipients)

    with state_lock:
        app_state["status"] = "Triggering MCP Actions..."

    # Fire MCPactions sequentially
    doc_ok = append_to_doc(payload)
    email_ok = create_draft(payload)

    with state_lock:
        app_state["action_taken"] = True
        
        if doc_ok and email_ok:
            app_state["status"] = "Approved & Actions Completed"
            return jsonify({"success": True, "message": "Doc appended and Email draft created."})
        elif doc_ok:
            app_state["status"] = "Approved (Email Failed)"
            return jsonify({"success": True, "message": "Doc appended, but Email draft failed."})
        elif email_ok:
            app_state["status"] = "Approved (Doc Failed)"
            return jsonify({"success": True, "message": "Email draft created, but Doc append failed."})
        else:
            app_state["status"] = "Approved (All MCP Actions Failed)"
            return jsonify({"error": "All MCP actions failed. Check terminal logs."}), 500


@app.route("/api/reject", methods=["POST"])
def reject_payload():
    """
    Triggered when user clicks Reject.
    Updates status and marks pipeline as finished.
    """
    with state_lock:
        if app_state["action_taken"]:
            return jsonify({"error": "Action already taken."}), 400
        
        app_state["action_taken"] = True
        app_state["status"] = "Rejected by User"
        
    return jsonify({"success": True, "message": "Pipeline rejected. No data written."})
