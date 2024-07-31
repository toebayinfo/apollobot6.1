#!/bin/bash

# Start Gunicorn
exec gunicorn --bind 0.0.0.0:8000 --config gunicorn.conf.py app:app