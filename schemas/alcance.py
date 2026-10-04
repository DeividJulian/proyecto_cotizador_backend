from typing import Annotated

from pydantic import BaseModel, StringConstraints

TextoAlcance = Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=20000)]


class AlcanceEntrada(BaseModel):
    descripcion_alcance: TextoAlcance
