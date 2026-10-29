FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/generated:/app/src
WORKDIR /app
COPY services/api-gateway/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY packages/api-contracts/proto /app/proto
RUN mkdir -p /app/generated && python -m grpc_tools.protoc \
    -I /app/proto \
    --python_out=/app/generated \
    --grpc_python_out=/app/generated \
    /app/proto/identity/v1/identity.proto \
    /app/proto/farm/v1/farm.proto
COPY services/api-gateway/src/farmplan_gateway /app/src/farmplan_gateway
USER nobody
EXPOSE 8000
CMD ["uvicorn", "farmplan_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
