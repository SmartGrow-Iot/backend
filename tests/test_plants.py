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
        plant_data = {
            "plantId": "plant_123",
            "name": "Aloe Vera",
            "createdAt": "2024-01-01T00:00:00",
            "updatedAt": "2024-01-01T00:00:00"
        }
        mock_get_db.return_value.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_document
        mock_document.get.return_value = mock_doc_snapshot
        mock_doc_snapshot.to_dict.return_value = plant_data

        # Import app after mocking
        from main import app
        client = TestClient(app)
        yield client

def test_create_plant_success(client_with_mock_firestore):
    """
        Test that create_plant returns success.
    """
    # Arrange
    client = client_with_mock_firestore
    payload = {
        "name": "Aloe Vera",
        "userId": "user123",
        "thresholds": {
            "moisture": {
                "min": 10.0,
                "max": 20.0
            },
            "temperature": {
                "min": 27.0,
                "max": 32.0
            },
            "light": {
                "min": 100.0,
                "max": 200.0
            }
        },
        "description": "good plant"
    }

    # Act
    response = client.post("/api/v1/plants", json=payload)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["plantId"].startswith("plant_")
    assert data["name"] == "Aloe Vera"
    assert data["userId"] == "user123"
    assert "createdAt" in data
    assert "updatedAt" in data

def test_create_plant_with_min_over_max(client_with_mock_firestore):
    """
        Test that create_plant fails if min over max.
    """
    # Arrange
    client = client_with_mock_firestore
    payload = {
        "name": "Aloe Vera",
        "userId": "user123",
        "thresholds": {
            "moisture": {
                "min": 30.0,
                "max": 20.0
            },
            "temperature": {
                "min": 27.0,
                "max": 32.0
            },
            "light": {
                "min": 100.0,
                "max": 200.0
            }
        },
        "description": "good plant"
    }

    # Act
    response = client.post("/api/v1/plants", json=payload)

    # Assert
    assert response.status_code == 422
    error_detail = response.json()["detail"]
    assert any(
        err.get("msg") == "Value error, min must be less than max"
        for err in error_detail
    )

def test_get_plant_success(client_with_mock_firestore):
    """
        Test that get_plant returns success.
    """
    # Arrange
    client = client_with_mock_firestore
    plant_id = "plant_123"

    # Act
    response = client.get(f"/api/v1/plants/{plant_id}")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["plantId"] == "plant_123"
    assert data["name"] == "Aloe Vera"

