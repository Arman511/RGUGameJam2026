FROM python:3.12-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir uv && uv sync --all-packages --all-groups
EXPOSE 8000
CMD ["uv", "run", "--package", "elemental-api", "uvicorn", "elemental_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
