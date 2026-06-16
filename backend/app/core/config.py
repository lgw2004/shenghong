from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_name: str = "FastAPI App"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/app"

    # MinIO / S3
    minio_endpoint: str = "121.43.60.72:9010"
    minio_access_key: str = "aIR9gFFJCYfEaPHRoe2l"
    minio_secret_key: str = "pOxN2QjaniBJcqeuPSd2BEVpRk0sluPbJ316wI1R"
    minio_session_token: str = ""
    minio_bucket: str = "dev-sherp"
    minio_secure: bool = False
    minio_region: str = "cn-south-1"

    # Proxy（可选，服务器海外访问用。格式 http://user:pass@host:port 或 socks5://host:port）
    proxy_server: str = ""

    # Crawler
    crawler_delay_seconds: int = 5
    crawler_max_retries: int = 3
    crawler_browser_channel: str = ""   # "chrome"=系统Chrome, ""=Playwright自带Chromium

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
