"""集中配置：全部来自环境变量，默认值与 .env.example 保持一致。"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # 数据库
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "maskguard"
    db_user: str = "maskguard"
    db_password: str = "maskguard_pw_2026"

    # 安全
    jwt_secret: str = "maskguard-jwt-secret-change-me-2026"
    hash_salt: str = "maskguard-pepper-2026"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 120
    refresh_token_days: int = 7

    # 运行时
    redis_url: str = "redis://localhost:6379/0"
    artifact_dir: str = "/data/artifacts"
    rate_limit_per_minute: int = 120
    seed_demo: bool = True

    # 数据 schema：平台元数据 / 上游业务库
    meta_schema: str = "meta"
    raw_schema: str = "clinic"

    # k-匿名校验口径
    default_target_k: int = 5
    default_target_l: int = 2
    # 年龄计算基准日（固定，保证 seed 与校验可复现）
    age_reference_date: str = "2026-11-10"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
