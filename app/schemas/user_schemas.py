import uuid

from pydantic import BaseModel, ConfigDict


class UserOut(BaseModel):
    """What the API may show about a user. Never includes password_hash."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role: str
    department: str | None