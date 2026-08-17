"""
test_app.py  –  pytest suite for the Student Registration Flask app.

Covers:
  - /health  (success path when DB is up, failure path when DB is down)
  - /        (index lists students)
  - /add     (GET form, POST creates a student)
  - /update  (GET form, POST updates a student)
  - /delete  (removes a student)

Uses mongomock so tests run without a real MongoDB instance,
which is exactly what the CI pipeline needs.
"""

import pytest
from unittest.mock import patch, MagicMock
from app import app


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ──────────────────────────────────────────────
# /health  –  deploy-verification gate
# ──────────────────────────────────────────────

class TestHealthEndpoint:

    def test_health_returns_200_when_db_is_up(self, client):
        """Pipeline health check: expects HTTP 200 and status=healthy."""
        with patch("app.client") as mock_mongo:
            mock_mongo.admin.command.return_value = {"ok": 1}
            response = client.get("/health")

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"

    def test_health_returns_503_when_db_is_down(self, client):
        """Pipeline health check: expects HTTP 503 when MongoDB is unreachable."""
        with patch("app.client") as mock_mongo:
            mock_mongo.admin.command.side_effect = Exception("Connection refused")
            response = client.get("/health")

        assert response.status_code == 503
        data = response.get_json()
        assert data["status"] == "unhealthy"
        assert data["database"] == "unreachable"

    def test_health_response_is_json(self, client):
        """Health endpoint must return JSON content-type."""
        with patch("app.client") as mock_mongo:
            mock_mongo.admin.command.return_value = {"ok": 1}
            response = client.get("/health")

        assert "application/json" in response.content_type


# ──────────────────────────────────────────────
# /  –  index
# ──────────────────────────────────────────────

class TestIndexRoute:

    def test_index_returns_200(self, client):
        with patch("app.students_collection") as mock_col:
            mock_col.find.return_value = []
            response = client.get("/")
        assert response.status_code == 200

    def test_index_lists_students(self, client):
        fake_students = [
            {"_id": "abc", "name": "Alice", "age": 20, "grade": "A"},
            {"_id": "def", "name": "Bob",   "age": 21, "grade": "B"},
        ]
        with patch("app.students_collection") as mock_col:
            mock_col.find.return_value = fake_students
            response = client.get("/")
        assert b"Alice" in response.data
        assert b"Bob" in response.data


# ──────────────────────────────────────────────
# /add  –  create student
# ──────────────────────────────────────────────

class TestAddStudentRoute:

    def test_add_get_returns_200(self, client):
        response = client.get("/add")
        assert response.status_code == 200

    def test_add_post_inserts_and_redirects(self, client):
        with patch("app.students_collection") as mock_col:
            mock_col.insert_one.return_value = MagicMock()
            response = client.post("/add", data={
                "name": "Charlie",
                "age": "22",
                "grade": "A"
            })
        assert response.status_code in (301, 302)
        mock_col.insert_one.assert_called_once()

    def test_add_post_missing_fields_does_not_insert(self, client):
        """Incomplete form data must not write to the database."""
        with patch("app.students_collection") as mock_col:
            response = client.post("/add", data={"name": "Incomplete"})
        mock_col.insert_one.assert_not_called()


# ──────────────────────────────────────────────
# /update/<id>  –  update student
# ──────────────────────────────────────────────

class TestUpdateStudentRoute:

    def test_update_get_returns_200(self, client):
        fake_student = {"_id": "507f1f77bcf86cd799439011",
                        "name": "Dana", "age": 23, "grade": "B"}
        with patch("app.students_collection") as mock_col:
            mock_col.find_one.return_value = fake_student
            response = client.get("/update/507f1f77bcf86cd799439011")
        assert response.status_code == 200

    def test_update_post_calls_update_one(self, client):
        fake_student = {"_id": "507f1f77bcf86cd799439011",
                        "name": "Dana", "age": 23, "grade": "B"}
        with patch("app.students_collection") as mock_col:
            mock_col.find_one.return_value = fake_student
            mock_col.update_one.return_value = MagicMock()
            response = client.post(
                "/update/507f1f77bcf86cd799439011",
                data={"name": "Dana Updated", "age": "24", "grade": "A"}
            )
        assert response.status_code in (301, 302)
        mock_col.update_one.assert_called_once()


# ──────────────────────────────────────────────
# /delete/<id>  –  delete student
# ──────────────────────────────────────────────

class TestDeleteStudentRoute:

    def test_delete_removes_student_and_redirects(self, client):
        with patch("app.students_collection") as mock_col:
            mock_col.delete_one.return_value = MagicMock()
            response = client.get("/delete/507f1f77bcf86cd799439011")
        assert response.status_code in (301, 302)
        mock_col.delete_one.assert_called_once()
