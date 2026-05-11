from pydantic import BaseModel, Field, field_validator


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)

    @field_validator('username')
    @classmethod
    def validate_username(cls, value: str) -> str:
        value = value.strip()
        if not value.replace('_', '').isalnum():
            raise ValueError('Username must be alphanumeric and may include underscores.')
        return value


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'


class UserResponse(BaseModel):
    id: int
    username: str


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(min_length=3, max_length=100)


class ApiKeyResponse(BaseModel):
    name: str
    prefix: str
    api_key: str
