# DocQuery Phase 2 - Local Testing Without Docker (Windows)

## 🚀 Prerequisites

### 1. Install Python 3.11+
Download from: https://www.python.org/downloads/

**Verify installation:**
```cmd
python --version
# Should show: Python 3.11.x or higher
```

### 2. Install PostgreSQL
Download from: https://www.postgresql.org/download/windows/

**During installation:**
- Username: `postgres`
- Password: Choose a password (remember it!)
- Port: `5432`

**Verify installation:**
```cmd
psql --version
```

### 3. Install Redis for Windows
Download from: https://github.com/microsoftarchive/redis/releases

Or use WSL/Docker just for Redis, or use an alternative like Memurai:
https://www.memurai.com/get-memurai

**Start Redis:**
```cmd
redis-server
```

### 4. Install Tesseract OCR
Download from: https://github.com/UB-Mannheim/tesseract/wiki

**Add to PATH:**
- Default install: `C:\Program Files\Tesseract-OCR`
- Add to System PATH environment variable

**Verify:**
```cmd
tesseract --version
```

---

## 📦 Setup Project

### Step 1: Create Virtual Environment

```cmd
cd e:\Projects\docquery

# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate

# You should see (venv) in your prompt
```

### Step 2: Install Python Dependencies

```cmd
pip install --upgrade pip
pip install -r requirements.txt
```

**This will install:**
- FastAPI, Uvicorn
- SQLAlchemy, psycopg2
- Redis, Celery
- PyMuPDF, pytesseract, Pillow
- OpenAI, tiktoken, nltk
- And more...

**Note:** This may take 5-10 minutes on first install.

### Step 3: Setup Database

**Create database:**
```cmd
# Open psql
psql -U postgres

# In psql prompt:
CREATE DATABASE docquery;
CREATE USER docquery_user WITH PASSWORD 'changeme_postgres_password';
GRANT ALL PRIVILEGES ON DATABASE docquery TO docquery_user;
\q
```

### Step 4: Configure Environment

**Edit `.env` file:**
```env
# Database (local PostgreSQL)
POSTGRES_USER=docquery_user
POSTGRES_PASSWORD=changeme_postgres_password
POSTGRES_DB=docquery
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
DATABASE_URL=postgresql://docquery_user:changeme_postgres_password@localhost:5432/docquery

# Redis (local)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET=your-very-long-random-secret-key-at-least-32-characters-long
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# OpenAI (for audio transcription)
OPENAI_API_KEY=sk-your-openai-api-key-here

# App Settings
APP_NAME=DocQuery
APP_VERSION=0.2.0
ENVIRONMENT=development
DEBUG=true

# File Upload
UPLOAD_DIR=e:\Projects\docquery\uploads
MAX_UPLOAD_SIZE=52428800

# Rate Limiting
LOGIN_RATE_LIMIT=5
```

### Step 5: Initialize Database

```cmd
python scripts\init_db.py
```

**Expected output:**
```
Initializing database...
✓ Database tables created successfully

Created tables:
  - users
  - documents
  - chunks
  - query_logs
```

### Step 6: Create Admin User

```cmd
python scripts\create_admin.py
```

**Enter:**
- Username: `admin`
- Email: `admin@example.com` (optional)
- Password: `Admin123!`

---

## 🚀 Running the System

You'll need **3 terminal windows**:

### Terminal 1: Start FastAPI Server

