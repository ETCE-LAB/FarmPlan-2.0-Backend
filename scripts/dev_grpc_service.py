"""gRPC health-only process for modules not implemented yet."""

import json
import os
from concurrent import futures

import grpc
from grpc_health.v1 import health, health_pb2, health_pb2_grpc

service_name = os.environ.get("SERVICE_NAME", "development-service")
port = int(os.environ.get("PORT", "50051"))

server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
health_servicer = health.HealthServicer()
health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
health_servicer.set("", health_pb2.HealthCheckResponse.SERVING)
health_servicer.set(service_name, health_pb2.HealthCheckResponse.SERVING)
server.add_insecure_port(f"[::]:{port}")
server.start()
print(json.dumps({"service": service_name, "event": "started", "port": port}), flush=True)
try:
    server.wait_for_termination()
except KeyboardInterrupt:
    server.stop(grace=5).wait()
