#!/bin/bash

# Install dependencies without cache
pip install -r requirements.txt --no-cache-dir

pip install --upgrade pip

# Start the application
hypercorn app:app --bind 0.0.0.0:8000

echo "Deployment completed."
