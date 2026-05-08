from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str
    JWT_PRIVATE_KEY: str
    JWT_PUBLIC_KEY: str
    SECRET_KEY: str

    ENVIRONMENT: str = "development"
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    BCRYPT_ROUNDS: int = 12

    @field_validator("BCRYPT_ROUNDS")
    @classmethod
    def bcrypt_rounds_minimum(cls, v: int) -> int:
        if v < 10:
            raise ValueError("BCRYPT_ROUNDS must be at least 10")
        return v

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def jwt_private_key_pem(self) -> str:
        return self.JWT_PRIVATE_KEY.replace("\\n", "\n")

    @property
    def jwt_public_key_pem(self) -> str:
        return self.JWT_PUBLIC_KEY.replace("\\n", "\n")


settings = Settings()
