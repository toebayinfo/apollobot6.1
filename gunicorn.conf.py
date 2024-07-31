import multiprocessing

# Gunicorn config variables
workers = multiprocessing.cpu_count() * 2 + 1
threads = 2
timeout = 600
bind = "0.0.0.0:3978"
worker_class = "sync"
# For development:
reload = True

# Server hooks
def on_starting(server):
    pass

def on_reload(server):
    pass

def on_exit(server):
    pass
