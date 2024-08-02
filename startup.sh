#!/bin/bash

# Start the Gunicorn server
gunicorn --bind 0.0.0.0:8000 app:init_func
