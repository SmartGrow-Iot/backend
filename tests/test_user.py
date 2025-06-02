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
        user_data = {
            "plantId": "plant_123",
            "name": "Aloe Vera",
            "createdAt": "2024-01-01T00:00:00",
            "updatedAt": "2024-01-01T00:00:00"
        }
        mock_get_db.return_value.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_document
        mock_document.get.return_value = mock_doc_snapshot
        mock_doc_snapshot.to_dict.return_value = user_data

        # Import app after mocking
        from main import app
        client = TestClient(app)
        yield client


def test_register_user_success(client_with_mock_firestore):
    """
        Test that register_user returns success.
    """
    # Arrange
    client = client_with_mock_firestore
    user_payload = {
        "email": "test@example.com",
        "password": "securepassword",
        "display_name": "Test User"
    }
    mock_user_record = Mock()
    mock_user_record.uid = "user_123"
    mock_user_record.email = user_payload["email"]
    mock_user_record.display_name = user_payload["display_name"]

    with patch("routes.user.auth.create_user", return_value=mock_user_record):
        # Act
        response = client.post("/api/v1/auth/register", json=user_payload)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "User created successfully"
        assert data["uid"] == "user_123"
        assert data["email"] == user_payload["email"]
        assert data["display_name"] == user_payload["display_name"]


def test_register_user_with_weak_password(client_with_mock_firestore):
    """
        Test that register_user fails for weak password.
    """
    # Arrange
    client = client_with_mock_firestore
    user_payload = {
        "email": "test@example.com",
        "password": "123",
        "display_name": "Test User"
    }
    mock_user_record = Mock()
    mock_user_record.uid = "user_123"
    mock_user_record.email = user_payload["email"]
    mock_user_record.display_name = user_payload["display_name"]

    with patch("routes.user.auth.create_user", return_value=mock_user_record):
        # Act
        response = client.post("/api/v1/auth/register", json=user_payload)

        # Assert
        assert response.status_code == 422
        error_detail = response.json()["detail"]
        assert any(
            err.get("msg") == "Value error, Password must be at least 6 characters"
            for err in error_detail
        )



