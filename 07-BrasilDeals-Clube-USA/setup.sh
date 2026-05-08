#!/bin/bash
# setup.sh for Clube USA project

echo "--- Setting up Clube USA project environment ---"

# 1. Create a Python virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment 'venv'..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create virtual environment."
        exit 1
    fi
else
    echo "Virtual environment 'venv' already exists."
fi

# 2. Activate the virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "Error: Failed to activate virtual environment."
    exit 1
fi

# 3. Install dependencies from requirements.txt
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Error: Failed to install dependencies."
    exit 1
fi

# 4. Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from .env.example. Please fill in your credentials."
    cp .env.example .env
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create .env file."
        exit 1
    fi
    echo "Edit .env file with your API keys and database URL: nano .env"
else
    echo ".env file already exists."
fi

# 5. Initialize the database
echo "Initializing database (creating tables)..."
python -c "from database import init_db; init_db()"
if [ $? -ne 0 ]; then
    echo "Error: Failed to initialize database. Check DATABASE_URL in .env."
    exit 1
fi

# 6. Run integration tests
echo "Running integration tests..."
# Ensure .env is loaded for tests
export $(grep -v '^#' .env | xargs)
pytest tests/test_integration.py -v
if [ $? -ne 0 ]; then
    echo "Warning: Integration tests failed. Review your .env configuration and logs."
fi

echo "--- Setup complete! ---"
echo "You can now run the scheduler: python scheduler.py"
echo "Or run a single cycle: python main.py"
echo "To deactivate the virtual environment, simply type 'deactivate'."