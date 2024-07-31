#!/bin/bash

# Start Gunicorn
exec gunicorn --bind 0.0.0.0:3978 --config gunicorn.conf.py app:app