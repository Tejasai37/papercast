
# Gunicorn configuration file
import multiprocessing

# Bind to localhost on port 8000 (standard for our app)
bind = "127.0.0.1:8000"

# Number of worker processes
# Formula: (2 x num_cores) + 1
workers = (multiprocessing.cpu_count() * 2) + 1

# Type of worker
worker_class = "uvicorn.workers.UvicornWorker"

# Logging
accesslog = "-" # Log to stdout
errorlog = "-"  # Log to stderr
loglevel = "info"

# Timeout to allow for AI generation processing
timeout = 120
keepalive = 5
