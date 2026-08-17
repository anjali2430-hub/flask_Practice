from flask import Flask, render_template, request, redirect, url_for, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
import os

app = Flask(__name__)

# MongoDB connection
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["student_db"]
students_collection = db["students"]


# ──────────────────────────────────────────────
# Health / status endpoint (required by pipeline)
# ──────────────────────────────────────────────
@app.route("/health")
def health():
    """
    Deploy-verification gate used by the CI/CD pipeline.
    Returns 200 + JSON when the app AND MongoDB are reachable.
    Returns 503 if MongoDB is down so the pipeline can detect a bad deploy.
    """
    try:
        # ping forces an actual round-trip to MongoDB
        client.admin.command("ping")
        return jsonify({
            "status": "healthy",
            "database": "connected"
        }), 200
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "database": "unreachable",
            "error": str(e)
        }), 503


# ──────────────────────────────────────────────
# Existing application routes (unchanged)
# ──────────────────────────────────────────────
@app.route("/")
def index():
    students = list(students_collection.find())
    return render_template("index.html", students=students)


@app.route("/add", methods=["GET", "POST"])
def add_student():
    if request.method == "POST":
        name = request.form.get("name")
        age = request.form.get("age")
        grade = request.form.get("grade")
        if name and age and grade:
            students_collection.insert_one({
                "name": name,
                "age": int(age),
                "grade": grade
            })
            return redirect(url_for("index"))
    return render_template("add_student.html")


@app.route("/update/<student_id>", methods=["GET", "POST"])
def update_student(student_id):
    student = students_collection.find_one({"_id": ObjectId(student_id)})
    if request.method == "POST":
        name = request.form.get("name")
        age = request.form.get("age")
        grade = request.form.get("grade")
        students_collection.update_one(
            {"_id": ObjectId(student_id)},
            {"$set": {"name": name, "age": int(age), "grade": grade}}
        )
        return redirect(url_for("index"))
    return render_template("update_student.html", student=student)


@app.route("/delete/<student_id>")
def delete_student(student_id):
    students_collection.delete_one({"_id": ObjectId(student_id)})
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
