"""gRPC service (Connect protocol) of the Monte Carlo simulation, mounted inside the FastAPI app.

It reuses services/simulation.py (the same generator as POST /quotes/{id}/simulation) and the same JWT as the REST
API: the token travels as the "authorization: Bearer <token>" header (gRPC metadata). Only the owner of the quote can
simulate it; for anyone else it does not exist, exactly like in REST.
"""
import asyncio
import logging
from collections.abc import AsyncIterator
from types import SimpleNamespace

from connectrpc.code import Code
from connectrpc.errors import ConnectError
from connectrpc.request import RequestContext

import database
from models.quote import Quote
from proto_gen.cotizador.v1 import simulation_pb2 as pb
from proto_gen.cotizador.v1.simulation_connect import SimulationServiceASGIApplication
from security import INVALID_SESSION, NO_SESSION, user_from_token
from services import simulation

logger = logging.getLogger("cotizador.grpc")


def _token(ctx: RequestContext) -> str:
    scheme, _, token = (ctx.request_headers.get("authorization") or "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise ConnectError(Code.UNAUTHENTICATED, NO_SESSION)
    return token.strip()


def _load_quote(token: str, quote_id: int) -> SimpleNamespace:
    """Checks the session and the owner, and copies what the simulation needs (the DB session closes here)."""
    db = database.SessionLocal()
    try:
        user = user_from_token(db, token)
        if user is None:
            raise ConnectError(Code.UNAUTHENTICATED, INVALID_SESSION)
        quote = db.query(Quote).filter(Quote.id == quote_id, Quote.user_id == user.id).first()
        if quote is None:
            raise ConnectError(Code.NOT_FOUND, "Cotización no encontrada")
        items = [
            SimpleNamespace(
                hours_optimistic=i.hours_optimistic,
                hours_likely=i.hours_likely,
                hours_pessimistic=i.hours_pessimistic,
                hours_expected=i.hours_expected,
            )
            for i in quote.items
        ]
        return SimpleNamespace(items=items, total=quote.total, estimate=dict(quote.estimate or {}))
    finally:
        db.close()


def _to_proto(event: dict) -> pb.SimulateEvent:
    if "progress" in event:
        return pb.SimulateEvent(progress=pb.Progress(**event["progress"]))
    result = dict(event["result"])
    result["histogram"] = [pb.HistogramBin(**b) for b in result["histogram"]]
    return pb.SimulateEvent(result=pb.SimulationResult(**result))


class SimulationRpc:
    async def simulate(self, request: pb.SimulateRequest, ctx: RequestContext) -> AsyncIterator[pb.SimulateEvent]:
        quote = await asyncio.to_thread(_load_quote, _token(ctx), request.quote_id)
        events = simulation.simulate(quote, request.runs, request.samples)
        while True:
            # numpy runs in a thread: the server keeps answering other requests meanwhile.
            # If the browser cancels, the stream is closed here and no more chunks are computed.
            try:
                event = await asyncio.to_thread(next, events, None)
            except simulation.InvalidSimulation as e:
                raise ConnectError(Code.INVALID_ARGUMENT, str(e))
            except simulation.SimulationUnavailable as e:
                raise ConnectError(Code.FAILED_PRECONDITION, str(e))
            if event is None:
                break
            yield _to_proto(event)
        logger.info("gRPC Simulate quote %s: %s runs", request.quote_id, request.runs)


simulation_app = SimulationServiceASGIApplication(SimulationRpc())
