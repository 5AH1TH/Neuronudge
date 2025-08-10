#!/bin/bash
# Activate the virtual environment (created by Azure or manually)
if [ -d "antenv" ]; then
    source antenv/bin/activate
elif [ -d "env" ]; then
    source env/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

# Start Gunicorn with binding to all interfaces and increased timeout
exec gunicorn --bind=0.0.0.0 --timeout 600 run:app
