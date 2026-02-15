import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import load_settings
from app.logging_setup import setup_logging
from app.handlers.router import build_router
from app.db.mongo import init_mongo
from app.security.crypto import CryptoBox
from app.services.gemini_media import GeminiMedia

async def main():
    setup_logging()
    log = logging.getLogger("app")

    s = load_settings()

    bot = Bot(
        token=s.telegram_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(build_router())

    mongo = await init_mongo(s.mongodb_uri, s.mongodb_db)

    crypto = CryptoBox(s.api_key_enc_secret)
    gemini = GeminiMedia(
        model_image_fast=s.model_image_fast,
        model_image_hd=s.model_image_hd,
        model_video=s.model_video,
    )

    @dp.update.middleware()
    async def inject(handler, event, data):
        data["mongo"] = mongo
        data["crypto"] = crypto
        data["gemini"] = gemini
        return await handler(event, data)

    log.info("Bot iniciado.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
