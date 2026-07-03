FROM python:3.12-slim

WORKDIR /app

COPY model_service/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "model_service.main:app", "--host", "0.0.0.0", "--port", "8000"]