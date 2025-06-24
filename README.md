
# 🛒 ShelfCam Backend

**AI-powered FastAPI backend for real-time retail shelf monitoring**, developed for Walmart Sparkathon 2025. This backend handles detection, inventory tracking, user roles, and integration with Edge AI and PostgreSQL.

---

## 🚀 Features

- 🧠 AI Inference Integration (YOLOv5 / ONNX)
- 📦 Real-time Shelf Monitoring API
- 📊 Inventory & Misplacement Detection
- 🔐 JWT-Based Role Authentication (Staff, Manager, Admin)
- 🔄 Offline-First Support with Sync
- 🗃 PostgreSQL Support (production-grade database)
- 🔌 RESTful API with FastAPI
- 📁 Modular Project Structure

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

| Layer         | Technology                                  |
|---------------|---------------------------------------------|
| Backend       | FastAPI                                     |
| Database      | PostgreSQL                                  |
| AI Inference  | YOLOv5n + ONNX                              |
| Auth          | JWT                                         |
| Data Sync     | JSON/SQLite (offline-capable edge devices)  |
| Frontend      | [shelfcam-frontend](https://github.com/<your-username>/shelfcam-frontend) |

---

## 📦 Project Structure

```
shelfcam-backend/
├── app/
│   ├── api/routes/        # API Endpoints
│   ├── core/              # Configs, DB Setup
│   ├── crud/              # DB Operations
│   ├── models/            # SQLAlchemy Models
│   ├── schemas/           # Pydantic Schemas
│   ├── services/          # AI Integration Logic
│   └── main.py            # Entry Point
├── models/                # AI Model Files (.onnx)
├── database/              # SQL Scripts, offline DBs
├── scripts/               # Sync / Utility Scripts
├── .env                   # Environment Variables
├── requirements.txt       # Python Dependencies
└── init_db.py             # DB Table Creator Script
```

---

## 🧪 Setup Instructions

### 1. Create Virtual Environment

```bash
python -m venv venv
.env\Scriptsctivate   # Windows
# OR
source venv/bin/activate  # macOS/Linux
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure `.env` File

Create a `.env` file in the project root and add the following:

```ini
DATABASE_URL=postgresql://<username>:<password>@localhost:5432/shelfcam_db
```

Replace `<username>` and `<password>` with your actual PostgreSQL credentials.

### 🏗 4. Initialize Database

```bash
python init_db.py
```

### 🚀 5. Run the Server

```bash
uvicorn app.main:app --reload
```

---

## Visit:

- **API root:** [http://127.0.0.1:8000](http://127.0.0.1:8000)  
- **Swagger Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

### 📡 API Endpoints (Sample)

| Method | Endpoint       | Description                        |
|--------|----------------|------------------------------------|
| GET    | `/`            | Welcome message                    |
| POST   | `/detect`      | Run AI inference on shelf image    |
| GET    | `/inventory`   | List all products                  |
| POST   | `/login`       | JWT-based login                    |

---

### 👥 Roles

| Role    | Permissions                                 |
|---------|---------------------------------------------|
| Staff   | View alerts, mark shelf tasks done          |
| Manager | Assign tasks, manage categories             |
| Admin   | Full system control, audit logs             |

---

### 📌 To-Do / Roadmap

- [ ] Add real-time image sync from Pi camera  
- [ ] Deploy using Docker & CI/CD  
- [ ] Add audit logging  
- [ ] Connect to live inventory from Walmart APIs (mock)  

---

### 🛡 License

This project is licensed for educational and hackathon use.  
For production licensing, contact the maintainers.

---

### 🔗 Related Repos

- **Frontend:** `shelfcam-frontend`  
- **Demo Video & Pitch Deck:** *(link once uploaded)*
