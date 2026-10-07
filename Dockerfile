FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt . 
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

RUN groupadd -g 1001 appgroup \
    && useradd -r -u 1001 -g appgroup appuser \
    && chown -R appuser:appgroup /app
    
USER appuser

EXPOSE 9090

CMD uvicorn main:app --host 0.0.0.0 --port 9090