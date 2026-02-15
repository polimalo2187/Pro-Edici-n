import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    telegram_token: str

    mongodb_uri: str
    mongodb_db: str

    api_key_enc_secret: str

    model_image_fast: str
    model_image_hd: str
    model_video: str

    use_mongo_fsm: bool
    fsm_mongo_collection: str

def _must(name: str) -> str:
    v = os.getenv(name, "").strip()
    if not v:
        raise RuntimeError(f"Falta {name} en .env")
    return v

def load_settings() -> Settings:
    return Settings(
        telegram_token=_must("TELEGRAM_BOT_TOKEN"),

        mongodb_uri=_must("MONGODB_URI"),
        mongodb_db=_must("MONGODB_DB"),

        api_key_enc_secret=_must("API_KEY_ENC_SECRET"),

        model_image_fast=os.getenv("MODEL_IMAGE_FAST", "gemini-2.5-flash-image").strip(),
        model_image_hd=os.getenv("MODEL_IMAGE_HD", "gemini-3-pro-image-preview").strip(),
        model_video=os.getenv("MODEL_VIDEO", "veo-3.1-generate-preview").strip(),

        use_mongo_fsm=os.getenv("USE_MONGO_FSM", "1").strip() in ("1", "true", "True", "yes", "YES"),
        fsm_mongo_collection=os.getenv("FSM_MONGO_COLLECTION", "aiogram_fsm").strip(),
    )
