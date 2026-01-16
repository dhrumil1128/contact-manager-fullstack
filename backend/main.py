import datetime
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, DateTime, UniqueConstraint
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel, EmailStr

# --- 1. Database Configuration and Model (SQLAlchemy) ---

# Database URL for SQLite
SQLALCHEMY_DATABASE_URL = "sqlite:///./contacts.db"

# Create engine
# check_same_thread=False is necessary for SQLite access from multiple threads (like FastAPI workers)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Create session local
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative models
Base = declarative_base()

# Database Model: Contact
class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    phone = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Explicitly define uniqueness constraint for clarity
    __table_args__ = (UniqueConstraint('email', name='_email_uc'),)

# Initialize database (create tables if they don't exist)
Base.metadata.create_all(bind=engine)


# --- 2. Pydantic Schemas ---

class ContactCreate(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None

class ContactUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None

class ContactResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    created_at: datetime.datetime

    class Config:
        # Important for mapping ORM objects directly to Pydantic models
        orm_mode = True 


# --- 3. Dependency Injection ---

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- 4. FastAPI Application Setup and CORS ---

app = FastAPI(title="Contact Manager API")

# CORS Configuration (Section 6)
origins = [
    "http://localhost",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allow specified origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# --- 5. API Endpoint Paths, HTTP Methods, and Logic ---

# 1. GET /contacts: Retrieve all contacts
@app.get("/contacts", response_model=List[ContactResponse])
def read_contacts(db: Session = Depends(get_db)):
    contacts = db.query(Contact).all()
    return contacts

# 2. POST /contacts: Create a new contact
@app.post("/contacts", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
def create_contact(contact_in: ContactCreate, db: Session = Depends(get_db)):
    # Check for duplicate email (409 Conflict)
    existing_contact = db.query(Contact).filter(Contact.email == contact_in.email).first()
    if existing_contact:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email address already exists"
        )
    
    # Create new contact instance
    db_contact = Contact(
        name=contact_in.name,
        email=contact_in.email,
        phone=contact_in.phone
    )
    
    db.add(db_contact)
    try:
        db.commit()
        db.refresh(db_contact)
        return db_contact
    except Exception:
        db.rollback()
        # Fallback for unexpected DB errors not caught by unique constraint check
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during creation"
        )

# 3. GET /contacts/{contact_id}: Retrieve single contact
@app.get("/contacts/{contact_id}", response_model=ContactResponse)
def read_contact(contact_id: int, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contact with ID {contact_id} not found"
        )
    return contact

# 4. PATCH /contacts/{contact_id}: Update existing contact
@app.patch("/contacts/{contact_id}", response_model=ContactResponse)
def update_contact(contact_id: int, contact_update: ContactUpdate, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    
    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contact with ID {contact_id} not found"
        )

    # Only process fields explicitly provided in the request body
    update_data = contact_update.dict(exclude_unset=True)

    # Check for email conflict if email is being updated
    if 'email' in update_data and update_data['email'] != contact.email:
        existing_contact = db.query(Contact).filter(Contact.email == update_data['email']).first()
        if existing_contact:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email address already exists"
            )

    for key, value in update_data.items():
        setattr(contact, key, value)
    
    try:
        db.commit()
        db.refresh(contact)
        return contact
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during update"
        )

# 5. DELETE /contacts/{contact_id}: Delete contact
@app.delete("/contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact(contact_id: int, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    
    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contact with ID {contact_id} not found"
        )
    
    db.delete(contact)
    try:
        db.commit()
        return None # Returns 204 No Content
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during deletion"
        )
