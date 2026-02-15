import asyncio
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from app.ui.keyboards import main_menu_kb, gen_mode_kb, BTN_VIDEO, BTN_MENU
from app.db.mongo import Mongo, get_user_api_key_enc
from app.security.crypto import CryptoBox
from app.services.gemini_media import GeminiMedia

router = Router()

class VideoState(StatesGroup):
    waiting_prompt = State()

@router.message(F.text == BTN_VIDEO)
async def video_mode(m: Message, state: FSMContext):
    await state.set_state(VideoState.waiting_prompt)
    await m.answer(
        "🎬 *Modo VIDEO*\n\nEnvíame el prompt del video (Veo).\n"
        "Para salir: 🏠 Menú",
        reply_markup=gen_mode_kb(),
        parse_mode="Markdown",
    )

@router.message(VideoState.waiting_prompt, F.text)
async def do_video(
    m: Message,
    state: FSMContext,
    mongo: Mongo,
    crypto: CryptoBox,
    gemini: GeminiMedia,
):
    if (m.text or "").strip() == BTN_MENU:
        await state.clear()
        return await m.answer("🏠 Menú", reply_markup=main_menu_kb())

    enc = await get_user_api_key_enc(mongo, m.from_user.id)
    if not enc:
        await state.clear()
        return await m.answer("Primero conecta tu API Key 🔑", reply_markup=main_menu_kb())

    prompt = (m.text or "").strip()
    if not prompt:
        return await m.answer("Escribe un prompt en texto.", reply_markup=gen_mode_kb())

    status = await m.answer("🎬 Generando video… (puede tardar)", reply_markup=gen_mode_kb())
    try:
        api_key = crypto.decrypt(enc)
        video_bytes = await asyncio.to_thread(gemini.generate_video, api_key, prompt, "720p")
        await status.delete()
        await m.answer_video(video=video_bytes, caption="✅ Video listo", reply_markup=main_menu_kb())
        await state.clear()
    except Exception as e:
        await status.edit_text(f"⚠️ Error generando video:\n{e}")
