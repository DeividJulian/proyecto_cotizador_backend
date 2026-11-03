"""The gRPC contract (proto/) and the Python code generated from it (proto_gen/) stay in sync."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_generated_code_is_up_to_date():
    r = subprocess.run([sys.executable, "scripts/gen_proto.py", "--check"], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
