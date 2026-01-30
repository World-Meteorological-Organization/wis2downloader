# Use the official NiceGUI image as the base image
FROM zauberzeug/nicegui:latest

# Set working directory
WORKDIR /app

# Copy the application code to the container
COPY ./modules/ui /app

# Copy local module to the container
COPY ./modules/shared /app/shared

# Install any additional dependencies if needed
RUN uv pip install /app/shared

# Expose the port your NiceGUI app runs on (default is 8080)
EXPOSE 8080

# Set the default command to run the NiceGUI app
CMD ["/opt/venv/bin/python", "main.py"]
