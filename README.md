This project sets up a full-stack Contact Manager. The frontend is pure HTML/CSS/JS, designed to interact with the FastAPI backend. The backend uses SQLite for persistence and exposes standard CRUD endpoints under /contacts.

**Project Structure:**
```
contact-manager-fullstack/
├── backend/
│   ├── main.py          # FastAPI application, database setup (SQLite), and API endpoints
│   └── requirements.txt # Python dependencies
├── frontend/
│   ├── index.html       # Main structure and UI layout
│   ├── style.css        # Styling for the application
│   └── script.js        # Frontend logic (AJAX calls to the backend)
└── README.md
```

**Backend Setup (FastAPI/SQLite):**
1. Navigate to the `backend` directory.
2. Install dependencies: `pip install -r requirements.txt`
3. Run the server: `uvicorn main:app --reload` (The database file `contacts.db` will be created automatically upon first run).

**Frontend Setup (Static Files):**
The frontend is configured to communicate with `http://127.0.0.1:8000/contacts` in `script.js`. For local testing, ensure the backend is running before opening `index.html`.

**Deployment Instructions (Vercel):**
Vercel is excellent for deploying static frontends. 
1. **Frontend Deployment:** Connect the GitHub repository to Vercel. Configure the build step to serve the contents of the `frontend/` directory as static assets. Since there is no framework build step (like React/Vue), Vercel simply needs to know where the static files are located. If Vercel detects a root deployment, ensure `index.html` is accessible at the root path. *Note: For successful deployment, the API_BASE_URL in `frontend/script.js` must be updated to point to the externally hosted backend URL.*
