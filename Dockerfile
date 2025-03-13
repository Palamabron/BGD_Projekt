FROM python:3.10

# Set environment variable to prevent bytecode compilation
# This avoids the "bad marshal data" error
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Default command
CMD ["python", "import_csv_to_postgres.py", "--folder", "csv_files"]