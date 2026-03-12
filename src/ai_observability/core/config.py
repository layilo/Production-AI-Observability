from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="production-ai-observability", alias="AI_OBS_APP_NAME")
    environment: str = Field(default="demo", alias="AI_OBS_ENVIRONMENT")
    release: str = Field(default="0.1.0", alias="AI_OBS_RELEASE")
    db_path: str = Field(default="artifacts/observability.db", alias="AI_OBS_DB_PATH")
    redaction_enabled: bool = Field(default=True, alias="AI_OBS_REDACTION_ENABLED")
    redaction_fields: str = Field(
        default="prompt,completion,input,output,user_email,authorization,api_key",
        alias="AI_OBS_REDACTION_FIELDS",
    )
    sampling_rate: float = Field(default=1.0, alias="AI_OBS_SAMPLING_RATE")
    demo_seed: int = Field(default=42, alias="AI_OBS_DEMO_SEED")
    otlp_enabled: bool = Field(default=False, alias="AI_OBS_OTLP_ENABLED")
    otlp_endpoint: str = Field(
        default="http://localhost:4318/v1/traces",
        alias="AI_OBS_OTLP_ENDPOINT",
    )
    otlp_headers: str = Field(default="", alias="AI_OBS_OTLP_HEADERS")
    cost_per_1k_input_tokens: float = Field(
        default=0.003,
        alias="AI_OBS_COST_PER_1K_INPUT_TOKENS",
    )
    cost_per_1k_output_tokens: float = Field(
        default=0.006,
        alias="AI_OBS_COST_PER_1K_OUTPUT_TOKENS",
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def redaction_field_set(self) -> set[str]:
        return {field.strip() for field in self.redaction_fields.split(",") if field.strip()}

    @property
    def db_file(self) -> Path:
        path = Path(self.db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

