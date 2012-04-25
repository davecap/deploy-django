accesslog = "/srv/myapp/shared/logs/gunicorn_access.log"
errorlog = "/srv/myapp/shared/logs/gunicorn_error.log"

loglevel = "info"

# What ports/sockets to listen on, and what options for them.
bind = "127.0.0.1:8080"

# The maximum number of pending connections
backlog = 2048

# What the timeout for killing busy workers is, in seconds
timeout = 60

# How long to wait for requests on a Keep-Alive connection, in seconds
keepalive = 2

# The maxium number of requests a worker will process before restarting
max_requests = 0

# Whether the app should be pre-loaded
preload_app = False

# How many worker processes
workers = 7

# Type of worker to use
worker_class = "sync"


# What to do before we fork a worker
def def_pre_fork(server, worker):
    import time
    time.sleep(1)
