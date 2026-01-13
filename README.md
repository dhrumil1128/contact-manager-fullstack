# Contact Manager Project

## Project Structure
The project is separated into two main directories: `frontend` (for static files) and `backend` (for Python/FastAPI application).

```
contact-manager-fullstack/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # Contains FastAPI application, models, schemas, and CRUD logic
│   │   ├── database.py      # SQLAlchemy setup (Engine, SessionLocal) (Note: Integrated into main.py for single file deployment)
│   │   └── schemas.py       # Pydantic validation models (Note: Integrated into main.py for single file deployment)
│   ├── contacts.db          # SQLite database file (created on first run)
│   ├── requirements.txt     # Python dependencies
│   └── README.md
│
└── index.html           # Main HTML structure (containing embedded CSS/JS)
```

## Environment Variables
For this local setup, environment variables are minimal, primarily used to configure the database path, though hardcoded in the provided backend script for immediate runnability.

| Variable Name | Location | Purpose | Notes |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | `.env` (Optional, used in `backend/app/database.py`) | Specifies the SQLite connection string. | Defaulted to `./contacts.db` in the provided code. |

To use `.env` files for configuration (recommended for production/Vercel deployment):
1. Create a `.env` file in the root of the `backend/` directory.
2. Install `python-dotenv` (`pip install python-dotenv`).
3. Load variables in `backend/app/main.py` using `from dotenv import load_dotenv; load_dotenv()`.

## API Integration Notes
The frontend (Vanilla JS) communicates directly with the FastAPI backend.

1.  **Base URL**: The frontend JavaScript assumes the backend is running locally on port 8000: `http://127.0.0.1:8000`.
2.  **CORS**: The FastAPI backend is configured to accept requests from common local frontend serving ports (e.g., 5500) and the backend's own port (8000). If you serve the frontend from a different port (e.g., 3000 for a React dev server), you must update the `origins` list in `backend/app/main.py`.
3.  **Data Contract**: The frontend expects JSON payloads for POST/PUT operations and receives JSON arrays or objects from GET operations, matching the Pydantic schemas defined in the backend.

## How To Run Locally
This process requires Python (3.8+) and a tool to serve the static HTML files (like a simple local web server).

### Step 1: Backend Setup and Execution (FastAPI/SQLite)

1.  **Navigate to Backend Directory**:
    ```bash
    cd contact-manager-fullstack/backend
    ```

2.  **Create Virtual Environment (Recommended)**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use: .\venv\Scripts\activate
    ```

3.  **Install Dependencies**:
    ```bash
    pip install fastapi uvicorn[standard] sqlalchemy pydantic python-dotenv
    ```

4.  **Run the Server**:
    ```bash
    uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
    ```

### Step 2: Frontend Setup and Execution (HTML/CSS/JS)

1.  **Navigate to Frontend Directory** (or stay in root if serving from root):
    ```bash
    cd ../frontend # If following the structure strictly
    ```

2.  **Serve Static Files** (e.g., using Python's built-in server):
    ```bash
    python -m http.server 5500
    ```

3.  **Access the Application**:
    Open your web browser and navigate to:
    ```
    http://127.0.0.1:5500
    ```

(Note: The provided structure places `index.html` at the root, and backend files in `backend/app/`.)