FROM python:3.11.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --timeout 120 --retries 10 -r requirements.txt
COPY src/ /app/src/
COPY api/ /app/api/
ENV PYTHONPATH=/app/src:/app
EXPOSE 8000
CMD ["uvicorn","api.main:app","--host","0.0.0.0","--port","8000"]

COPY tests/ /app/tests/

