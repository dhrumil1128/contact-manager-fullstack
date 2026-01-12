# Contact Manager Project

This project implements a full-stack Contact Manager application using modern web technologies and a Python backend for data persistence and external API integration.

## Project Structure
The project is organized into two main directories:
```
/contact-manager-project/
├── .env                      # Environment variables for backend and local configuration
├── requirements.txt          # Python dependencies
├── backend/
│   ├── main.py               # FastAPI application, routing, and core logic
│   └── contacts.db           # SQLite database file (created on first run)
└── frontend/
    ├── index.html            # Contains HTML, embedded CSS (Glassmorphism, Dark/Light Mode), and JavaScript logic
```

## Key Features
*   **Frontend:** Modern UI utilizing CSS Grid, Glassmorphism effects, and dynamic Dark/Light mode switching.
*   **Backend:** Python FastAPI serving a REST API.
*   **Database:** Persistent storage using SQLite.
*   **Email Verification:** Asynchronous background task calls the Hunter.io Email Verifier API to check contact validity.

## Environment Variables
A single `.env` file must be created in the root directory (`/contact-manager-project/`) to configure the backend:

| Variable Name | Purpose |
| :--- | :--- |
| `HUNTER_API_KEY` | Your secret API key from Hunter.io, used by the FastAPI backend. |
| `DATABASE_URL` | Connection string for SQLite. Use `sqlite:///./contacts.db` for local testing. |

## API Integration Notes

### Frontend to Backend Communication
The Vanilla JavaScript frontend communicates exclusively with the FastAPI backend running locally on port 8000.

| Action | HTTP Method | Backend Endpoint (v1) | Payload (JSON) |
| :--- | :--- | :--- | :--- |
| Add Contact | `POST` | `/api/v1/contacts` | `{ "name": "...", "email": "...", "phone": "..." }` |
| Get Contacts | `GET` | `/api/v1/contacts` | None |
| Delete Contact | `DELETE` | `/api/v1/contacts/{contact_id}` | None |

### Backend to External API (Hunter.io)
When a contact is created, the backend immediately queues a background task to verify the email using the `HUNTER_API_KEY`. The contact's `is_verified` status in the SQLite database is updated based on the external API response.

## How To Run Locally

Follow these steps sequentially to get the full system running:

### Step 1: Setup Project Structure and Files
1.  Create the root directory and place the files as structured above.
2.  Place the provided HTML/CSS/JS code into `/frontend/index.html`.
3.  Place the provided Python code into `/backend/main.py`.

### Step 2: Configure Environment
1.  Create the `.env` file in the root directory with your `HUNTER_API_KEY`.
2.  **Frontend Update:** Open `/frontend/index.html` and ensure the JavaScript section sets the API base URL to the backend's local address:
    ```javascript
    const API_BASE = 'http://localhost:8000'; 
    // Ensure any old Hunter API key definitions in the JS are removed/commented out.
    ```

### Step 3: Install Dependencies
Run the following command from the root directory:
```bash
pip install -r requirements.txt
```

### Step 4: Run Services
1.  **Start Backend Server:** Run the FastAPI application from the root directory:
    ```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
    ```
2.  **Start Frontend:** Open `/frontend/index.html` directly in your web browser.