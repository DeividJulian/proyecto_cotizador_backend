from pydantic import BaseModel


class Message(BaseModel):
    """Confirmation in Spanish, shown to the user."""
    message: str


class Health(BaseModel):
    status: str


class Error(BaseModel):
    """Every error of the API: a message in Spanish that the front shows as is."""
    detail: str


_DESCRIPTIONS = {
    400: "Código inválido o vencido",
    401: "Falta el token o venció",
    404: "No existe o es de otro usuario",
    409: "Conflicto con el estado actual",
    422: "Datos inválidos",
    429: "Demasiadas solicitudes (puede traer Retry-After)",
    502: "Falló un servicio externo (correo o IA)",
    503: "La IA no está configurada",
}


def errors(*codes: int) -> dict:
    """OpenAPI `responses` for these status codes, all with the Error schema."""
    return {code: {"model": Error, "description": _DESCRIPTIONS[code]} for code in codes}


def json_errors(*codes: int) -> dict:
    """Same as errors(), for a route whose success is not JSON (the errors still are)."""
    ref = {"$ref": "#/components/schemas/Error"}
    return {code: {"description": _DESCRIPTIONS[code], "content": {"application/json": {"schema": ref}}} for code in codes}
