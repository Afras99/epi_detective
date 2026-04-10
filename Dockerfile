FROM python:3.11-slim

WORKDIR /app

COPY epi_detective/ /app/

RUN pip install --no-cache-dir \
    fastapi>=0.100.0 \
    uvicorn>=0.23.0 \
    pydantic>=2.0.0 \
    openai>=1.0.0 \
    requests>=2.31.0 \
    openenv-core>=0.2.0

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/health')" || exit 1

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]
