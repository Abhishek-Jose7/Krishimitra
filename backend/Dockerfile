FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Generate dummy models during build if they don't exist
RUN python models/generate_dummy_models.py

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
