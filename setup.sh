#!/bin/bash
set -e

echo "=========================================="
echo "  WarmGrid Setup"
echo "=========================================="

# Check Python 3.11+
if ! command -v python3 &>/dev/null; then
    echo "ERROR: Python 3 is not installed. Please install Python 3.11+"
    exit 1
fi
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
    echo "ERROR: Python 3.11+ required. Found: $PYTHON_VERSION"
    exit 1
fi
echo "[OK] Python $PYTHON_VERSION found"

# Create virtual environment
cd backend
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi
echo "[OK] Virtual environment ready"

# Install dependencies
echo "Installing Python dependencies..."
source venv/bin/activate
pip install --quiet -r requirements.txt
echo "[OK] Python dependencies installed"

# Generate keys and create .env
if [ ! -f ".env" ]; then
    echo "Generating encryption keys..."
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    cat > .env <<EOF
SECRET_KEY=$SECRET_KEY
ENCRYPTION_KEY=$ENCRYPTION_KEY
DATABASE_URL=sqlite+aiosqlite:///./warmgrid.db
DEFAULT_SEND_HOUR_START=7
DEFAULT_SEND_HOUR_END=11
WEEKLY_VOLUME_INCREASE=5
MAX_DAILY_VOLUME=50
IMAP_POLL_INTERVAL_MINUTES=120
HEALTH_CHECK_INTERVAL_HOURS=24
EOF
    echo "[OK] .env file created with generated keys"
else
    echo "[SKIP] .env already exists"
fi

# Run database setup (create tables + seed settings)
echo "Setting up database..."
python3 -c "
import asyncio
import sys
sys.path.insert(0, '.')
async def setup():
    from database import create_all_tables
    await create_all_tables()
    print('Tables created')
asyncio.run(setup())
"
echo "[OK] Database ready"

deactivate
cd ..

# Check Node.js
if ! command -v node &>/dev/null; then
    echo "ERROR: Node.js is not installed. Please install Node.js 18+"
    exit 1
fi
NODE_VERSION=$(node --version | sed 's/v//' | cut -d. -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "ERROR: Node.js 18+ required"
    exit 1
fi
echo "[OK] Node.js $(node --version) found"

# Install frontend dependencies
echo "Installing frontend dependencies..."
cd frontend
npm install --silent
echo "[OK] Frontend dependencies installed"
cd ..

echo ""
echo "=========================================="
echo "  WarmGrid Setup Complete!"
echo "=========================================="
echo ""
echo "To start the backend:"
echo "  cd backend && source venv/bin/activate && uvicorn main:app --reload"
echo ""
echo "To start the frontend (in a new terminal):"
echo "  cd frontend && npm run dev"
echo ""
echo "Dashboard URL: http://localhost:5173"
echo ""
echo "First step: Visit the dashboard and create your admin account."
echo ""
echo "REMINDER: To use DeepSeek AI content generation,"
echo "add your API key in Settings -> Content Engine."
echo "Get your key at: https://platform.deepseek.com"
echo "=========================================="
