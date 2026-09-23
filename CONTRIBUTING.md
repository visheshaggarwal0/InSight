# Contributing to InSight

Thank you for your interest in contributing to **InSight**! This document provides guidelines for local development, testing, and submitting pull requests.

---

## 🛠️ Local Development Setup

### Prerequisites
- **Python**: 3.10+
- **Node.js**: v18+ and `npm`

### 1. Clone & Install
```bash
git clone https://github.com/your-username/InSight.git
cd InSight

# Install Python backend dependencies
cd backend
pip install -r requirements.txt
cd ..

# Install Frontend dependencies
cd frontend
npm install
cd ..
```

### 2. Launching Locally
From the root directory, simply run:
```bash
npm run dev
# or on Windows:
.\start.bat
```
- **Backend API**: `http://127.0.0.1:8000` (Swagger docs: `/docs`)
- **Frontend Dashboard**: `http://localhost:5173`

---

## 🧪 Testing Guidelines

Before opening a pull request, ensure all validations pass:

### Frontend
```bash
cd frontend
npm run build
```

### Backend
```bash
cd backend
python -c "from app.api.routes import initialize_domain, state; print('Pipeline OK')"
```
