#!/bin/bash

echo "==============================================" 
echo "Document Query App Startup with Diagnostics"
echo "==============================================" 

# Function to check if a command succeeds
check_success() {
  if [ $? -ne 0 ]; then
    echo -e "\n\033[31mError: $1 failed!\033[0m"
    echo -e "Please check the logs above for more details.\n"
    exit 1
  fi
}

# Absolute path to the project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

# Check if Python is installed
echo -e "\n\033[36mChecking environment...\033[0m"
if ! command -v python3 &> /dev/null; then
    echo -e "\033[31mError: Python 3 is not installed or not in PATH\033[0m"
    exit 1
fi
echo "✓ Python 3 is installed"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo -e "\033[31mError: Node.js is not installed or not in PATH\033[0m"
    exit 1
fi
echo "✓ Node.js is installed"

# Check if the .env file exists
if [ ! -f "$PROJECT_DIR/../.env" ]; then
    echo -e "\033[31mError: .env file not found at $PROJECT_DIR/../.env\033[0m"
    echo "Please create an .env file with your Supabase credentials."
    exit 1
fi
echo "✓ .env file found"

# Install backend dependencies if needed
echo -e "\n\033[36mChecking backend dependencies...\033[0m"
cd "$BACKEND_DIR" || { echo "Error: Could not change to backend directory"; exit 1; }

# Check if a Python virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
    check_success "Virtual environment creation"
fi

# Activate the virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
check_success "Virtual environment activation"

# Install or update packages
echo "Installing/updating dependencies..."
pip install -r requirements.txt
check_success "Backend dependencies installation"

# Run diagnostics
echo -e "\n\033[36mRunning Supabase diagnostic tests...\033[0m"
python supabase_diagnostics.py
diagnostics_exit_code=$?

if [ $diagnostics_exit_code -ne 0 ]; then
    echo -e "\n\033[31mDiagnostic tests failed.\033[0m"
    echo "Please fix the Supabase integration issues before starting the application."
    echo "You can manually run diagnostics with: cd backend && python supabase_diagnostics.py"
    exit 1
else
    echo -e "\n\033[32mDiagnostic tests completed.\033[0m"
fi

# Ask if user wants to continue
read -p "Continue with application startup? (y/n): " continue_startup
if [[ ! $continue_startup =~ ^[Yy]$ ]]; then
    echo "Startup aborted by user."
    exit 0
fi

# Start backend server in background
echo -e "\n\033[36mStarting backend server...\033[0m"
echo "Backend logs will be saved to backend_server.log"
python main.py > backend_server.log 2>&1 &
backend_pid=$!
echo "Backend server started with PID: $backend_pid"

# Check if backend server started successfully
sleep 2
if ! ps -p $backend_pid > /dev/null; then
    echo -e "\033[31mError: Backend server failed to start!\033[0m"
    echo "Check backend_server.log for details."
    exit 1
fi

# Setup and start frontend
echo -e "\n\033[36mSetting up frontend...\033[0m"
cd "$FRONTEND_DIR" || { echo "Error: Could not change to frontend directory"; exit 1; }

# Install frontend dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
    check_success "Frontend dependencies installation"
else
    echo "✓ Frontend dependencies already installed"
fi

# Start frontend in development mode
echo -e "\n\033[36mStarting frontend development server...\033[0m"
echo "Frontend logs will be displayed in this terminal."
echo -e "To stop both servers, press Ctrl+C and then run: \033[33mkill $backend_pid\033[0m"
echo -e "\n\033[32mApplication is starting! The frontend will be available at http://localhost:3000\033[0m"
echo -e "API diagnostics endpoint: \033[34mhttp://localhost:8081/diagnostics/database\033[0m"
echo -e "==============================================\n"

# Start frontend server
npm start

# When npm start is interrupted, kill the backend server as well
kill $backend_pid
echo -e "\n\033[36mShutdown complete.\033[0m" 