```cmd
cd e:\Projects\docquery
venv\Scripts\activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Expected output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Keep this running!**

### Terminal 2: Start Redis (if not running as service)

```cmd
redis-server
```

**Or if using Memurai:**
```cmd
memurai
```

**Keep this running!**

### Terminal 3: Start Celery Worker

```cmd
cd e:\Projects\docquery
venv\Scripts\activate
celery -A app.tasks.celery_app worker --loglevel=info --pool=solo
```

**Note:** Windows requires `--pool=solo` option.

**Expected output:**
```
[INFO/MainProcess] Connected to redis://localhost:6379/0
[INFO/MainProcess] Ready to accept tasks
```

**Keep this running!**

---

## 🧪 Test the System

### Test 1: Health Check

Open a **4th terminal** or use your browser:

```cmd
curl http://localhost:8000/health
```

**Or browser:** http://localhost:8000/health

**Expected:**
```json
{
  "status": "healthy",
  "version": "0.2.0",
  "timestamp": "2025-01-17T...",
  "database": "connected",
  "redis": "connected"
}
```

### Test 2: API Documentation

**Browser:** http://localhost:8000/docs

You should see interactive Swagger UI!

### Test 3: Login

```cmd
curl -X POST http://localhost:8000/auth/login ^
  -H "Content-Type: application/json" ^
  -d "{\"username\": \"admin\", \"password\": \"Admin123!\"}"
```

**Copy the `access_token` from response!**

### Test 4: Upload Document

```cmd
set TOKEN=your-access-token-here

curl -X POST http://localhost:8000/upload ^
  -H "Authorization: Bearer %TOKEN%" ^
  -F "file=@README.md"
```

**Watch the Celery worker terminal** - you should see:
```
[INFO] Task app.tasks.document_tasks.process_document received
[INFO] Processing document 1: README.md
[INFO] Successfully processed document 1: 8 chunks created
```

### Test 5: Check Document Status

```cmd
curl -X GET http://localhost:8000/upload/1 ^
  -H "Authorization: Bearer %TOKEN%"
```

**Status should be:** `"completed"`

### Test 6: View Chunks

```cmd
curl -X GET http://localhost:8000/upload/1/chunks ^
  -H "Authorization: Bearer %TOKEN%"
```

You should see extracted text chunks!

### Test 7: Download Original

```cmd
curl -X GET http://localhost:8000/upload/1/download ^
  -H "Authorization: Bearer %TOKEN%" ^
  -o downloaded.md
```

Check the file:
```cmd
type downloaded.md
```

---

## 🔍 File Storage

Check your uploads directory:

```cmd
dir e:\Projects\docquery\uploads\user_1
```

You should see your uploaded file with a UUID name!

---

## 🐛 Troubleshooting

### Issue: "ModuleNotFoundError"

**Solution:**
```cmd
# Make sure virtual environment is activated
venv\Scripts\activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: "psycopg2 installation fails"

**Solution:**
```cmd
# Use binary version
pip install psycopg2-binary
```

### Issue: "Tesseract not found"

**Solution:**
```cmd
# Add to PATH or set in code
# Edit app\services\ocr.py and add:
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

### Issue: "Redis connection failed"

**Solution:**
```cmd
# Check if Redis is running
redis-cli ping
# Should return: PONG

# If not, start Redis:
redis-server
```

### Issue: "Database connection error"

**Solution:**
```cmd
# Check PostgreSQL is running
# Open Services (services.msc) and check "postgresql" service

# Test connection
psql -U docquery_user -d docquery
# Enter password when prompted

# If works, check DATABASE_URL in .env
```

### Issue: "Celery worker fails to start"

**Solution:**
```cmd
# Windows requires solo pool
celery -A app.tasks.celery_app worker --loglevel=info --pool=solo

# If still fails, check Redis connection
```

### Issue: "File upload fails"

**Solution:**
```cmd
# Create uploads directory
mkdir e:\Projects\docquery\uploads

