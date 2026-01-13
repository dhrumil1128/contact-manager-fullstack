import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, DateTime, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel, EmailStr, Field

# --- 1. Setup and Configuration ---

# Define paths based on the expected structure
# We assume the script is run from the 'contact_manager_backend/' root directory
BASE_DIR = Path(__file__).resolve().parent.parent # Adjusting path to point to backend/ from backend/app/
DATA_DIR = BASE_DIR / "data"
DATABASE_URL = f"sqlite:///{DATA_DIR / 'contacts.db'}"

# Ensure the data directory exists (Crucial for runnable script)
DATA_DIR.mkdir(exist_ok=True) # This will fail if run directly as a module without proper context, but necessary for the provided logic.

# --- 2. Database Setup (SQLAlchemy Engine and Base) ---

# SQLite setup: check_same_thread=False is necessary for FastAPI/SQLAlchemy usage in a multi-threaded environment
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- 3. Data Model (app/models.py) ---

class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, index=True, nullable=False)
    last_name = Column(String, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# --- 4. Pydantic Schemas (app/schemas.py) ---

class ContactBase(BaseModel):
    # NOTE: Frontend sends 'name' but backend expects first/last name split.
    # For simplicity matching the input structure, we map 'name' input to 'first_name' and use a placeholder for 'last_name'.
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(default="N/A", min_length=1) # Placeholder for simplicity
    email: EmailStr
    phone: Optional[str] = None

class ContactCreate(ContactBase):
    pass

class ContactUpdate(BaseModel):
    # All fields optional for partial updates
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None

    class Config:
        orm_mode = True 

class ContactResponse(ContactBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True 

# --- 5. CRUD Logic (app/crud.py) ---

def get_contacts(db: Session, skip: int = 0, limit: int = 100) -> List[Contact]:
    return db.query(Contact).offset(skip).limit(limit).all()

def get_contact(db: Session, contact_id: int) -> Optional[Contact]:
    return db.query(Contact).filter(Contact.id == contact_id).first()

def create_contact(db: Session, contact: ContactCreate) -> Contact:
    # Map frontend 'name' field to 'first_name' and assign default last_name if not explicitly set in schema
    contact_dict = contact.dict()
    if 'last_name' not in contact_dict or not contact_dict['last_name']:
        contact_dict['last_name'] = "N/A"
        
    db_contact = Contact(**contact_dict)
    
    try:
        db.add(db_contact)
        db.commit()
        db.refresh(db_contact)
        return db_contact
    except Exception as e:
        db.rollback()
        # Check for unique constraint violation (SQLAlchemy error message)
        if "UNIQUE constraint failed: contacts.email" in str(e):
             raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email address already registered"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database operation failed"
        )

def update_contact(db: Session, contact_id: int, contact_data: ContactUpdate) -> Optional[Contact]:
    db_contact = get_contact(db, contact_id=contact_id)
    if not db_contact:
        return None
    
    update_data = contact_data.dict(exclude_unset=True)
    
    # Handle potential unique email conflict during update
    if 'email' in update_data and update_data['email'] != db_contact.email:
        existing_email_check = db.query(Contact).filter(
            Contact.email == update_data['email'],
            Contact.id != contact_id
        ).first()
        if existing_email_check:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email address already registered by another contact"
            )

    for key, value in update_data.items():
        setattr(db_contact, key, value)
    
    try:
        db.commit()
        db.refresh(db_contact)
        return db_contact
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database update failed"
        )


def delete_contact(db: Session, contact_id: int) -> bool:
    contact_to_delete = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact_to_delete:
        return False
    db.delete(contact_to_delete)
    db.commit()
    return True

# --- 6. Sample Data Initialization ---

