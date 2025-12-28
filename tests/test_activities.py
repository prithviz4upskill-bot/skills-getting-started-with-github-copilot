"""
Tests for the Mergington High School Activities API
"""

import pytest
from pathlib import Path
import json
from fastapi.testclient import TestClient
from src.app import app, activities, DEFAULT_ACTIVITIES, DATA_FILE


@pytest.fixture
def client():
    """Fixture to provide a test client"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities to initial state before each test and remove data file"""
    # Remove the data file if it exists
    if DATA_FILE.exists():
        DATA_FILE.unlink()
    
    # Clear and reset activities
    activities.clear()
    activities.update(DEFAULT_ACTIVITIES.copy())
    
    yield
    
    # Cleanup after test - remove data file
    if DATA_FILE.exists():
        DATA_FILE.unlink()
    
    # Reset activities to defaults
    activities.clear()
    activities.update(DEFAULT_ACTIVITIES.copy())


class TestGetActivities:
    """Test cases for GET /activities endpoint"""

    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert len(data) == 9

    def test_activity_contains_required_fields(self, client):
        """Test that each activity contains required fields"""
        response = client.get("/activities")
        data = response.json()
        activity = data["Chess Club"]
        
        assert "description" in activity
        assert "schedule" in activity
        assert "max_participants" in activity
        assert "participants" in activity

    def test_activity_participants_is_list(self, client):
        """Test that participants field is a list"""
        response = client.get("/activities")
        data = response.json()
        activity = data["Chess Club"]
        
        assert isinstance(activity["participants"], list)
        assert "michael@mergington.edu" in activity["participants"]


class TestSignupForActivity:
    """Test cases for POST /activities/{activity_name}/signup endpoint"""

    def test_signup_new_participant_success(self, client):
        """Test successfully signing up a new participant"""
        response = client.post(
            "/activities/Chess%20Club/signup",
            params={"email": "newstudent@mergington.edu"}
        )
        assert response.status_code == 200
        assert "Signed up newstudent@mergington.edu for Chess Club" in response.json()["message"]
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "newstudent@mergington.edu" in activities_data["Chess Club"]["participants"]

    def test_signup_duplicate_participant_fails(self, client):
        """Test that signing up an already registered participant fails"""
        response = client.post(
            "/activities/Chess%20Club/signup",
            params={"email": "michael@mergington.edu"}
        )
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]

    def test_signup_nonexistent_activity_fails(self, client):
        """Test that signing up for a nonexistent activity fails"""
        response = client.post(
            "/activities/Nonexistent%20Activity/signup",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_signup_multiple_participants_same_activity(self, client):
        """Test that multiple different participants can sign up for the same activity"""
        # Sign up first participant
        response1 = client.post(
            "/activities/Chess%20Club/signup",
            params={"email": "student1@mergington.edu"}
        )
        assert response1.status_code == 200
        
        # Sign up second participant
        response2 = client.post(
            "/activities/Chess%20Club/signup",
            params={"email": "student2@mergington.edu"}
        )
        assert response2.status_code == 200
        
        # Verify both were added
        activities_response = client.get("/activities")
        participants = activities_response.json()["Chess Club"]["participants"]
        assert "student1@mergington.edu" in participants
        assert "student2@mergington.edu" in participants


class TestUnregisterFromActivity:
    """Test cases for POST /activities/{activity_name}/unregister endpoint"""

    def test_unregister_existing_participant_success(self, client):
        """Test successfully unregistering a participant"""
        response = client.post(
            "/activities/Chess%20Club/unregister",
            params={"email": "michael@mergington.edu"}
        )
        assert response.status_code == 200
        assert "Unregistered michael@mergington.edu from Chess Club" in response.json()["message"]
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "michael@mergington.edu" not in activities_data["Chess Club"]["participants"]

    def test_unregister_nonexistent_participant_fails(self, client):
        """Test that unregistering a non-registered participant fails"""
        response = client.post(
            "/activities/Chess%20Club/unregister",
            params={"email": "notregistered@mergington.edu"}
        )
        assert response.status_code == 400
        assert "not registered" in response.json()["detail"]

    def test_unregister_from_nonexistent_activity_fails(self, client):
        """Test that unregistering from a nonexistent activity fails"""
        response = client.post(
            "/activities/Nonexistent%20Activity/unregister",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_unregister_multiple_participants(self, client):
        """Test unregistering multiple participants from an activity"""
        # Unregister first participant
        response1 = client.post(
            "/activities/Theater%20Club/unregister",
            params={"email": "lucas@mergington.edu"}
        )
        assert response1.status_code == 200
        
        # Unregister second participant
        response2 = client.post(
            "/activities/Theater%20Club/unregister",
            params={"email": "isabella@mergington.edu"}
        )
        assert response2.status_code == 200
        
        # Verify both were removed
        activities_response = client.get("/activities")
        participants = activities_response.json()["Theater Club"]["participants"]
        assert "lucas@mergington.edu" not in participants
        assert "isabella@mergington.edu" not in participants
        assert "mason@mergington.edu" in participants  # Verify other participant still exists


class TestIntegration:
    """Integration tests for signup and unregister workflows"""

    def test_signup_then_unregister(self, client):
        """Test signing up and then unregistering"""
        email = "integration@mergington.edu"
        activity = "Chess%20Club"
        
        # Sign up
        signup_response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert signup_response.status_code == 200
        
        # Verify signed up
        activities_response = client.get("/activities")
        assert email in activities_response.json()["Chess Club"]["participants"]
        
        # Unregister
        unregister_response = client.post(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        assert unregister_response.status_code == 200
        
        # Verify unregistered
        activities_response = client.get("/activities")
        assert email not in activities_response.json()["Chess Club"]["participants"]

    def test_signup_unregister_signup_again(self, client):
        """Test signing up, unregistering, and signing up again"""
        email = "reregister@mergington.edu"
        activity = "Programming%20Class"
        
        # Sign up
        response1 = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        # Unregister
        response2 = client.post(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        assert response2.status_code == 200
        
        # Sign up again
        response3 = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response3.status_code == 200
        
        # Verify signed up
        activities_response = client.get("/activities")
        assert email in activities_response.json()["Programming Class"]["participants"]
