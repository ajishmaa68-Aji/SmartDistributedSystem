from flask import Flask, request, jsonify
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)

WORKER_ID = "W001"
@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "worker": WORKER_ID,
        "status": "Active",
        "port": 5001
    })
@app.route("/process", methods=["POST"])
def process_assignment():

    data = request.get_json()

    assignment_id = data.get("assignment_id")

    connection = sqlite3.connect(
    os.path.join(BASE_DIR, "assignments.db")
)
    cursor = connection.cursor()

    cursor.execute(
        "UPDATE assignments SET status = ? WHERE id = ?",
        ("Processing", assignment_id)
    )

    connection.commit()

    cursor.execute(
        "UPDATE assignments SET status = ? WHERE id = ?",
        ("Completed", assignment_id)
    )

    connection.commit()
    connection.close()

    return jsonify({
        "worker": WORKER_ID,
        "message": "Assignment processed successfully!"
    })

if __name__ == "__main__":
    app.run(port=5001, debug=False)