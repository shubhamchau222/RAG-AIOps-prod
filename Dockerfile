FROM python:3.13-rc-slim

# Set working directory inside the container
WORKDIR /app

# COPY only dependancies 
COPY requirements.txt . 

# Install Python deps
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (excluding .env and ignored files) 
# Check the ignored file in .dockerignore
COPY . .

#Expose the port same as your application
EXPOSE 8000 

# Start FastAPI using uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]