import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
import os

@pytest.fixture
def client_with_mock_firestore():
    """
        Testing environment setup.
    """
    os.environ["TEST_MODE"] = "true"
    with patch("firebase_config.get_firestore_db") as mock_get_db:
        # Mock Firestore behavior
        mock_collection = Mock()
        mock_document = Mock()
        mock_doc_snapshot = Mock()
        action_log_data = {
            "action": "watering",
            "actuatorId": "act123",
            "plantId": "plant456",
            "amount": 5.0,
            "trigger": "manual",
            "triggerBy": "user123",
            "timestamp": "2024-01-01T00:00:00"
        }
        mock_get_db.return_value.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_document
        mock_document.get.return_value = mock_doc_snapshot
        mock_doc_snapshot.to_dict.return_value = action_log_data

        # Import app after mocking
        from main import app
        client = TestClient(app)
        yield client

def test_create_watering_log_success(client_with_mock_firestore):
    """
        Test that create_action_log for watering action returns success.
    """
    # Arrange
    client = client_with_mock_firestore
    payload = {
        "action": "watering",
        "actuatorId": "act123",
        "plantId": "plant456",
        "amount": 5.0,
        "trigger": "manual",
        "triggerBy": "user123",
    }

    # Act
    response = client.post("/api/v1/logs/action/water", json=payload)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["id"].startswith("action_")
    assert data["action"] == "watering"
    assert data["actuatorId"] == "act123"

def test_create_watering_log_with_negative_amount(client_with_mock_firestore):
    """
        Test that create_action_log fails for watering action with negative amount.
    """
    # Arrange
    client = client_with_mock_firestore
    payload = {
            "action": "watering",
            "actuatorId": "act123",
            "plantId": "plant456",
            "amount": -10.0,
            "trigger": "manual",
            "triggerBy": "user123",
    }

    # Act
    response = client.post("/api/v1/logs/action/water", json=payload)

    # Assert
    assert response.status_code == 422
    error_detail = response.json()["detail"]
    assert any(
        err.get("msg") == "Value error, amount must be a positive number."
        for err in error_detail
    )

def test_create_watering_log_without_amount(client_with_mock_firestore):
    """
        Test that create_action_log fails for watering action without pass in amount.
    """
    # Arrange
    client = client_with_mock_firestore
    payload = {
            "action": "watering",
            "actuatorId": "act123",
            "plantId": "plant456",
            "trigger": "manual",
            "triggerBy": "user123",
    }

    # Act
    response = client.post("/api/v1/logs/action/water", json=payload)

    # Assert
    assert response.status_code == 422
    error_detail = response.json()["detail"]
    assert any(
        err.get("msg") == "Value error, amount is required for watering actions."
        for err in error_detail
    )

def test_invalid_action_for_endpoint(client_with_mock_firestore):
    """
        Test that create_action_log fails if endpoint parameter inconsistent with action.
    """
    # Arrange
    client = client_with_mock_firestore
    payload = {
        "action": "light_on",  # Invalid for "water" endpoint
        "actuatorId": "act123",
        "plantId": "plant456",
        "trigger": "manual",
        "triggerBy": "user123"
    }

    # Act
    response = client.post("/api/v1/logs/action/water", json=payload)

    # Assert
    assert response.status_code == 400
    assert "Invalid action" in response.json()["detail"]


def test_get_action_log_success(client_with_mock_firestore):
    """
        Test that get_action_log returns success.
    """
    # Arrange
    client = client_with_mock_firestore
    test_doc_id = "action_mock_456"

    # Act
    response = client.get(f"/api/v1/logs/action/{test_doc_id}")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["action"] == "watering"
    assert data["actuatorId"] == "act123"




