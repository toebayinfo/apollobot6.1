#!/bin/bash
python -m venv antenv
source antenv/bin/activate
pip install -r requirements.txt
hypercorn app:app -c hypercorn_config.py
