from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]
Code = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^\d{6}$")]


class RegisterInput(BaseModel):
    name: Name
    email: EmailStr


class LoginInput(BaseModel):
    email: EmailStr


class VerifyInput(BaseModel):
    email: EmailStr
    code: Code


class PasswordLoginInput(BaseModel):
    """Only for the demo account (DEMO_ACCOUNTS): everybody else logs in with an emailed code."""
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    created_at: datetime
    last_login_at: datetime | None


class SessionOut(BaseModel):
    token: str
    user: UserOut


class CodeSent(BaseModel):
    message: str
    email: str
