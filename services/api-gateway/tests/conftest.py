import sys
from pathlib import Path

from grpc_tools import protoc


BACKEND_ROOT = Path(__file__).resolve().parents[3]
GENERATED_ROOT = BACKEND_ROOT / ".generated"
PROTO_ROOT = BACKEND_ROOT / "packages" / "api-contracts" / "proto"
PROTO_FILES = [
    PROTO_ROOT / "identity" / "v1" / "identity.proto",
    PROTO_ROOT / "farm" / "v1" / "farm.proto",
]

if any(
    not (generated := GENERATED_ROOT / proto.parent.relative_to(PROTO_ROOT) / f"{proto.stem}_pb2.py").exists()
    or generated.stat().st_mtime < proto.stat().st_mtime
    for proto in PROTO_FILES
):
    GENERATED_ROOT.mkdir(parents=True, exist_ok=True)
    result = protoc.main(
        [
            "grpc_tools.protoc",
            f"-I{PROTO_ROOT}",
            f"--python_out={GENERATED_ROOT}",
            f"--grpc_python_out={GENERATED_ROOT}",
            *(str(proto) for proto in PROTO_FILES),
        ]
    )
    if result != 0:
        raise RuntimeError("Could not generate Python gRPC contracts for tests.")

sys.path.insert(0, str(GENERATED_ROOT))
sys.path.insert(0, str(BACKEND_ROOT / "services" / "api-gateway" / "src"))
