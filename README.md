# 🛒 ShelfCam Backend - Staff & Inventory Assignment System

AI-powered FastAPI backend for real-time **retail shelf monitoring and staff assignment**, developed for Walmart Sparkathon 2025. This system enables secure role-based staff management, intelligent shelf staff assignment tracking, and inventory monitoring.

---

## 🚀 Features

### 👥 Staff Management
- JWT-protected login system with roles: `staff`, `manager`, `admin`
- Staff profile with:
  - `employee_id` (string, primary)
  - `username`, `email`, `phone`, `whatsapp`, `dob`
  - Role-based access to profile
- Endpoints:
  - `POST /auth/login` – Login with username, password, role
  - `GET /me/profile` – View own profile
  - `PUT /me/profile` – Update own profile

### 📋 Staff Assignment
- Assign staff (`employee_id`) to a shelf (`shelf_id`)
- Prevent reassigning if already active
- Record history in `assignment_history`:
  - `employee_id`, `shelf_id`, `action`, `performed_by`, `timestamp`
- Models:
  - `staff_assignments`
  - `assignment_history`

- Endpoints:
  - `POST /staff-assignments/assign?employee_id=E101`
  - `GET /staff-assignments/current` – Current active assignments
  - `POST /staff-assignments/unassign?employee_id=E101` – Unassign staff

### 🧊 Shelf Management
- Shelves are defined using shelf `name` (e.g., A1, A2, etc.)
- Related to `inventory_items` and staff assignments

### 📦 Inventory Management
- Linked to shelves via shelf `name`
- Tracks low stock and item details (future extension for Edge AI)

---

## 🧩 Technologies

- **FastAPI** – Web Framework
- **SQLAlchemy** – ORM
- **PostgreSQL** – Relational Database
- **Uvicorn** – ASGI server
- **JWT Auth** – User-based auth and protected routes

---

## 🛠 Setup Instructions

```bash
git clone https://github.com/your-repo/ShelfCam-Backend.git
cd ShelfCam-Backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

---

## ✅ Tables Overview

### staff_assignments
| Column        | Type    |
|---------------|---------|
| id            | Integer |
| employee_id   | String  |
| shelf_id      | String  |
| assigned_by   | String  |
| is_active     | Boolean |
| assigned_at   | DateTime|

### assignment_history
| Column        | Type    |
|---------------|---------|
| id            | Integer |
| employee_id   | String  |
| shelf_id      | String  |
| action        | String  |
| action_date   | DateTime|
| performed_by  | String  |
| notes         | Text    |

---

## 📬 Contribution

Pull requests and issue reports are welcome! Please ensure proper testing before submitting.

---

## 🧑‍💻 Developed By

**Team ShelfCam - Walmart Sparkathon 2025**