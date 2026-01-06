"""
Tests for content API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


class TestContentAPI:
    """Tests for /api/v1/content endpoints."""

    def test_list_content(self, client: TestClient, sample_content):
        """Test listing content."""
        response = client.get("/api/v1/content")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    def test_list_content_by_project(self, client: TestClient, sample_content, sample_project):
        """Test listing content filtered by project."""
        response = client.get(f"/api/v1/content?project_id={sample_project.id}")
        assert response.status_code == 200
        data = response.json()
        assert all(c["project_id"] == sample_project.id for c in data["items"])

    def test_list_content_by_opportunity(self, client: TestClient, sample_content, sample_opportunity):
        """Test listing content filtered by opportunity."""
        response = client.get(f"/api/v1/content?opportunity_id={sample_opportunity.id}")
        assert response.status_code == 200
        data = response.json()
        assert all(c["opportunity_id"] == sample_opportunity.id for c in data["items"])

    def test_list_content_by_status(self, client: TestClient, sample_content):
        """Test listing content filtered by status."""
        response = client.get("/api/v1/content?status=pending")
        assert response.status_code == 200
        data = response.json()
        assert all(c["status"] == "pending" for c in data["items"])

    def test_get_content(self, client: TestClient, sample_content):
        """Test getting specific content."""
        response = client.get(f"/api/v1/content/{sample_content.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_content.id
        assert data["content_text"] == sample_content.content_text

    def test_get_content_not_found(self, client: TestClient):
        """Test getting non-existent content."""
        response = client.get("/api/v1/content/99999")
        assert response.status_code == 404

    def test_update_content(self, client: TestClient, sample_content):
        """Test updating content text."""
        response = client.put(
            f"/api/v1/content/{sample_content.id}",
            json={"content_text": "Updated content text here..."}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Updated content text" in data["content_text"]

    def test_update_published_content_fails(self, client: TestClient, sample_content, db):
        """Test that updating published content fails."""
        sample_content.status = "published"
        db.commit()

        response = client.put(
            f"/api/v1/content/{sample_content.id}",
            json={"content_text": "Trying to update published..."}
        )
        assert response.status_code == 400

    def test_approve_content(self, client: TestClient, sample_content):
        """Test approving content."""
        response = client.post(f"/api/v1/content/{sample_content.id}/approve")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"

    def test_reject_content(self, client: TestClient, sample_content):
        """Test rejecting content."""
        response = client.post(
            f"/api/v1/content/{sample_content.id}/reject?reason=Too%20promotional"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"

    def test_get_content_performance(self, client: TestClient, sample_content, db):
        """Test getting content performance metrics."""
        # Add some performance data
        from app.models import ContentPerformance
        from datetime import datetime

        perf = ContentPerformance(
            content_id=sample_content.id,
            score=25,
            upvotes=30,
            downvotes=5,
            num_replies=3,
            is_removed=False,
            snapshot_at=datetime.utcnow(),
        )
        db.add(perf)
        db.commit()

        response = client.get(f"/api/v1/content/{sample_content.id}/performance")
        assert response.status_code == 200
        data = response.json()
        assert data["content_id"] == sample_content.id
        assert data["current_score"] == 25
        assert data["current_replies"] == 3
        assert len(data["snapshots"]) == 1

    def test_list_content_quality_filter(self, client: TestClient, sample_content):
        """Test filtering content by quality gate status."""
        response = client.get("/api/v1/content?passed_quality=true")
        assert response.status_code == 200
        data = response.json()
        assert all(c["passed_quality_gates"] == True for c in data["items"])
