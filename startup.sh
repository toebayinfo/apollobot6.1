#!/bin/bash
cd /home/site/wwwroot
exec gunicorn -c gunicorn.conf.py app:app