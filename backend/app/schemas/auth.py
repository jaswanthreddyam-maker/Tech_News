from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Schema for new user registration."""

    name: str = Field(..., min_length=1, max_length=150, description="User display name")
    email: EmailStr = Field(..., description="Valid email address")
    password: str = Field(..., min_length=8, max_length=128, description="Password (minimum 8 characters)")


class LoginRequest(BaseModel):
    """Schema for email/password login."""

    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., description="Account password")
    remember_me: bool = Field(False, description="Extend refresh token duration when True")


class TokenResponse(BaseModel):
    """Schema returned after successful authentication."""

    access_token: str = Field(..., description="JWT access token for API authorization")
    token_type: str = Field("bearer", description="Token type identifier")
    user: dict = Field(..., description="Authenticated user summary")


class UserResponse(BaseModel):
    """Schema for user profile data."""

    id: int
    name: str
    email: str
    role: str | None = None
    permissions: list[str] = Field(default_factory=list)
    status: str


class GoogleAuthRequest(BaseModel):
    """Schema for Google OAuth ID token submission."""

    credential: str = Field(..., description="Google ID token from client-side sign-in")
