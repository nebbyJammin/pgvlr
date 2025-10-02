# Use python image
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Prevent Python from writing pyc files and enable stoud/stderr buffering
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Expose the 8111 port
EXPOSE 8111

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8111"]
