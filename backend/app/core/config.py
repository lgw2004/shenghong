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
    # 按站点分配代理（JSON 格式），如 {"US":"http://1.2.3.4:7890","UK":"socks5://5.6.7.8:1080"}
    # 优先匹配 site_code，没匹配到则回退到 proxy_server
    proxy_map: str = ""

    # Crawler
    crawler_delay_seconds: int = 1
    crawler_max_retries: int = 3
    crawler_browser_channel: str = ""   # "chrome"=系统Chrome, ""=Playwright自带Chromium
    crawler_concurrency: int = 3         # 并发处理条数

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
