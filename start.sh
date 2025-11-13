#!/bin/bash
# CSP Brush Converter - Auto-start Script
# This script automatically starts the Python backend and opens the application

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  CSP Brush Converter - Hybrid Edition${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}⚠️  Python 3 not found. Please install Python 3.${NC}"
    exit 1
fi

# Check if requirements are installed
echo -e "${BLUE}📦 Checking dependencies...${NC}"
if ! python3 -c "import flask" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Installing dependencies...${NC}"
    pip3 install -r requirements.txt
fi

echo -e "${GREEN}✅ Dependencies ready${NC}"
echo ""

# Start Python backend in background
echo -e "${BLUE}🐍 Starting Python backend server...${NC}"
python3 simple_server.py &
PYTHON_PID=$!

# Wait for server to start
echo -e "${YELLOW}⏳ Waiting for server to start...${NC}"
sleep 2

# Check if server is running
if ps -p $PYTHON_PID > /dev/null; then
    echo -e "${GREEN}✅ Python backend started (PID: $PYTHON_PID)${NC}"
    echo -e "${GREEN}📍 Server running on http://localhost:5001${NC}"
else
    echo -e "${YELLOW}⚠️  Python backend failed to start${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}🌐 Opening application in browser...${NC}"

# Open in default browser (cross-platform)
if command -v open &> /dev/null; then
    # macOS
    open index.html
elif command -v xdg-open &> /dev/null; then
    # Linux
    xdg-open index.html
elif command -v start &> /dev/null; then
    # Windows
    start index.html
else
    echo -e "${YELLOW}⚠️  Could not open browser automatically${NC}"
    echo -e "${BLUE}📂 Please open index.html manually in your browser${NC}"
fi

echo ""
echo -e "${GREEN}✅ Application ready!${NC}"
echo -e "${BLUE}================================================${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo -e "${BLUE}================================================${NC}"

# Wait for user to stop
trap "echo -e '\n${YELLOW}🛑 Stopping Python backend...${NC}'; kill $PYTHON_PID 2>/dev/null; echo -e '${GREEN}✅ Server stopped${NC}'; exit 0" INT TERM

wait $PYTHON_PID
