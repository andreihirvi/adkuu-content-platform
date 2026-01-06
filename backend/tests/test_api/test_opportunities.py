"""
Tests for opportunity API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


class TestOpportunitiesAPI:
    """Tests for /api/v1/opportunities endpoints."""

    def test_list_opportunities(self, client: TestClient, sample_opportunity):
        """Test listing opportunities."""
        response = client.get("/api/v1/opportunities")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    def test_list_opportunities_by_project(self, client: TestClient, sample_opportunity, sample_project):
        """Test listing opportunities filtered by project."""
        response = client.get(f"/api/v1/opportunities?project_id={sample_project.id}")
        assert response.status_code == 200
        data = response.json()
        assert all(o["project_id"] == sample_project.id for o in data["items"])

    def test_list_opportunities_by_status(self, client: TestClient, sample_opportunity):
        """Test listing opportunities filtered by status."""
        response = client.get("/api/v1/opportunities?status=pending")
        assert response.status_code == 200
        data = response.json()
        assert all(o["status"] == "pending" for o in data["items"])

    def test_list_opportunities_by_subreddit(self, client: TestClient, sample_opportunity):
        """Test listing opportunities filtered by subreddit."""
        response = client.get("/api/v1/opportunities?subreddit=python")
        assert response.status_code == 200
        data = response.json()
        assert all(o["subreddit"] == "python" for o in data["items"])

    def test_get_opportunity(self, client: TestClient, sample_opportunity):
        """Test getting a specific opportunity."""
        response = client.get(f"/api/v1/opportunities/{sample_opportunity.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_opportunity.id
        assert data["reddit_post_id"] == sample_opportunity.reddit_post_id

    def test_get_opportunity_not_found(self, client: TestClient):
        """Test getting a non-existent opportunity."""
        response = client.get("/api/v1/opportunities/99999")
        assert response.status_code == 404

    def test_approve_opportunity(self, client: TestClient, sample_opportunity):
        """Test approving an opportunity."""
        response = client.post(f"/api/v1/opportunities/{sample_opportunity.id}/approve")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"

    def test_approve_already_approved(self, client: TestClient, sample_opportunity, db):
        """Test approving an already approved opportunity."""
        sample_opportunity.status = "approved"
        db.commit()

        response = client.post(f"/api/v1/opportunities/{sample_opportunity.id}/approve")
        assert response.status_code == 400

    def test_reject_opportunity(self, client: TestClient, sample_opportunity):
        """Test rejecting an opportunity."""
        response = client.post(
            f"/api/v1/opportunities/{sample_opportunity.id}/reject",
            json={"reason": "Not relevant to our product"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"

    def test_list_opportunities_exclude_expired(self, client: TestClient, sample_opportunity, db):
        """Test that expired opportunities are excluded by default."""
        # Create an expired opportunity
        from app.models import Opportunity
        from datetime import datetime

        expired_opp = Opportunity(
            project_id=sample_opportunity.project_id,
            reddit_post_id="expired123",
            subreddit="python",
            post_title="Expired Post",
            post_url="https://reddit.com/r/python/comments/expired123",
            status="expired",
            discovered_at=datetime.utcnow(),
        )
        db.add(expired_opp)
        db.commit()

        # Default should exclude expired
        response = client.get("/api/v1/opportunities")
        data = response.json()
        assert all(o["status"] != "expired" for o in data["items"])

        # With include_expired=true, should include expired
        response = client.get("/api/v1/opportunities?include_expired=true")
        data = response.json()
        statuses = [o["status"] for o in data["items"]]
        assert "expired" in statuses

    def test_list_opportunities_min_score(self, client: TestClient, sample_opportunity):
        """Test filtering opportunities by minimum score."""
        response = client.get("/api/v1/opportunities?min_score=0.5")
        assert response.status_code == 200
        data = response.json()
        assert all(o["composite_score"] >= 0.5 for o in data["items"])
