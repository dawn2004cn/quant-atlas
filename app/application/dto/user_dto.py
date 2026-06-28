from __future__ import annotations
"""DTOs for User and Authentication services."""


from pydantic import BaseModel, Field


class UserDTO(BaseModel):
    """Public user information."""
    id: int
    username: str
    role: str
    role_name: str
    protected: bool = False
    avatar_url: str = ""


class UserAccountDTO(BaseModel):
    """Public user information (alias for UserDTO)."""
    id: int
    username: str
    role: str
    role_name: str
    protected: bool = False
    avatar_url: str = ""


class RoleDTO(BaseModel):
    """Role information."""
    id: int
    code: str
    label: str
    sort_order: int = 0


class CreateUserCommand(BaseModel):
    """Command to create a new user."""
    username: str = Field(..., min_length=3, max_length=32)
    password: str = Field(..., min_length=6)
    role: str = "viewer"


class ChangePasswordCommand(BaseModel):
    """Command to change user password."""
    target_username: str | None = None
    new_password: str = Field(..., min_length=6)
    confirm_password: str
    old_password: str | None = None


UserCreateDTO = CreateUserCommand


class UserUpdateDTO(BaseModel):
    """DTO for updating user information."""
    username: str | None = Field(default=None, min_length=3, max_length=32)
    role: str | None = None
    avatar_url: str | None = None
