FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/generated:/app/src
WORKDIR /app
COPY services/farm-service/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY packages/api-contracts/proto /app/proto
RUN mkdir -p /app/generated && python -m grpc_tools.protoc \
    -I /app/proto \
    --python_out=/app/generated \
    --grpc_python_out=/app/generated \
    /app/proto/farm/v1/farm.proto
COPY services/farm-service/src/farmplan_farm /app/src/farmplan_farm
USER nobody
EXPOSE 50051
CMD ["python", "-m", "farmplan_farm.main"]
