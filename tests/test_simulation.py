"""Monte Carlo simulation: the REST fallback and the gRPC (Connect) service, called with the generated client."""
import socket
import threading
import time

import pytest
import uvicorn
from connectrpc.code import Code
from connectrpc.errors import ConnectError

from main import app
from proto_gen.cotizador.v1 import simulation_pb2 as pb
from proto_gen.cotizador.v1.simulation_connect import SimulationServiceClientSync


@pytest.fixture(scope="module")
def server():
    """The real app on a free local port: the Connect client needs an HTTP server."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    instance = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=instance.run, daemon=True)
    thread.start()
    while not instance.started:
        time.sleep(0.02)
    yield f"http://127.0.0.1:{port}"
    instance.should_exit = True
    thread.join(timeout=5)


@pytest.fixture
def grpc(server):
    with SimulationServiceClientSync(server) as client:
        yield client


def token(session) -> str:
    return session.headers["Authorization"].removeprefix("Bearer ")


def stream(grpc, quote_id: int, auth: str | None, runs: int = 5_000, samples: int = 0) -> list[pb.SimulateEvent]:
    headers = {"authorization": f"Bearer {auth}"} if auth else None
    return list(grpc.simulate(pb.SimulateRequest(quote_id=quote_id, runs=runs, samples=samples), headers=headers))


# ---------- REST fallback ----------

def test_rest_simulation(client, analyzed_quote):
    r = client.post(f"/quotes/{analyzed_quote['id']}/simulation", json={"runs": 5_000, "samples": 100})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["runs"] == 5_000 and len(body["samples"]) == 100 and len(body["histogram"]) == 30
    assert body["p50"] <= body["p80"] <= body["p90"]
    assert body["price_p50"] <= body["price_p80"] <= body["price_p90"]
    assert 0 <= body["prob_over_plan"] <= 1
    assert sum(b["count"] for b in body["histogram"]) == 5_000
    # The PERT average and the simulated mean agree
    assert body["mean"] == pytest.approx(body["planned_hours"], rel=0.03)


def test_rest_needs_an_analyzed_quote(client, quote):
    r = client.post(f"/quotes/{quote['id']}/simulation", json={"runs": 5_000})
    assert r.status_code == 409 and "Analiza" in r.json()["detail"]


def test_rest_rejects_out_of_range(client, analyzed_quote):
    assert client.post(f"/quotes/{analyzed_quote['id']}/simulation", json={"runs": 10}).status_code == 422
    assert client.post(f"/quotes/{analyzed_quote['id']}/simulation", json={"runs": 5_000, "samples": 6_000}).status_code == 422


def test_rest_requires_login_and_ownership(anonymous, other, analyzed_quote):
    assert anonymous.post(f"/quotes/{analyzed_quote['id']}/simulation", json={}).status_code == 401
    assert other.post(f"/quotes/{analyzed_quote['id']}/simulation", json={}).status_code == 404


# ---------- gRPC ----------

def test_grpc_streams_progress_then_the_result(grpc, client, analyzed_quote):
    events = stream(grpc, analyzed_quote["id"], token(client), runs=5_000, samples=100)
    kinds = [e.WhichOneof("event") for e in events]
    assert kinds == ["progress"] * 10 + ["result"]
    assert [e.progress.done for e in events[:-1]] == list(range(500, 5_001, 500))
    result = events[-1].result
    assert result.runs == 5_000 and len(result.samples) == 100 and len(result.histogram) == 30


def test_grpc_and_rest_give_the_same_result(grpc, client, analyzed_quote):
    """Same business logic behind both protocols (and a fixed seed)."""
    rest = client.post(f"/quotes/{analyzed_quote['id']}/simulation", json={"runs": 5_000, "samples": 50}).json()
    result = stream(grpc, analyzed_quote["id"], token(client), samples=50)[-1].result
    for field in ("p10", "p50", "p80", "p90", "mean", "prob_over_plan", "price_p80", "planned_hours"):
        assert getattr(result, field) == pytest.approx(rest[field]), field
    assert list(result.samples) == pytest.approx(rest["samples"])
    assert [b.count for b in result.histogram] == [b["count"] for b in rest["histogram"]]


def test_grpc_without_token(grpc, analyzed_quote):
    with pytest.raises(ConnectError) as error:
        stream(grpc, analyzed_quote["id"], None)
    assert error.value.code == Code.UNAUTHENTICATED
    assert error.value.message == "Debes iniciar sesión"


def test_grpc_with_an_invalid_token(grpc, analyzed_quote):
    with pytest.raises(ConnectError) as error:
        stream(grpc, analyzed_quote["id"], "no-es-un-jwt")
    assert error.value.code == Code.UNAUTHENTICATED


def test_grpc_another_users_quote_does_not_exist(grpc, other, analyzed_quote):
    with pytest.raises(ConnectError) as error:
        stream(grpc, analyzed_quote["id"], token(other))
    assert error.value.code == Code.NOT_FOUND


def test_grpc_needs_an_analyzed_quote(grpc, client, quote):
    with pytest.raises(ConnectError) as error:
        stream(grpc, quote["id"], token(client))
    assert error.value.code == Code.FAILED_PRECONDITION


def test_grpc_rejects_out_of_range(grpc, client, analyzed_quote):
    with pytest.raises(ConnectError) as error:
        stream(grpc, analyzed_quote["id"], token(client), runs=10)
    assert error.value.code == Code.INVALID_ARGUMENT
    assert "entre 1.000 y 200.000" in error.value.message
