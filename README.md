# VitalApp

VitalApp is a Django-based application designed to manage blood analyzer devices, test runs, and metrics across multiple data sources (factory, cloud, and legacy). It provides a robust API for device management, test data synchronization, and detailed logging.

## Features

- **Device Management**: Create, read, update, and delete blood analyzer devices with unique device IDs, types, statuses, locations, manufacturing dates, calibration details, and assigned technicians.
- **Data Sources**: Support for multiple data sources (factory, cloud, legacy) with clear relationships to devices and test runs.
- **Test Runs & Metrics**: Each device can have multiple test runs, each with detailed metrics (e.g., hemoglobin, WBC, etc.).
- **Sync Process**: Background synchronization of data from different sources, with comprehensive logging and status/history tracking.
- **API Security**: Secure API endpoints with session and token-based authentication.
- **Test Data Management**: Commands to clear and repopulate test data, ensuring no duplicate entries.
- **Extensibility**: Modular code structure for easy addition of new source types or device types.
- **API Documentation**: Interactive API documentation using Swagger/OpenAPI.

## Setup

### Prerequisites

- Python 3.8 or higher
- Django 3.2 or higher
- Django REST Framework
- Celery
- Redis (for Celery broker and result backend)
- drf-yasg (for API documentation)

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd VitalApp
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up the database:
   ```bash
   python manage.py migrate
   ```

5. Start the development server:
   ```bash
   python manage.py runserver
   ```

6. Start Celery worker:
   ```bash
   celery -A vital_tools worker -l info
   ```

7. Start Celery beat (for scheduled tasks):
   ```bash
   celery -A vital_tools beat -l info
   ```

## Usage

### API Documentation

The API documentation is available at:
- Swagger UI: `/api/docs/`
- ReDoc: `/api/redoc/`

These interactive documentation pages allow you to:
- Browse all available API endpoints
- View detailed request/response schemas
- Test API calls directly from the browser
- View authentication requirements

### API Endpoints

- **Devices**: `/api/devices/`
  - List all devices: `GET /api/devices/`
  - Create new device: `POST /api/devices/`
  - Get device details: `GET /api/devices/{device_id}/`
  - Update device: `PUT /api/devices/{device_id}/`
  - Delete device: `DELETE /api/devices/{device_id}/`
  - Sync device: `POST /api/devices/{device_id}/sync/`
  - Get sync status: `GET /api/devices/{device_id}/sync_status/`
  - Get sync history: `GET /api/devices/{device_id}/sync_history/`

- **Sync Logs**: `/api/sync-logs/`
  - List all sync logs: `GET /api/sync-logs/`
  - Filter by device: `GET /api/sync-logs/?device_id={device_id}`
  - Filter by status: `GET /api/sync-logs/?status={status}`
  - Sort by timestamp: `GET /api/sync-logs/?ordering=-timestamp`

- **Test Runs**: `/api/test-runs/`
  - List all test runs: `GET /api/test-runs/`
  - Create new test run: `POST /api/test-runs/`
  - Get test run details: `GET /api/test-runs/{id}/`
  - Get test run metrics: `GET /api/test-runs/{id}/metrics/`
  - Filter by device: `GET /api/test-runs/?device_id={device_id}`
  - Filter by run type: `GET /api/test-runs/?run_type={run_type}`

### Authentication

The API uses Django REST Framework's session and token authentication. Ensure you are logged in or provide a valid token in the `Authorization` header.

To obtain a token:
1. Login via the admin interface or browsable API
2. Or use the token endpoint: `POST /api-token-auth/` with username and password

### Test Data

To clear and repopulate test data, use the following commands:
```bash
python manage.py clear_test_data
python manage.py populate_test_data
```

## Testing

Run the tests using:
```bash
python manage.py test devices.tests
```

## Contributing

1. Fork the repository
2. Create a new branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.