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
RUNTIME_DIR = VOLUMES_DIR.joinpath("runtime")
SCREENSHOTS_DIR = VOLUMES_DIR.joinpath("screenshots")
RECORD_DIR = VOLUMES_DIR.joinpath("record")
HCAPTCHA_DIR = VOLUMES_DIR.joinpath("hcaptcha")

# 获取用户设置的 Master 模型名，默认使用 gemini-2.0-flash-free
_MASTER_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-free")

# === 配置类定义 ===
class EpicSettings(AgentConfig):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore")

    # [核心修正：自动对齐细分变量]
    # 全部强行统一为指定的 Master 模型 ID
    GEMINI_MODEL: str = Field(default=_MASTER_MODEL, description="Master 模型 ID")
    CHALLENGE_CLASSIFIER_MODEL: str = Field(default=_MASTER_MODEL)
    IMAGE_CLASSIFIER_MODEL: str = Field(default=_MASTER_MODEL)
    SPATIAL_POINT_REASONER_MODEL: str = Field(default=_MASTER_MODEL)
    SPATIAL_PATH_REASONER_MODEL: str = Field(default=_MASTER_MODEL)

    # [基础配置]
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
    # 调高超时限制，防止下单重载导致 Timeout
    EXECUTION_TIMEOUT: float = Field(default=240.0) 
    RESPONSE_TIMEOUT: float = Field(default=60.0)

    REDIS_URL: str = Field(default="redis://redis:6379/0")
    CELERY_WORKER_CONCURRENCY: int = Field(default=1)
    CELERY_TASK_TIME_LIMIT: int = Field(default=1200)
    CELERY_TASK_SOFT_TIME_LIMIT: int = Field(default=900)

    @property
    def user_data_dir(self) -> Path:
        target_ = USER_DATA_DIR.joinpath(self.EPIC_EMAIL)
        target_.mkdir(parents=True, exist_ok=True)
        return target_

settings = EpicSettings()
settings.ignore_request_questions = ["Please drag the crossing to complete the lines"]

# ========================= 处理中转解析与多图冲突 =========================
def _apply_aihubmix_patch():
    if not settings.GEMINI_API_KEY:
        return

    try:
        from google import genai
        from google.genai import types
        
        # 1. 劫持 Client 初始化 (自动修正中转路径)
        orig_init = genai.Client.__init__
        def new_init(self, *args, **kwargs):
            if hasattr(settings.GEMINI_API_KEY, 'get_secret_value'):
                api_key = settings.GEMINI_API_KEY.get_secret_value()
            else:
                api_key = str(settings.GEMINI_API_KEY)
            
            kwargs['api_key'] = api_key
            
            base_url = settings.GEMINI_BASE_URL.rstrip('/')
            if base_url.endswith('/v1'): base_url = base_url[:-3]
            if not base_url.endswith('/gemini'): base_url = f"{base_url}/gemini"
            
            kwargs['http_options'] = types.HttpOptions(base_url=base_url)
            logger.info(f"🚀 已强行同步模型变量 | 当前生效 ID: {settings.GEMINI_MODEL} | 地址: {base_url}")
            orig_init(self, *args, **kwargs)
        
        genai.Client.__init__ = new_init

        # 2. 劫持文件上传与生成逻辑 (修复 400 报错与 Base64 兼容)
        try:
            file_cache = {}

            def _local_to_list(c):
                return c if isinstance(c, list) else [c]

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
                # [修正：针对多图发送时的分辨率冲突]
                if 'config' in kwargs and kwargs['config'] is not None:
                    if hasattr(kwargs['config'], 'media_resolution'):
                        kwargs['config'].media_resolution = None # 剔除写死的 HIGH 分辨率

                normalized = _local_to_list(contents)
                
                for content in normalized:
                    if hasattr(content, 'parts'):
                        for i, part in enumerate(content.parts):
                            if part.file_data and part.file_data.file_uri in file_cache:
                                data = file_cache[part.file_data.file_uri]
                                content.parts[i] = types.Part.from_bytes(data=data, mime_type="image/png")
                
                # 强制使用关键字参数确保 API 握手成功
                return await orig_generate(self_models, model=model, contents=normalized, **kwargs)

            genai.files.AsyncFiles.upload = patched_upload
            genai.models.AsyncModels.generate_content = patched_generate
            logger.info("🚀 补丁成功挂载：多图写保护 + 模型 ID 动态注入已就绪")
            
        except Exception as ie:
            logger.warning(f"⚠️ 文件层补丁处理异常: {ie}")

    except Exception as e:
        logger.error(f"❌ 严重：补丁框架启动失败! 原因: {e}")

# 执行补丁
_apply_aihubmix_patch()
