#!/bin/bash

# Install dependencies without cache
pip install -r requirements.txt --no-cache-dir

# Any other deployment steps can go here, for example:
# python manage.py migrate
# python manage.py collectstatic --noinput

echo "Deployment completed."
