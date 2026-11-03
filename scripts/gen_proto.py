"""Generates the Python code of the gRPC (Connect) services from proto/ into proto_gen/.

    python scripts/gen_proto.py          regenerates proto_gen/
    python scripts/gen_proto.py --check  fails if proto_gen/ is not up to date

Needs requirements-dev.txt (grpcio-tools brings protoc; protoc-gen-connectrpc writes the Connect stubs).
The front generates its own client from the same .proto (npm run gen:proto).
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROTO = ROOT / "proto"
OUT = ROOT / "proto_gen"


def plugin() -> str:
    folder = Path(sys.executable).parent
    for name in ("protoc-gen-connectrpc.exe", "protoc-gen-connectrpc"):
        if (folder / name).exists():
            return str(folder / name)
    found = shutil.which("protoc-gen-connectrpc")
    if not found:
        sys.exit("Falta protoc-gen-connectrpc: pip install -r requirements-dev.txt")
    return found


def generate(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    files = sorted(f.relative_to(PROTO).as_posix() for f in PROTO.rglob("*.proto"))
    subprocess.run(
        [
            sys.executable, "-m", "grpc_tools.protoc", "-I.",
            f"--python_out={out}", f"--pyi_out={out}",
            f"--plugin=protoc-gen-connectrpc={plugin()}", f"--connectrpc_out=protobuf=google:{out}",
            *files,
        ],
        check=True,
        cwd=PROTO,
    )
    # Packages, so the generated modules import each other (proto_gen.cotizador.v1)
    for folder in [out, *(p for p in out.rglob("*") if p.is_dir())]:
        (folder / "__init__.py").touch()


def same_tree(a: Path, b: Path) -> bool:
    files_a = sorted(p.relative_to(a) for p in a.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    files_b = sorted(p.relative_to(b) for p in b.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    if files_a != files_b:
        return False
    read = lambda p: p.read_text(encoding="utf-8").replace("\r\n", "\n")  # noqa: E731
    return all(read(a / f) == read(b / f) for f in files_a)


def main() -> int:
    if "--check" in sys.argv:
        with tempfile.TemporaryDirectory() as temp:
            generate(Path(temp))
            if not OUT.exists() or not same_tree(Path(temp), OUT):
                print("proto_gen/ está desactualizado: corre python scripts/gen_proto.py")
                return 1
        print("proto_gen/ está al día")
        return 0
    shutil.rmtree(OUT, ignore_errors=True)
    generate(OUT)
    print(f"Código generado en {OUT.name}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
