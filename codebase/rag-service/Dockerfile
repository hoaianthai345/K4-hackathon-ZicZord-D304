FROM python:3.11-slim

ARG RAG_ANYTHING_COMMIT=65b7ffdeb801309d4c87b6accf81bfe5cd9b175d

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /service
RUN for attempt in 1 2 3; do \
        rm -rf /opt/RAG-Anything; \
        git clone https://github.com/HKUDS/RAG-Anything.git /opt/RAG-Anything \
            && cd /opt/RAG-Anything \
            && git checkout "$RAG_ANYTHING_COMMIT" \
            && break; \
        if [ "$attempt" = "3" ]; then exit 1; fi; \
        sleep 3; \
    done

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir --no-deps /opt/RAG-Anything

COPY app ./app
RUN mkdir -p /data/rag_storage /data/processed

EXPOSE 8010
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010"]
