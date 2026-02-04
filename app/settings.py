# -*- coding: utf-8 -*-
import os
import sys
import asyncio
from pathlib import Path

# === 引入所需库 ===
from hcaptcha_challenger.agent import AgentConfig
from pydantic import Field, SecretStr
from pydantic_settings import SettingsConfigDict
from loguru import logger

# --- 核心路径定义 ---
PROJECT_ROOT = Path(__file__).parent
VOLUMES_DIR = PROJECT_ROOT.joinpath("volumes")
LOG_DIR = VOLUMES_DIR.joinpath("logs")
USER_DATA_DIR = VOLUMES_DIR.joinpath("user_data")
HCAPTCHA_DIR = VOLUMES_DIR.joinpath("hcaptcha")

# === 配置类定义 ===
class EpicSettings(AgentConfig):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore")

    # [核心修正] 全部默认值强制改为你要求的 gemini-2.0-flash-free
    GEMINI_MODEL: str = Field(
        default=os.getenv("GEMINI_MODEL", "gemini-2.0-flash-free"),
        description="模型名称",
    )
    CHALLENGE_CLASSIFIER_MODEL: str = Field(default=os.getenv("GEMINI_MODEL", "gemini-2.0-flash-free"))
    IMAGE_CLASSIFIER_MODEL: str = Field(default=os.getenv("GEMINI_MODEL", "gemini-2.0-flash-free"))
    SPATIAL_POINT_REASONER_MODEL: str = Field(default=os.getenv("GEMINI_MODEL", "gemini-2.0-flash-free"))
    SPATIAL_PATH_REASONER_MODEL: str = Field(default=os.getenv("GEMINI_MODEL", "gemini-2.0-flash-free"))

    GEMINI_API_KEY: SecretStr | None = Field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY"),
        description="AiHubMix 的令牌",
    )
    GEMINI_BASE_URL: str = Field(
        default=os.getenv("GEMINI_BASE_URL", "https://aihubmix.com"),
        description="中转地址",
    )

    EPIC_EMAIL: str = Field(default_factory=lambda: os.getenv("EPIC_EMAIL"))
    EPIC_PASSWORD: SecretStr = Field(default_factory=lambda: os.getenv("EPIC_PASSWORD"))
    DISABLE_BEZIER_TRAJECTORY: bool = Field(default=True)

    cache_dir: Path = HCAPTCHA_DIR.joinpath(".cache")
    challenge_dir: Path = HCAPTCHA_DIR.joinpath(".challenge")
    captcha_response_dir: Path = HCAPTCHA_DIR.joinpath(".captcha")

    ENABLE_APSCHEDULER: bool = Field(default=True)
    TASK_TIMEOUT_SECONDS: int = Field(default=900)
    REDIS_URL: str = Field(default="redis://redis:6379/0")

    @property
    def user_data_dir(self) -> Path:
        target_ = USER_DATA_DIR.joinpath(self.EPIC_EMAIL)
        target_.mkdir(parents=True, exist_ok=True)
        return target_

settings = EpicSettings()
settings.ignore_request_questions = ["Please drag the crossing to complete the lines"]

# ==========================================
# [AiHubMix 终极补丁 V3] 多图分辨率修复版
# ==========================================
def _apply_aihubmix_patch():
    if not settings.GEMINI_API_KEY:
        return
    try:
        from google import genai
        from google.genai import types
        
        # 1. 劫持初始化
        orig_init = genai.Client.__init__
        def new_init(self, *args, **kwargs):
            api_key = settings.GEMINI_API_KEY.get_secret_value() if hasattr(settings.GEMINI_API_KEY, 'get_secret_value') else str(settings.GEMINI_API_KEY)
            kwargs['api_key'] = api_key
            base_url = settings.GEMINI_BASE_URL.rstrip('/')
            if base_url.endswith('/v1'): base_url = base_url[:-3]
            if not base_url.endswith('/gemini'): base_url = f"{base_url}/gemini"
            kwargs['http_options'] = types.HttpOptions(base_url=base_url)
            logger.info(f"🚀 补丁生效 | 强制模型: {settings.GEMINI_MODEL}")
            orig_init(self, *args, **kwargs)
        genai.Client.__init__ = new_init

        # 2. 劫持生成逻辑 (按你说的，解决多图分辨率报错问题)
        file_cache = {}
        async def patched_upload(self_files, file, **kwargs):
            if hasattr(file, 'read'): content = file.read()
            elif isinstance(file, (str, Path)):
                with open(file, 'rb') as f: content = f.read()
            else: content = bytes(file)
            if asyncio.iscoroutine(content): content = await content
            file_id = f"bypass_{id(content)}"
            file_cache[file_id] = content
            return types.File(name=file_id, uri=file_id, mime_type="image/png")

        orig_generate = genai.models.AsyncModels.generate_content
        async def patched_generate(self_models, model, contents, **kwargs):
            # [关键修复] 只要请求里带了 config，就强行把 media_resolution 删掉
            # 这能彻底绕过“多张图片不准用高分辨率”的 400 报错
            if 'config' in kwargs and kwargs['config'] is not None:
                if hasattr(kwargs['config'], 'media_resolution'):
                    kwargs['config'].media_resolution = None 

            normalized = contents if isinstance(contents, list) else [contents]
            for content in normalized:
                if hasattr(content, 'parts'):
                    for i, part in enumerate(content.parts):
                        if part.file_data and part.file_data.file_uri in file_cache:
                            data = file_cache[part.file_data.file_uri]
                            content.parts[i] = types.Part.from_bytes(data=data, mime_type="image/png")
            return await orig_generate(self_models, model=model, contents=normalized, **kwargs)

        genai.files.AsyncFiles.upload = patched_upload
        genai.models.AsyncModels.generate_content = patched_generate
        logger.info("🚀 分辨率降写保护已加载。")
    except Exception as e:
        logger.error(f"❌ 补丁异常: {e}")

_apply_aihubmix_patch()
