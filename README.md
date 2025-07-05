
# 🔐 ShelfCam Authentication Backend

FastAPI-based login system for ShelfCam — a retail shelf monitoring project. This module handles secure authentication for multiple user roles without password hashing (for internal/test use only).

---

## 📦 Features

- ✅ FastAPI backend
- ✅ PostgreSQL integration
- ✅ Role-based login system:
  - Staff
  - Store Manager
  - Area Manager
- ✅ JWT Token generation
- ✅ `.env` configuration support

---

## 🛠️ Tech Stack

- FastAPI
- PostgreSQL
- SQLAlchemy
- Pydantic v2
- Uvicorn
- Python 3.11+
- JWT (`python-jose`)
- dotenv (`pydantic-settings`)

---

## 🔧 Project Structure

```
ShelfCam-Backend/
├── app/
│   ├── api/routes/auth.py       # Login route
│   ├── core/
│   │   ├── config.py            # Settings using pydantic-settings
│   │   └── jwt_token.py         # Token generator
│   ├── database/db.py           # SQLAlchemy DB setup
│   ├── models/employee.py       # Employee ORM model
│   └── schemas/user.py          # Pydantic models
├── .env                         # Environment variables
└── main.py                      # FastAPI app entry point
```

---

## 📄 .env Configuration

Create a `.env` file at the project root:

```
DATABASE_URL=postgresql://postgres:yourpassword@localhost/shelfCam_auth
SECRET_KEY=your_super_secret_key
```

---

## 🚀 Run the App

```bash
# 1. Activate virtual environment
cd ShelfCam-Backend
venv\Scripts\activate  # (Windows)

# 2. Install requirements
pip install -r requirements.txt

# 3. Start the server
uvicorn app.main:app --reload
```

---

## ✅ API Endpoint

### 🔐 POST `/auth/login`

Login with employee credentials.

#### Request Body
```json
{
  "employee_id": "E101",
  "username": "staff1",
  "password": "staffpass",
  "role": "staff"
}
```

#### Response
```json
{
  "access_token": "your.jwt.token",
  "token_type": "bearer"
}
```

---

## ⚠️ Notes

- Passwords are stored in plain text — intended for internal use or testing only.
- Do not use this in production without password hashing and security enhancements.
