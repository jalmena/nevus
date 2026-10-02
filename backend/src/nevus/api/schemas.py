"""Request and response bodies."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from nevus.auth.passwords import MIN_PASSWORD_LENGTH

Username = Field(min_length=2, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
Password = Field(min_length=MIN_PASSWORD_LENGTH, max_length=1024)
Language = Literal["en", "es"]
Theme = Literal["system", "light", "dark"]
AccessRole = Literal["owner", "manager", "viewer"]


class Credentials(BaseModel):
    username: str = Username
    password: str = Password


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    email: str | None
    role: Literal["admin", "member"]
    language: str
    theme: str
    show_uncertainty: bool
    card_line_mm: float | None
    email_reminders: bool
    created_at: datetime
    last_login_at: datetime | None
    disabled_at: datetime | None
    totp_enabled: bool = False


class SessionOut(BaseModel):
    user: UserOut
    sudo_until: datetime | None
    instance_claimed: bool = True


class LoginOut(BaseModel):
    """A session, or word that the account's second factor is needed before there is one."""

    session: SessionOut | None = None
    second_factor_required: bool = False


class SecondFactorIn(BaseModel):
    code: str | None = Field(default=None, min_length=6, max_length=16, description="From the authenticator")
    recovery_code: str | None = Field(default=None, min_length=8, max_length=16)


class TotpCodeIn(BaseModel):
    code: str = Field(min_length=6, max_length=16)


class TotpSetupOut(BaseModel):
    secret: str
    otpauth_uri: str
    qr_svg: str


class TotpStatusOut(BaseModel):
    enabled: bool
    enabled_at: datetime | None
    setting_up: bool
    recovery_codes_left: int


class RecoveryCodesOut(BaseModel):
    recovery_codes: list[str]


class InstanceStatus(BaseModel):
    claimed: bool
    version: str
    auth_mode: Literal["local", "proxy"] = "local"
    logout_url: str | None = None


class UserCreate(BaseModel):
    username: str = Username
    password: str = Password
    role: Literal["admin", "member"] = "member"
    email: str | None = Field(default=None, max_length=254)


class UserUpdateMe(BaseModel):
    language: Language | None = None
    theme: Theme | None = None
    show_uncertainty: bool | None = None
    email: str | None = Field(default=None, max_length=254)
    card_line_mm: float | None = Field(
        default=None, ge=45.0, le=55.0, description="Measured length of the printed card's 50 mm line"
    )
    email_reminders: bool | None = None


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=1024)
    new_password: str = Password


class PasswordReset(BaseModel):
    new_password: str = Password


class SudoIn(BaseModel):
    password: str | None = Field(default=None, min_length=1, max_length=1024, description="Not used in proxy mode")


class PersonIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)
    birth_year: int | None = Field(default=None, ge=1900, le=2100)
    skin_tone: str | None = Field(default=None, max_length=16)

    @field_validator("display_name")
    @classmethod
    def _strip(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("display_name must not be blank")
        return value


class PersonUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    birth_year: int | None = Field(default=None, ge=1900, le=2100)
    skin_tone: str | None = Field(default=None, max_length=16)
    experimental_analysis: bool | None = None


class PersonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    display_name: str
    birth_year: int | None
    skin_tone: str | None
    owner_user_id: uuid.UUID
    experimental_analysis: bool
    created_at: datetime
    updated_at: datetime
    my_role: AccessRole


class AccessOut(BaseModel):
    user_id: uuid.UUID
    username: str
    role: AccessRole


class AccessIn(BaseModel):
    username: str = Username
    role: Literal["manager", "viewer"]
