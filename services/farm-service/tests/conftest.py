"""Generate Farm contracts with protoc for standalone service test execution."""
from pathlib import Path
import sys
from grpc_tools import protoc

ROOT = Path(__file__).resolve().parents[3]
PROTO = ROOT / "packages/api-contracts/proto"
GENERATED = ROOT / ".generated"
GENERATED.mkdir(exist_ok=True)
if protoc.main(["grpc_tools.protoc", f"-I{PROTO}", f"--python_out={GENERATED}", f"--grpc_python_out={GENERATED}", str(PROTO / "farm/v1/farm.proto")]):
    raise RuntimeError("Farm contract generation failed")
sys.path.insert(0, str(GENERATED))
sys.path.insert(0, str(ROOT / "services/farm-service/src"))
