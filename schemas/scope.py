from typing import Annotated

from pydantic import BaseModel, StringConstraints

ScopeText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=20000)]


class ScopeInput(BaseModel):
    scope_description: ScopeText
