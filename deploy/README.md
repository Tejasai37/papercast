# Production Deployment Configurations

This directory contains the optimized configuration files required for deploying PaperCast to a production Amazon EC2 instance. These files act in tandem to wrap the FastAPI backend in a high-performance web server array.

These configurations replace the need for manually writing basic `nano` configuration blocks during the server setup process outlined in `infrastructure/manual_setup.md`.

## Files

### `gunicorn_conf.py`
The configuration for the **Gunicorn Application Server**.
*   **Purpose**: Gunicorn is a process manager that runs the Python FastAPI application (`main.py`). It binds to the internal `localhost:8000` port.
*   **Dynamic Scaling**: It uses Python's `multiprocessing` library to automatically calculate the optimal number of Uvicorn worker processes based on your EC2 instance size (`(2 x CPU Cores) + 1`). This ensures maximum parallel processing for concurrent users.
*   **Timeout Handling**: Crucially, it sets the process `timeout` to 120 seconds. Because AWS Bedrock and Polly can take significant time to synthesize massive audio news files, this prevents the Gunicorn workers from hastily severing the connection before the AI finishes processing.

### `nginx.conf`
The configuration for the **Nginx Reverse Proxy**.
*   **Purpose**: Nginx acts as the "front door" to your EC2 instance. It binds to the public port `80` (HTTP) and securely proxies permitted traffic internally to the Gunicorn server.
*   **Static Asset Offloading**: It bypasses Python entirely to serve your frontend CSS (`style.css`), JavaScript (`main.js`), and images directly to the client with `Cache-Control` headers, drastically improving page load speeds.
*   **Buffering Optimization**: It turns off `proxy_buffering` and sets identical 120-second read timeouts. This ensures that massive AI-generated audio streams (MP3s) are delivered smoothly to the browser without overwhelming the EC2 instance's memory.
