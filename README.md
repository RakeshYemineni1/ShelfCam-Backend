
# 🛒 ShelfCam Backend

**AI-powered FastAPI backend for real-time retail shelf monitoring**, developed for Walmart Sparkathon 2025. This backend handles detection, inventory tracking, authentication, and role-based access using Edge AI and PostgreSQL.

---

## 🚀 Features

- 🔐 **Authentication System**
  - `POST /auth/signup`: Register user with role (`admin`, `manager`, `staff`)
  - `POST /auth/login`: JWT-based login returns access token
  - Role-based access protection for endpoints
- 🧠 AI Inference Integration (YOLOv5 / ONNX)
- 📦 Real-time Shelf Monitoring API
- 📊 Inventory & Misplacement Detection
- 🔄 Offline-First Support with Sync
- 🗃 PostgreSQL (Production-grade)
- 🌐 RESTful FastAPI Interface
- 🧪 Swagger UI for testing

---

## 🧱 Architecture Overview

```
Mobile Camera / Pi Camera
↓
Edge AI Model (YOLOv5n, ONNX)
↓
FastAPI Backend ───▶ PostgreSQL
↓
React Frontend Dashboard
```

---

## 🧰 Tech Stack

| Layer         | Technology     |
|---------------|----------------|
| Backend       | FastAPI        |
| Database      | PostgreSQL     |
| AI Inference  | YOLOv5n + ONNX |
| Auth          | JWT            |
| Frontend      | React.js       |

---

## 📁 Project Structure

```
shelfcam-backend/
├── app/
│   ├── api/routes/        # All API endpoints
│   ├── core/              # Configs & settings
│   ├── crud/              # Database operations
│   ├── models/            # SQLAlchemy models
│   ├── schemas/           # Pydantic schemas
│   ├── services/          # AI & auth utilities
│   └── main.py            # Entry point
├── database/              # DB config
├── models/                # AI model files (.onnx)
├── scripts/               # Utility scripts
├── .env                   # Env variables
├── requirements.txt       # Python dependencies
└── README.md
```

---

## 🔐 Auth API Usage

### ➕ Signup

`POST /auth/signup`

```json
{
  "username": "admin1",
  "email": "admin@example.com",
  "password": "admin123",
  "role": "admin"
}
```

### 🔑 Login

`POST /auth/login`

```json
{
  "username": "admin1",
  "password": "admin123"
}
```

**Response:**
```json
{
  "access_token": "<JWT_TOKEN>",
  "token_type": "bearer",
  "username": "admin1",
  "role": "admin"
}
```

---

### 👥 Roles & Access

| Role    | Permissions                                 |
|---------|---------------------------------------------|
| Staff   | View alerts, mark shelf tasks done          |
| Manager | Assign tasks, manage inventory              |
| Admin   | Full system control, audit logs             |

---

## 🧪 Setup & Run

### 1. Clone the repo
```bash
git clone https://github.com/<your-username>/shelfcam-backend.git
cd shelfcam-backend
```

### 2. Create virtual environment
```bash
python -m venv venv
.env\Scriptsctivate   # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure `.env`
```
DATABASE_URL=postgresql://postgres:<password>@localhost:5432/shelfcam_db
SECRET_KEY=your_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 5. Run the server
```bash
uvicorn app.main:app --reload
```

### 6. Test via Swagger UI
[http://localhost:8000/docs](http://localhost:8000/docs)

---

## 📌 To-Do / Roadmap

- [ ] Add JWT token refresh
- [ ] Add audit logging
- [ ] Dockerize with PostgreSQL
- [ ] Connect real-time camera stream
- [ ] CI/CD pipeline for deployment

---

## 🔗 Related Repositories

- [Frontend (React)](https://github.com/rakeshyemineni1/shelfcam-frontend)

---

## 📄 License

This project is for educational and hackathon use. For production licensing, contact the maintainers.
