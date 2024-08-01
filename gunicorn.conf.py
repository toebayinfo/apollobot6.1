# Gunicorn configuration file
bind = "0.0.0.0:8000"
workers = 4
# If you're using Flask, remove this line or replace it with a standard worker class if needed
# worker_class = "uvicorn.workers.UvicornWorker"  # This is typically for ASGI frameworks like Quart or FastAPI
