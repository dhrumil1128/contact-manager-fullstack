import sqlite3
import json
from typing import List, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
import os # Needed for environment variable access
import httpx # Needed for GitHub API calls

# --- Configuration ---
DATABASE_NAME = "contacts.db"

# --- 2. Database Setup & Initialization ---

def initialize_db():
    """Creates the database file and the contacts table if they don't exist."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            phone TEXT
        );
    """)
    conn.commit()
    conn.close()

# --- 3. Pydantic Schemas ---

class ContactCreate(BaseModel):
    """Schema for creating a new contact (used for POST and PUT body)."""
    name: str = Field(..., min_length=1)
    email: EmailStr
    phone: Optional[str] = None

class ContactUpdate(BaseModel):
    """Schema for partial updates (Not strictly used for PUT based on plan, but defined)."""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None

class Contact(ContactCreate):
    """Schema for returning a contact record, including the ID."""
    id: int

# --- 4. Database Utility Functions ---

def db_get_all_contacts() -> List[Contact]:
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row # Allows accessing columns by name
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, phone FROM contacts")
    rows = cursor.fetchall()
    conn.close()
    
    contacts = []
    for row in rows:
        # Convert sqlite row to dictionary and then to Pydantic model
        contact_data = dict(row)
        contacts.append(Contact(**contact_data))
    return contacts

def db_get_contact_by_id(contact_id: int) -> Optional[Contact]:
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, phone FROM contacts WHERE id = ?", (contact_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return Contact(**dict(row))
    return None

def db_create_contact(contact_data: ContactCreate) -> Contact:
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO contacts (name, email, phone) VALUES (?, ?, ?)",
            (contact_data.name, contact_data.email, contact_data.phone)
        )
        conn.commit()
        new_id = cursor.lastrowid
        
        # Retrieve the newly created contact to return the full object
        cursor.execute("SELECT id, name, email, phone FROM contacts WHERE id = ?", (new_id,))
        row = cursor.fetchone()
        conn.close()
        return Contact(**dict(row))
    except sqlite3.IntegrityError:
        conn.close()
        raise
    except Exception:
        conn.close()
        raise

def db_update_contact(contact_id: int, contact_data: ContactCreate) -> Optional[Contact]:
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    # Check if contact exists first
    cursor.execute("SELECT id FROM contacts WHERE id = ?", (contact_id,))
    if not cursor.fetchone():
        conn.close()
        return None

    try:
        cursor.execute(
            "UPDATE contacts SET name = ?, email = ?, phone = ? WHERE id = ?",
            (contact_data.name, contact_data.email, contact_data.phone, contact_id)
        )
        conn.commit()
        
        # Retrieve updated contact
        cursor.execute("SELECT id, name, email, phone FROM contacts WHERE id = ?", (contact_id,))
        row = cursor.fetchone()
        conn.close()
        return Contact(**dict(row))
    except sqlite3.IntegrityError:
        conn.close()
        raise
    except Exception:
        conn.close()
        raise

def db_delete_contact(contact_id: int) -> bool:
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
    conn.commit()
    deleted_count = cursor.rowcount
    conn.close()
    return deleted_count > 0

# --- 1. FastAPI Application Setup ---

app = FastAPI(
    title="Contact Manager API",
    description="Backend implementation using FastAPI and SQLite.",
    version="1.0.0"
)

# --- 6. CORS Configuration ---
origins = [
    "*" # Allowing all origins for development simplicity as per plan context
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initializes the database on application startup."""
    initialize_db()
    
# --- GitHub Automation Endpoint (As required by summary) ---

@app.post("/github/sync", summary="Trigger GitHub Sync via Server Token")
async def trigger_github_sync():
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="GITHUB_TOKEN environment variable not set.")

    # Placeholder for actual GitHub API interaction
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    
    # Example: Fetching user data to prove token access
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("https://api.github.com/user", headers=headers)
            response.raise_for_status()
            user_data = response.json()
            return {"message": "GitHub sync initiated successfully", "user": user_data['login']}
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"GitHub API Error: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error during GitHub sync: {str(e)}")

# --- 4. API Endpoint Paths and HTTP Methods ---

# 1. POST /contacts: Create a new contact
@app.post("/contacts", response_model=Contact, status_code=status.HTTP_201_CREATED, summary="Create a new contact")
async def create_contact(contact: ContactCreate):
    try:
        new_contact = db_create_contact(contact)
        return new_contact
    except sqlite3.IntegrityError:
        # 409 Conflict: Duplicate email
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Contact with email '{contact.email}' already exists"
        )

# 2. GET /contacts: Retrieve all contacts
@app.get("/contacts", response_model=List[Contact], summary="Retrieve all contacts")
async def get_all_contacts():
    return db_get_all_contacts()

# 3. GET /contacts/{contact_id}: Retrieve a single contact by ID
@app.get("/contacts/{contact_id}", response_model=Contact, summary="Retrieve a contact by ID")
async def get_contact(contact_id: int):
    contact = db_get_contact_by_id(contact_id)
    if contact is None:
        # 404 Not Found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contact with ID {contact_id} not found"
        )
    return contact

# 4. PUT /contacts/{contact_id}: Fully update an existing contact by ID
@app.put("/contacts/{contact_id}", response_model=Contact, summary="Fully update an existing contact")
async def update_contact(contact_id: int, contact_update_data: ContactCreate):
    # PUT requires full replacement data (using ContactCreate schema as per plan)
    
    # Check existence and attempt update in one go via utility function
    try:
        updated_contact = db_update_contact(contact_id, contact_update_data)
    except sqlite3.IntegrityError:
        # 409 Conflict: Duplicate email resulting from update
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Update failed: Email '{contact_update_data.email}' is already in use by another contact."
        )
    
    if updated_contact is None:
        # 404 Not Found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contact with ID {contact_id} not found"
        )
    
    return updated_contact


# 5. DELETE /contacts/{contact_id}: Delete a contact by ID
@app.delete("/contacts/{contact_id}", summary="Delete a contact by ID")
async def delete_contact(contact_id: int):
    success = db_delete_contact(contact_id)
    
    if not success:
        # 404 Not Found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contact with ID {contact_id} not found"
        )
    
    # Response matching the plan example: {"message": "Contact deleted"}
    return {"message": "Contact deleted"}
