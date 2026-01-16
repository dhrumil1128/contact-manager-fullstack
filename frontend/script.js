const API_BASE_URL = 'http://127.0.0.1:8000/contacts';

let contacts = [];
let isEditing = false;
let currentContactId = null;

// DOM Elements
const form = document.getElementById('contact-form');
const messageArea = document.getElementById('message-area');
const loadingIndicator = document.getElementById('loading-indicator');
const tableBody = document.querySelector('#contacts-table tbody');
const submitBtn = document.getElementById('form-submit-btn');
const cancelEditBtn = document.getElementById('cancel-edit-btn');

// --- Utility Functions ---

function showMessage(message, type = 'success') {
    messageArea.textContent = message;
    messageArea.className = `message ${type}`;
    setTimeout(() => {
        messageArea.textContent = '';
        messageArea.className = '';
    }, 3000);
}

function setLoading(isLoading) {
    loadingIndicator.classList.toggle('hidden', !isLoading);
}

// --- API Interaction ---

async function fetchContacts() {
    setLoading(true);
    try {
        const response = await fetch(API_BASE_URL);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        contacts = await response.json();
        renderContactList();
    } catch (error) {
        showMessage(`Failed to load contacts: ${error.message}`, 'error');
    } finally {
        setLoading(false);
    }
}

async function handleFormSubmit(event) {
    event.preventDefault();
    setLoading(true);

    const name = document.getElementById('name').value;
    const email = document.getElementById('email').value;
    const phone = document.getElementById('phone').value;
    const payload = { name, email, phone };

    try {
        let response;
        if (isEditing) {
            // PUT /contacts/{currentContactId}
            response = await fetch(`${API_BASE_URL}/${currentContactId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        } else {
            // POST /contacts/
            response = await fetch(API_BASE_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        }

        if (!response.ok) throw new Error(`Operation failed: ${response.statusText}`);
        
        await fetchContacts(); // Refresh list
        form.reset();
        showMessage(`Contact ${isEditing ? 'updated' : 'added'} successfully!`)
        resetFormState();

    } catch (error) {
        showMessage(`Error during save: ${error.message}`, 'error');
    } finally {
        setLoading(false);
    }
}

async function deleteContact(id) {
    if (!confirm("Are you sure you want to delete this contact?")) return;
    
    setLoading(true);
    try {
        const response = await fetch(`${API_BASE_URL}/${id}`, { method: 'DELETE' });
        
        if (!response.ok) throw new Error(`Deletion failed: ${response.statusText}`);
        
        showMessage("Contact deleted successfully.");
        await fetchContacts(); // Refresh list
    } catch (error) {
        showMessage(`Error deleting contact: ${error.message}`, 'error');
    } finally {
        setLoading(false);
    }
}

// --- UI Rendering ---

function renderContactList() {
    tableBody.innerHTML = ''; // Clear existing rows
    
    if (contacts.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="4">No contacts found.</td></tr>';
        return;
    }

    contacts.forEach(contact => {
        const row = tableBody.insertRow();
        row.innerHTML = `
            <td>${contact.name}</td>
            <td>${contact.email}</td>
            <td>${contact.phone || 'N/A'}</td>
            <td>
                <button onclick="startEdit(${contact.id})">Edit</button>
                <button onclick="deleteContact(${contact.id})">Delete</button>
            </td>
        `;
    });
}

function startEdit(id) {
    const contactToEdit = contacts.find(c => c.id === id);
    if (!contactToEdit) return;

    isEditing = true;
    currentContactId = id;
    
    // Populate form
    document.getElementById('name').value = contactToEdit.name;
    document.getElementById('email').value = contactToEdit.email;
    document.getElementById('phone').value = contactToEdit.phone || '';
    
    // Update UI controls
    submitBtn.textContent = 'Save Changes';
    cancelEditBtn.classList.remove('hidden');
    document.querySelector('#contact-form-section h2').textContent = `Edit Contact (ID: ${id})`;}

function resetFormState() {
    isEditing = false;
    currentContactId = null;
    submitBtn.textContent = 'Add Contact';
    cancelEditBtn.classList.add('hidden');
    document.querySelector('#contact-form-section h2').textContent = 'Add New Contact';
}

// --- Initialization ---

window.onload = () => {
    form.addEventListener('submit', handleFormSubmit);
    cancelEditBtn.addEventListener('click', () => {
        form.reset();
        resetFormState();
    });
    fetchContacts();
};

// Expose functions to global scope for inline HTML event handlers
window.deleteContact = deleteContact;
window.startEdit = startEdit;
