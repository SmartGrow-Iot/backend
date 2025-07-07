# SmartGrow FastAPI Backend
Persist data using Firebase Firestore. Backend server run on FastAPI, deployed on Render.

This is the backend server for the SmartGrow system. It is a FastAPI application designed to receive data from IoT devices, store it in Firebase Firestore, and expose a REST API for web and mobile team to consume.

## 🌐 Server Address
https://test-server-owq2.onrender.com

## 🌱 Features

- **Plant API:** Logic to create a plant in the system, and get plant data.
- **Sensor API:** Logic to submit sensor data (moisture, temperature, light, humidity) from ESP32, and get sensor data for real-time monitoring.
- **Action Log API:** Logic to record action logs (water, light, fan), either downstream from ESP32 actuator control, or upstream by user manual control.
- **User API:** Logic to register a user, and get user profile settings.
- **API Docs:**: Swagger UI docs for quick reference, available at <server-address>/docs.
- **Caching:** Utilize LRU cache with time-to-live (TTL) of 60 seconds to store frequently accessed data, to reduce Firestore read document limit.
- **MQTT service:** Publish and subscribe (Pub/Sub) to MQTT broker for actuator control command.
- **Ping service:** Ping to server root endpoint every 10 minutes to keep it running 24/7, as Render free plan spins down server afer 15 minutes without receiving inbound traffic.
- **Data Cleanup service:** Daily clean up sensor and action logs prior to last one week (e.g. today Friday, delete all logs prior to last Friday), to optimize Firestore data storage limit.

## 🚀 Getting Started

### Prerequisites

- [Python](https://www.python.org/) (v3.8 or newer)
- [pip](https://pypi.org/project/pip/) (comes with Python)

### Setup Instructions

1. **Clone the repository:**

   ```sh
   git clone <your-repo-url>
   ```

2. **Install dependencies:**

   ```sh
   pip install -r requirements.txt
   ```

3. **Configure .env file for local setup:**

    ```sh
   FIREBASE_CREDENTIALS_PATH=<your-firebase-adminsdk-service-key>
   TEST_MODE="true"
   ADA_BROKER = "io.adafruit.com"
   ADA_PORT = "1883"
   ADA_USERNAME = <your-adafruit-broker-username>
   ADA_KEY = <your-adafruit-broker-private-key>
   ```

4. **Start the development server:**

   ```sh
   fastapi dev main.py
   ```

5. **Open your browser and visit:**
   ```
   http://localhost:8000
   ```

## 📁 Project Structure
- `main.py` - Handles application startup logic, main entry point
- `schema.py` - Pydantic models for user, plant, sensor and action logs modules
- `firebase_config.py` — Handles Firebase Firestore initialization logic
- `auth.py` — Handles Firebase authentication logic
- `/routes` — Core APIs 
- `/services` — Startup async services 
- `/tests` — pytest unit test

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first.

## 📄 License

© 2025 SmartGrow. All rights reserved.

---

**Enjoy growing smarter with SmartGrow!**

