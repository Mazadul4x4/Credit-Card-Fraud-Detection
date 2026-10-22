FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY webapp/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY webapp /app

EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
