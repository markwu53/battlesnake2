# 1. Use an official Python runtime as a parent image
FROM python:3.11-slim

# 2. Set environment variables to ensure output is logged correctly
ENV PYTHONUNBUFFERED=1

# 3. Set the working directory in the container
WORKDIR /app

# 4. Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of your application code
COPY . .

# 6. Command to run your app
# Replace 'main:app' with 'your_filename:your_app_variable' 
# (e.g., if your file is server.py and you use Flask, it might be 'server:app')
CMD ["python", "main.py"]