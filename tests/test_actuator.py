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
        actuator_data = {
            "id": "actuator_mock_123",
            "actuatorModel": "FAN-9000",
            "description": "Cooling fan",
            "type": "fan",
            "createdAt": "2024-01-01T00:00:00Z"
        }
        mock_get_db.return_value.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_document
        mock_document.get.return_value = mock_doc_snapshot
        mock_doc_snapshot.to_dict.return_value = actuator_data

        # Import app after mocking
        from main import app
        client = TestClient(app)
        yield client

def test_add_actuator_success(client_with_mock_firestore):
    """
        Test that add_actuator returns success.
    """
    # Arrange
    client = client_with_mock_firestore
    payload = {
        "actuatorModel": "FAN-9000",
        "description": "Cooling fan",
        "type": "fan"
    }

    # Act
    response = client.post("/api/v1/actuator", json=payload)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["id"].startswith("actuator_")
    assert data["actuatorModel"] == payload["actuatorModel"]
    assert data["description"] == payload["description"]
    assert data["type"] == payload["type"]
    assert "createdAt" in data


def test_get_actuator_success(client_with_mock_firestore):
    """
        Test that get_actuator returns success.
    """
    # Arrange
    client = client_with_mock_firestore
    test_doc_id = "actuator_mock_123"

    # Act
    response = client.get(f"/api/v1/actuator/{test_doc_id}")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "actuator_mock_123"
    assert data["actuatorModel"] == "FAN-9000"
    assert data["type"] == "fan"
    assert data["description"] == "Cooling fan"

