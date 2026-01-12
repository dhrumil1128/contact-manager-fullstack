import os
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
from sqlmodel import Field, SQLModel, Session, create_engine, select
from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import httpx
from datetime import datetime

# --- 1. Configuration and Setup ===============

# Load environment variables from .env file (if present)
# NOTE: For this code to run successfully, you must set HUNTER_API_KEY in your environment or .env file.
load_dotenv()

DATABASE_URL = "sqlite:///./contacts.db"
HUNTER_API_KEY = os.getenv("HUNTER_API_KEY")

engine = create_engine(DATABASE_URL, echo=False)

def create_db_and_tables():
    """Initializes the database and creates tables."""
    SQLModel.metadata.create_all(engine)

# --- 2. Database Model ===============

class Contact(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    email: str = Field(index=True, unique=True)
    phone: Optional[str] = None
    is_verified: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

# --- 3. Pydantic Schemas ===============

# Request Schemas (Input)
class ContactCreate(SQLModel):
    name: str
    email: str
    phone: Optional[str] = None

class ContactUpdate(SQLModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

# Response Schemas (Output)
class ContactRead(SQLModel):
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    is_verified: bool
    created_at: datetime

# --- 4. Hunter.io Integration Logic ===============

async def verify_email_task(contact_id: int, email: str, db_session: Session):
    """
    Asynchronously verifies the email using Hunter.io API and updates the DB.
    This function runs in the background.
    """
    if not HUNTER_API_KEY:
        print("Warning: HUNTER_API_KEY not set. Skipping email verification.")
        return

    hunter_url = f"https://api.hunter.io/v2/email-verifier?email={email}&api_key={HUNTER_API_KEY}"

    is_valid = False
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(hunter_url)
            response.raise_for_status() # Raises HTTPStatusError for 4xx/5xx responses

        data = response.json()
        
        # Hunter.io success structure check
        if data.get("data", {}).get("status") in ["valid", "deliverable"]:
            is_valid = True
            
    except httpx.HTTPStatusError as e:
        print(f"Hunter API HTTP Error for {email}: {e.response.status_code} - {e.response.text}")
    except httpx.RequestError as e:
        print(f"Hunter API Request Error for {email}: {e}")
    except Exception as e:
        print(f"Unexpected error during Hunter verification for {email}: {e}")

    # Update the database record (requires a new session context for background tasks)
    try:
        with Session(engine) as update_session:
            contact_to_update = update_session.get(Contact, contact_id)
            if contact_to_update:
                contact_to_update.is_verified = is_valid
                update_session.add(contact_to_update)
                update_session.commit()
                update_session.refresh(contact_to_update)
                print(f"Successfully updated verification status for Contact ID {contact_id} to {is_valid}")
    except Exception as e:
        print(f"Database update failed for Contact ID {contact_id}: {e}")


# --- Dependency Injection for Database Session ===============

def get_session():
    with Session(engine) as session:
        yield session

# --- 5. FastAPI Application Initialization ===============

app = FastAPI(
    title="Contact Manager API",
    version="1.0.0",
    on_startup=[create_db_and_tables]
)

# --- 7. CORS Configuration ===============
origins = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "*" # Allow all origins for development simplicity
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 6. API Endpoint Definitions ===============

# Endpoint 1: Create Contact
@app.post("/api/v1/contacts", response_model=ContactRead, status_code=status.HTTP_201_CREATED)
async def create_contact(
    contact: ContactCreate, 
    session: Session = Depends(get_session),
    background_tasks: BackgroundTasks = Depends(BackgroundTasks)
):
    # Check for duplicates (409 Conflict)
    existing = session.exec(select(Contact).where(Contact.email == contact.email)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email address '{contact.email}' already exists"
        )

    db_contact = Contact.model_validate(contact)
    session.add(db_contact)
    session.commit()
    session.refresh(db_contact)

    # Trigger background verification task
    if HUNTER_API_KEY:
        background_tasks.add_task(verify_email_task, db_contact.id, db_contact.email, session)
    else:
        print("Skipping background task as API key is missing.")

    return db_contact

# Endpoint 2: Retrieve All Contacts
@app.get("/api/v1/contacts", response_model=List[ContactRead])
async def read_contacts(session: Session = Depends(get_session)):
    contacts = session.exec(select(Contact)).all()
    return contacts

# Endpoint 3: Retrieve Single Contact
@app.get("/api/v1/contacts/{contact_id}", response_model=ContactRead)
async def read_contact(contact_id: int, session: Session = Depends(get_session)):
    contact = session.get(Contact, contact_id)
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contact with ID {contact_id} not found"
        )
    return contact

# Endpoint 4: Update Contact
@app.put("/api/v1/contacts/{contact_id}", response_model=ContactRead)
async def update_contact(
    contact_id: int, 
    contact_update: ContactUpdate, 
    session: Session = Depends(get_session)
):
    db_contact = session.get(Contact, contact_id)
    if not db_contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contact with ID {contact_id} not found"
        )

    update_data = contact_update.model_dump(exclude_unset=True)
    
    # Handle potential email conflict during update
    if 'email' in update_data and update_data['email'] != db_contact.email:
        existing = session.exec(select(Contact).where(Contact.email == update_data['email'])).first()
        if existing and existing.id != contact_id:
             raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Email address '{update_data['email']}' already exists for another contact."
            )

    for key, value in update_data.items():
        setattr(db_contact, key, value)

    session.add(db_contact)
    session.commit()
    session.refresh(db_contact)
    return db_contact

# Endpoint 5: Delete Contact
@app.delete("/api/v1/contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(contact_id: int, session: Session = Depends(get_session)):
    contact = session.get(Contact, contact_id)
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contact with ID {contact_id} not found"
        )
    session.delete(contact)
    session.commit()
    return None

# Endpoint 6: Manual Verification Debug Endpoint
@app.get("/api/v1/contacts/verify/{email}")
async def manual_verify_email(email: str, background_tasks: BackgroundTasks):
    if not HUNTER_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Hunter.io API Key is not configured. Cannot perform verification."
        )
        
    # Find the contact ID first
    with Session(engine) as session:
        contact = session.exec(select(Contact).where(Contact.email == email)).first()
        if not contact:
            return {"status": "error", "message": f"Contact with email {email} not found in database."}
            
        background_tasks.add_task(verify_email_task, contact.id, contact.email, session)
        return {"status": "success", "message": f"Verification task initiated for {email}."}
