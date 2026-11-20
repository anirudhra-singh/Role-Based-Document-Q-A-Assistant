import uuid
from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.core.constants import ROLES


class UserOut(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role: str
    department: str | None


class UserAdminOut(UserOut):
    is_active: bool
    created_at: datetime


def _check_role(value: str | None) -> str:
    if value not in ROLES:  
        raise ValueError(f"role must be one of: {', '.join(ROLES)}")
    return value


def _clean_department(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None  


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=12, max_length=128)
    role: str
    department: str | None = Field(default=None, max_length=100)

    _role_ok = field_validator("role")(_check_role)
    _department_clean = field_validator("department")(_clean_department)


class UserUpdate(BaseModel):

    model_config = ConfigDict(extra="forbid")

    role: str | None = None
    department: str | None = Field(default=None, max_length=100)
    is_active: bool | None = None

    _role_ok = field_validator("role")(_check_role)
    _department_clean = field_validator("department")(_clean_department)

    @field_validator("is_active")
    @classmethod
    def is_active_not_null(cls, value: bool | None) -> bool:
        if value is None:
            raise ValueError("is_active cannot be null")
        return value

    @model_validator(mode="after")
    def at_least_one_field(self) -> "UserUpdate":
        if not self.model_fields_set:
            raise ValueError("send at least one field to update")
        return self