#!/bin/bash

cd /home/site/wwwroot
# Activate the virtual environment
source antenv/bin/activate

# Upgrade pip and install the requirements
pip install --upgrade pip
pip install -r requirements.txt

# Start Gunicorn with the specified configuration
exec gunicorn --config gunicorn.conf.py app:init_func
