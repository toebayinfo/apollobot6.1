#!/bin/bash
cd /home/site/wwwroot
python -m venv antenv
source antenv/bin/activate
pip install -r requirements.txt
gunicorn --config gunicorn.conf.py app:app
