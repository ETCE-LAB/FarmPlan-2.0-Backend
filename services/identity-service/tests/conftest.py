import os
import sys
from pathlib import Path

from grpc_tools import protoc


BACKEND_ROOT = Path(__file__).resolve().parents[3]
GENERATED_ROOT = BACKEND_ROOT / ".generated"
PROTO_ROOT = BACKEND_ROOT / "packages" / "api-contracts" / "proto"
PROTO_FILE = PROTO_ROOT / "identity" / "v1" / "identity.proto"

if not (GENERATED_ROOT / "identity" / "v1" / "identity_pb2.py").exists():
    GENERATED_ROOT.mkdir(parents=True, exist_ok=True)
    result = protoc.main(
        [
            "grpc_tools.protoc",
            f"-I{PROTO_ROOT}",
            f"--python_out={GENERATED_ROOT}",
            f"--grpc_python_out={GENERATED_ROOT}",
            str(PROTO_FILE),
        ]
    )
    if result != 0:
        raise RuntimeError("Could not generate Python gRPC contracts for tests.")

os.environ.setdefault("DATABASE_URL", "postgresql://farmplan:test@localhost:5432/farmplan")
os.environ.setdefault("JWT_SECRET", "test-only-secret-that-is-at-least-32-bytes-long")
sys.path.insert(0, str(GENERATED_ROOT))
sys.path.insert(0, str(BACKEND_ROOT / "services" / "identity-service" / "src"))
