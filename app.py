from flask import Flask, render_template, request
import os
import sqlite3
import json
import urllib.request
from werkzeug.utils import secure_filename
from database import create_database

app = Flask(__name__)

workers = [
    "http://127.0.0.1:5001/process",
    "http://127.0.0.1:5002/process"
]

next_worker = 0

create_database()

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# Check worker health
def get_worker_details():

    worker_details = []

    for worker_url in workers:
        try:
            health_url = worker_url.replace("/process", "/health")

            with urllib.request.urlopen(health_url, timeout=3) as response:
                details = json.loads(response.read().decode("utf-8"))

            worker_details.append(details)

        except Exception:
            worker_details.append({
                "worker": "Worker Unavailable",
                "status": "Inactive",
                "port": worker_url.split(":")[-1].split("/")[0]
            })

    return worker_details


# Home Dashboard
@app.route("/")
def home():

    connection = sqlite3.connect("assignments.db")
    cursor = connection.cursor()

    cursor.execute(
        "SELECT filename, status FROM assignments ORDER BY id DESC LIMIT 1"
    )
    latest_assignment = cursor.fetchone()

    cursor.execute(
        "SELECT saved_status FROM checkpoints ORDER BY id DESC LIMIT 1"
    )
    latest_checkpoint = cursor.fetchone()

    connection.close()

    worker_details = get_worker_details()

    total_workers = len(worker_details)

    active_workers = sum(
        1 for worker in worker_details
        if worker["status"] == "Active"
    )

    inactive_workers = total_workers - active_workers

    return render_template(
        "index.html",
        latest_assignment=latest_assignment,
        latest_checkpoint=latest_checkpoint,
        total_workers=total_workers,
        active_workers=active_workers,
        inactive_workers=inactive_workers
    )


# Upload Assignment
@app.route("/upload", methods=["POST"])
def upload_assignment():

    if "file" not in request.files:
        return "No file selected"

    file = request.files["file"]

    if file.filename == "":
        return "Please select a file"

    if file.filename.lower().endswith(".pdf"):

        filename = secure_filename(file.filename)

        if not filename:
            return "Invalid file name"

        file.save(
            os.path.join(app.config["UPLOAD_FOLDER"], filename)
        )

        connection = sqlite3.connect("assignments.db")
        cursor = connection.cursor()

        cursor.execute(
            "INSERT INTO assignments (filename, status) VALUES (?, ?)",
            (filename, "Pending")
        )

        connection.commit()

        assignment_id = cursor.lastrowid
        connection.close()

        global next_worker

        selected_worker = workers[next_worker]

        next_worker = (next_worker + 1) % len(workers)

        data = json.dumps({
            "assignment_id": assignment_id
        }).encode("utf-8")

        req = urllib.request.Request(
            selected_worker,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                result = response.read().decode("utf-8")

            return (
                "Assignment uploaded and processed successfully! "
                + result
            )

        except Exception as error:
            print("WORKER ERROR:", repr(error))
            return (
                "Assignment uploaded, but worker processing failed: "
                + repr(error)
            )

    return "Only PDF files are allowed"


# Assignment Status
@app.route("/status")
def assignment_status():

    connection = sqlite3.connect("assignments.db")
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM assignments")
    assignments = cursor.fetchall()

    connection.close()

    return render_template(
        "status.html",
        assignments=assignments
    )


# Recover Task
@app.route("/recover_task", methods=["POST"])
def recover_task():

    connection = sqlite3.connect("assignments.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT assignment_id, saved_status
        FROM checkpoints
        ORDER BY id DESC
        LIMIT 1
    """)

    checkpoint = cursor.fetchone()

    if checkpoint is None:
        connection.close()
        return "No checkpoint available!"

    cursor.execute(
        "UPDATE assignments SET status = ? WHERE id = ?",
        (checkpoint[1], checkpoint[0])
    )

    connection.commit()
    connection.close()

    return "Task recovered successfully from the last checkpoint!"


# Save Checkpoint
@app.route("/save_checkpoint", methods=["POST"])
def save_checkpoint():

    connection = sqlite3.connect("assignments.db")
    cursor = connection.cursor()

    cursor.execute(
        "SELECT id, status FROM assignments ORDER BY id DESC LIMIT 1"
    )

    assignment = cursor.fetchone()

    if assignment is None:
        connection.close()
        return "No assignment available to save checkpoint"

    cursor.execute(
        "INSERT INTO checkpoints (assignment_id, saved_status) VALUES (?, ?)",
        (assignment[0], assignment[1])
    )

    connection.commit()
    connection.close()

    return "Checkpoint saved successfully!"


# Simulate Worker Failure
@app.route("/simulate_failure", methods=["POST"])
def simulate_failure():

    connection = sqlite3.connect("assignments.db")
    cursor = connection.cursor()

    cursor.execute(
        "SELECT id FROM assignments ORDER BY id DESC LIMIT 1"
    )

    assignment = cursor.fetchone()

    if assignment is None:
        connection.close()
        return "No assignment available"

    cursor.execute(
        "UPDATE assignments SET status = ? WHERE id = ?",
        ("Failed", assignment[0])
    )

    connection.commit()
    connection.close()

    return "Worker failure simulated! Assignment marked as Failed."


# Worker Status
@app.route("/workers")
def worker_status():

    worker_details = get_worker_details()

    return render_template(
        "workers.html",
        workers=worker_details
    )


# Assignment History
@app.route("/history")
def assignment_history():

    connection = sqlite3.connect("assignments.db")
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM assignments")
    assignments = cursor.fetchall()

    connection.close()

    return render_template(
        "history.html",
        assignments=assignments
    )


if __name__ == "__main__":
    app.run(debug=True)