# Check UPLOAD_DIR in .env matches
```

---

## 📊 Development Tips

### Auto-reload on code changes

The FastAPI server (`--reload`) automatically restarts when you edit Python files.

**Celery does NOT auto-reload.** Restart it manually:
```cmd
Ctrl+C
celery -A app.tasks.celery_app worker --loglevel=info --pool=solo
```

### Database GUI Tools

Use **pgAdmin** or **DBeaver** to view database:
- Host: localhost
- Port: 5432
- Database: docquery
- User: docquery_user
- Password: (from .env)

### Redis GUI Tools

Use **RedisInsight** or **Another Redis Desktop Manager**:
- Host: localhost
- Port: 6379

### VS Code Setup

Install extensions:
- Python
- Pylance
- SQLAlchemy

**Set Python interpreter:**
- Ctrl+Shift+P → "Python: Select Interpreter"
- Choose: `.\venv\Scripts\python.exe`

---

## 🧪 Run Tests Locally

```cmd
# Activate venv first!
venv\Scripts\activate

# Run all tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific test
pytest tests\test_auth.py -v
```

**View coverage report:**
- Open: `htmlcov\index.html` in browser

---

## 🔧 Useful Commands

### View Logs

**Python logging** goes to console where uvicorn is running.

**Check Celery tasks:**
```cmd
celery -A app.tasks.celery_app inspect active
celery -A app.tasks.celery_app inspect scheduled
```

### Database Queries

```cmd
psql -U docquery_user -d docquery

-- List documents
SELECT id, original_filename, status, owner_id FROM documents;

-- List chunks
SELECT id, document_id, chunk_index, LEFT(content, 50) as preview FROM chunks;

-- Count chunks per document
SELECT document_id, COUNT(*) as chunk_count FROM chunks GROUP BY document_id;

\q
```

### Clear Data

```cmd
# Delete uploads
rmdir /S /Q e:\Projects\docquery\uploads
mkdir e:\Projects\docquery\uploads

# Reset database
psql -U postgres
DROP DATABASE docquery;
CREATE DATABASE docquery;
GRANT ALL PRIVILEGES ON DATABASE docquery TO docquery_user;
\q

# Reinitialize
python scripts\init_db.py
python scripts\create_admin.py
```

---

## ✅ Verification Checklist

- [ ] Python 3.11+ installed
- [ ] PostgreSQL installed and running
- [ ] Redis installed and running
- [ ] Tesseract OCR installed
- [ ] Virtual environment created and activated
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Database created and initialized
- [ ] Admin user created
- [ ] `.env` file configured correctly
- [ ] FastAPI server starts without errors
- [ ] Celery worker starts without errors
- [ ] Health check returns "healthy"
- [ ] Can login and get JWT token
- [ ] Can upload document
- [ ] Document processing completes
- [ ] Can view chunks
- [ ] Can download original file

---

## 🎯 Quick Test Script

Save as `test_local.bat`:

```bat
@echo off
echo Testing DocQuery locally...

echo.
echo [1/5] Testing health endpoint...
curl http://localhost:8000/health

echo.
echo [2/5] Logging in...
curl -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d "{\"username\": \"admin\", \"password\": \"Admin123!\"}"

echo.
echo [3/5] Upload test (requires TOKEN set)...
curl -X POST http://localhost:8000/upload -H "Authorization: Bearer %TOKEN%" -F "file=@README.md"

echo.
echo [4/5] Check document...
curl -X GET http://localhost:8000/upload/1 -H "Authorization: Bearer %TOKEN%"

echo.
echo [5/5] View chunks...
curl -X GET http://localhost:8000/upload/1/chunks -H "Authorization: Bearer %TOKEN%"

echo.
echo Testing complete!
pause
```

---

## 🛑 Stopping the System

### Stop Servers

In each terminal:
- Press `Ctrl+C`

### Deactivate Virtual Environment

```cmd
deactivate
```

---

## 🎉 Success!

If all checks pass, you have DocQuery Phase 2 running locally on Windows without Docker!

**Next steps:**
- Upload different file types (PDF, images, audio)
- Test multi-user scenarios
- Explore the API documentation
- Review the code in VS Code

**Need help?** Check the troubleshooting section or review error messages in the terminal where services are running.

---

**Happy Testing! 🚀**
