FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN pip install --no-cache-dir grpcio==1.71.0 grpcio-health-checking==1.71.0
COPY scripts/dev_grpc_service.py /app/dev_grpc_service.py
ARG SERVICE_NAME=development-service
ENV SERVICE_NAME=${SERVICE_NAME} PORT=50051
USER nobody
EXPOSE 50051
CMD ["python", "/app/dev_grpc_service.py"]
