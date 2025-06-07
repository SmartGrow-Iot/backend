import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
import os
from datetime import datetime

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
        sensor_id = "sensor_abc123"
        sensor_data = {
            "sensorId": sensor_id,
            "sensorModel": "DHT-11",
            "type": "humidity",
            "description": "Humidity sensor for testing"
        }
        mock_get_db.return_value.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_document
        mock_document.get.return_value = mock_doc_snapshot
        mock_doc_snapshot.to_dict.return_value = sensor_data

        # Import app after mocking
        from main import app
        client = TestClient(app)
        yield client

def test_create_sensor_success(client_with_mock_firestore):
    """
        Test that create_sensor returns success.
    """
    # Arrange
    client = client_with_mock_firestore
    payload = {
        "sensorModel": "DHT-22",
        "type": "temperature",
        "description": "Measures temperature in greenhouse"
    }

    # Act
    response = client.post("/api/v1/sensors", json=payload)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "sensorId" in data
    assert data["sensorId"].startswith("sensor_")
    assert data["sensorModel"] == payload["sensorModel"]
    assert data["type"] == payload["type"]
    assert data["description"] == payload["description"]

def test_get_sensor_success(client_with_mock_firestore):
    """
        Test that get_sensor returns success.
    """
    # Arrange
    client = client_with_mock_firestore
    sensor_id = "sensor_abc123"

    # Act
    response = client.get(f"/api/v1/sensors/{sensor_id}")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["sensorId"].startswith("sensor_")
    assert data["sensorModel"] == "DHT-11"
    assert data["type"] == "humidity"
    assert data["description"] == "Humidity sensor for testing"

def test_submit_environmental_sensor_data_success(client_with_mock_firestore):
    """
        Test that submit_environmental_sensor_data returns success.
    """
    # Arrange
    client = client_with_mock_firestore
    payload = {
        "plantId": "plant123",
        "automation": {
            "fanOn": False,
            "lightOn":  False,
            "waterOn":  False
        },
        "profile": {
            "humidityMax": 200,
            "humidityMin": 100,
            "lightMax": 300,
            "lightMin": 100,
            "moistureMax": 500,
            "moistureMin": 50,
            "tempMax": 37,
            "tempMin": 23
        },
        "userId": "user123",
        "sensorRecordId": "2024-05-31T10:00:00",
        "lastUpdated": "2024-05-31T10:05:00Z",
        "sensors": {
            "soilMoisture": 55.0,
            "light": 120.0,
            "temp": 26.0,
            "humidity": 75.0
        }
    }

    # Patch `get_or_create_sensor` and `generate_log_id`
    with patch("routes.sensor.get_or_create_sensor", return_value="mock_sensor_id",), \
         patch("routes.sensor.generate_log_id", side_effect=[f"log_{i}" for i in range(4)]), \
         patch("routes.sensor.datetime") as mock_datetime:

        mock_now = datetime(2024, 5, 31, 10, 10)
        mock_datetime.utcnow.return_value = mock_now
        mock_datetime.strptime = datetime.strptime

        # Act
        response = client.post("/api/v1/sensor-data", json=payload)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["plantId"] == "plant123"
        assert data["message"].startswith("Successfully processed")
        assert len(data["createdLogs"]) == 4





