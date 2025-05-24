#!/bin/bash

# Start Gunicorn in the background
gunicorn -b 0.0.0.0:5000 app:app &
GUNICORN_PID=$!

# Start the backend Python script
(cd backend && python3 main.py) &
BACKEND_PID=$!

# Wait for the backend process to finish
wait $BACKEND_PID
BACKEND_EXIT_CODE=$?

# Clean up the Gunicorn process
kill $GUNICORN_PID

exit $BACKEND_EXIT_CODE
