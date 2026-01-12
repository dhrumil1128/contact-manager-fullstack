# Contact Manager Fullstack Project

This repository contains a complete Contact Manager application built using a decoupled architecture:

*   **Frontend:** Vanilla HTML, CSS, and JavaScript for a responsive user interface.
*   **Backend:** Python FastAPI providing a RESTful API backed by SQLite.
*   **Automation:** Backend includes logic to interact with the GitHub REST API using a server-side environment variable (`GITHUB_TOKEN`).

## Project Structure
The project is structured into two main directories:

```
/contact-manager-project
├── /frontend
│   └── index.html      (Contains embedded HTML, CSS, and JavaScript logic)
└── /backend
    ├── main.py         (FastAPI application, models, endpoints, and GitHub logic)
    └── requirements.txt (Python dependencies)
```

## Environment Variables
The backend requires one environment variable for the GitHub automation feature.

| Variable Name | Purpose |
| :--- | :--- |
| `GITHUB_TOKEN` | Personal Access Token (PAT) required by the FastAPI backend to authenticate against the GitHub REST API for automation tasks. |

**Example (Linux/macOS):**
```bash
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

## How To Run Locally

### Step 1: Setup Backend Environment
1.  Navigate to the backend directory:
    ```bash
    cd backend
    ```
2.  Install required Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Step 2: Set Environment Variable and Start Backend
1.  Set your GitHub token in your current shell session:
    ```bash
    export GITHUB_TOKEN="your_actual_github_pat_here"
    ```
2.  Start the FastAPI server using Uvicorn:
    ```bash
    uvicorn main:app --reload --host 127.0.0.1 --port 8000
    ```
    The backend will run on `http://127.0.0.1:8000`.

### Step 3: Run Frontend
1.  Navigate to the frontend directory:
    ```bash
    cd ../frontend
    ```
2.  Open `index.html` directly in a web browser.