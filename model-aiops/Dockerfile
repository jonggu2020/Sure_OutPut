FROM python:3.12-slim

WORKDIR /app

# ChromaDB 빌드에 필요한 C++ 컴파일러
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential g++ && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003", "--reload"]
