FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY model_service/requirements.txt /app/model_service/requirements.txt
RUN pip install --no-cache-dir -r /app/model_service/requirements.txt

COPY model_service /app/model_service

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --retries=12 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "model_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
