from aiogram import Router

from .menu import router as menu_router
from .api_key import router as api_key_router
from .generate_image import router as image_router
from .generate_video import router as video_router
from .edit_images import router as edit_router

def build_router() -> Router:
    r = Router()
    r.include_router(menu_router)
    r.include_router(api_key_router)
    r.include_router(image_router)
    r.include_router(video_router)
    r.include_router(edit_router)
    return r