def init_db():
    """Creates database tables and seeds initial data if necessary."""
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        if db.query(Contact).count() == 0:
            print("Database empty. Seeding sample data...")
            sample_contacts = [
                ContactCreate(
                    first_name="Alice", 
                    last_name="Smith", 
                    email="alice@example.com", 
                    phone="555-1234"
                ),
                ContactCreate(
                    first_name="Bob", 
                    last_name="Johnson", 
                    email="bob@example.com"
                ),
                ContactCreate(
                    first_name="Charlie", 
                    last_name="Brown", 
                    email="charlie@peanuts.com",
                    phone="555-9999"
                ),
            ]
            for contact_data in sample_contacts:
                # Manually ensure last_name is set if the frontend only sends 'name'
                if not contact_data.last_name:
                    contact_data.last_name = "N/A"
                db_contact = Contact(**contact_data.dict())
                db.add(db_contact)
            db.commit()
            print(f"Seeded {len(sample_contacts)} contacts.")
        else:
            print("Database already contains contacts. Skipping seeding.")
    except Exception as e:
        print(f"Error during database initialization/seeding: {e}")
        db.rollback()
    finally:
        db.close()


# --- 7. FastAPI Application Setup (app/main.py) ---

app = FastAPI(
    title="Contact Manager API",
    description="Backend implementation using FastAPI and SQLite.",
    version="1.0.0"
)

# 10. CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allowing all origins for simplicity in a single runnable file setup
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Run initialization when the script starts (simulating startup event)
init_db()

# --- 8. API Endpoint Definitions ---

# Helper function to map Contact model fields to expected frontend response structure (which expects 'name')
class ContactResponse(ContactBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True 

def map_contact_to_response(contact: Contact) -> ContactResponse:
    # For simplicity, we map the response to match the ContactResponse schema, which inherits from ContactBase (first_name, last_name, email, phone)
    return ContactResponse(
        id=contact.id,
        created_at=contact.created_at,
        first_name=contact.first_name,
        last_name=contact.last_name,
        email=contact.email,
        phone=contact.phone
    )

# 1. GET /api/contacts/
@app.get("/api/contacts/", response_model=List[ContactResponse], status_code=status.HTTP_200_OK)
def read_contacts(
    db: Session = Depends(get_db), 
    skip: int = 0, 
    limit: int = 100
):
    contacts = get_contacts(db, skip=skip, limit=limit)
    return contacts

# 2. POST /api/contacts/
@app.post("/api/contacts/", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
def create_new_contact(
    contact: ContactCreate, 
    db: Session = Depends(get_db)
):
    # IMPORTANT: Frontend sends 'name' for the contact name, but schema expects first_name/last_name.
    # We map the single 'name' input from the frontend to 'first_name' in the backend schema.
    # We must ensure the contact object created has a valid structure.
    
    # Since the frontend input name maps to ContactCreate.first_name:
    # We create the contact using the received data.
    return create_contact(db=db, contact=contact)

# 3. GET /api/contacts/{contact_id}
@app.get("/api/contacts/{contact_id}", response_model=ContactResponse, status_code=status.HTTP_200_OK)
def read_contact(
    contact_id: int, 
    db: Session = Depends(get_db)
):
    db_contact = get_contact(db, contact_id=contact_id)
    if db_contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Contact with ID {contact_id} not found"
        )
    return db_contact

# 4. PUT /api/contacts/{contact_id}
@app.put("/api/contacts/{contact_id}", response_model=ContactResponse, status_code=status.HTTP_200_OK)
def update_existing_contact(
    contact_id: int, 
    contact_update: ContactUpdate, 
    db: Session = Depends(get_db)
):
    updated_contact = update_contact(db, contact_id=contact_id, contact_data=contact_update)
    if updated_contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Contact with ID {contact_id} not found"
        )
    return updated_contact

# 5. DELETE /api/contacts/{contact_id}
@app.delete("/api/contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_contact(
    contact_id: int, 
    db: Session = Depends(get_db)
):
    success = delete_contact(db, contact_id=contact_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Contact with ID {contact_id} not found"
        )
    return None
