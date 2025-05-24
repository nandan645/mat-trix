#!/bin/bash

# Start Gunicorn in the background
gunicorn -b 0.0.0.0:5000 app:app --log-level error &
GUNICORN_PID=$!

# Start SSH tunnel to expose port 8080 via localhost.run
ssh -q -R 80:localhost:5000 nokey@localhost.run &
SSH_TUNNEL_PID=$!

# Start the backend Python script
(cd backend && python3 main.py) &
BACKEND_PID=$!

# Wait for the backend process to finish
wait $BACKEND_PID
BACKEND_EXIT_CODE=$?

# Clean up other background processes
kill $GUNICORN_PID $SSH_TUNNEL_PID

exit $BACKEND_EXIT_CODE
