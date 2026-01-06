"""
Tests for project API endpoints.
"""
import pytest
from fastapi.testclient import TestClient


class TestProjectsAPI:
    """Tests for /api/v1/projects endpoints."""

    def test_create_project(self, client: TestClient):
        """Test creating a new project."""
        response = client.post(
            "/api/v1/projects",
            json={
                "name": "New Test Project",
                "description": "A project for testing",
                "brand_voice": "Professional and helpful",
                "target_subreddits": ["python", "programming"],
                "keywords": ["python", "code"],
                "automation_level": 2,
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Test Project"
        assert data["status"] == "active"
        assert "id" in data

    def test_list_projects(self, client: TestClient, sample_project):
        """Test listing all projects."""
        response = client.get("/api/v1/projects")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    def test_get_project(self, client: TestClient, sample_project):
        """Test getting a specific project."""
        response = client.get(f"/api/v1/projects/{sample_project.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_project.id
        assert data["name"] == sample_project.name

    def test_get_project_not_found(self, client: TestClient):
        """Test getting a non-existent project."""
        response = client.get("/api/v1/projects/99999")
        assert response.status_code == 404

    def test_update_project(self, client: TestClient, sample_project):
        """Test updating a project."""
        response = client.put(
            f"/api/v1/projects/{sample_project.id}",
            json={
                "name": "Updated Project Name",
                "automation_level": 3,
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Project Name"
        assert data["automation_level"] == 3

    def test_delete_project(self, client: TestClient, sample_project):
        """Test deleting (archiving) a project."""
        response = client.delete(f"/api/v1/projects/{sample_project.id}")
        assert response.status_code == 204

        # Verify project is archived
        response = client.get(f"/api/v1/projects/{sample_project.id}")
        assert response.status_code == 200
        assert response.json()["status"] == "archived"

    def test_add_subreddit_config(self, client: TestClient, sample_project):
        """Test adding subreddit configuration to a project."""
        response = client.post(
            f"/api/v1/projects/{sample_project.id}/subreddits",
            json={
                "subreddit_name": "learnpython",
                "min_karma": 50,
                "min_account_age_days": 14,
                "velocity_threshold": 10.0,
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["subreddit_name"] == "learnpython"
        assert data["min_karma"] == 50

    def test_list_projects_with_status_filter(self, client: TestClient, sample_project):
        """Test listing projects filtered by status."""
        response = client.get("/api/v1/projects?status=active")
        assert response.status_code == 200
        data = response.json()
        assert all(p["status"] == "active" for p in data["items"])
