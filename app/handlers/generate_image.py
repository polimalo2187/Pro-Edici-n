import asyncio
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from app.ui.keyboards import main_menu_kb, gen_mode_kb, BTN_IMAGE, BTN_HD, BTN_MENU
from app.db.mongo import Mongo, get_user_api_key_enc, upsert_user, get_user_quality
from app.security.crypto import CryptoBox
from app.services.gemini_media import GeminiMedia

router = Router()

class ImageState(StatesGroup):
    waiting_prompt = State()

@router.message(F.text == BTN_IMAGE)
async def image_mode(m: Message, state: FSMContext, mongo: Mongo):
    await state.set_state(ImageState.waiting_prompt)
    # cargar quality actual desde DB para mostrar
    q = await get_user_quality(mongo, m.from_user.id)
    await m.answer(
        f"🖼️ *Modo IMAGEN*\n\nEnvíame el prompt.\n\nCalidad: `{q}` (toca ✨ HD para cambiar)\n"
        "Para salir: 🏠 Menú",
        reply_markup=gen_mode_kb(),
        parse_mode="Markdown",
    )

@router.message(F.text == BTN_HD)
async def toggle_hd_image(m: Message, mongo: Mongo):
    q = await get_user_quality(mongo, m.from_user.id)
    new_q = "hd" if q != "hd" else "normal"
    await upsert_user(mongo, m.from_user.id, {"quality": new_q})
    await m.answer(f"✨ Calidad cambiada a: *{new_q}*", reply_markup=gen_mode_kb(), parse_mode="Markdown")

@router.message(ImageState.waiting_prompt, F.text)
async def do_image(
    m: Message,
    state: FSMContext,
    mongo: Mongo,
    crypto: CryptoBox,
    gemini: GeminiMedia,
):
    # si usuario toca menú, lo maneja menu.py, pero por si acaso:
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

    q = await get_user_quality(mongo, m.from_user.id)
    hd = (q == "hd")

    status = await m.answer("🖼️ Generando imagen…", reply_markup=gen_mode_kb())
    try:
        api_key = crypto.decrypt(enc)
        img_bytes = await asyncio.to_thread(gemini.generate_image, api_key, prompt, hd)
        await status.delete()
        await m.answer_photo(photo=img_bytes, caption="✅ Imagen lista", reply_markup=main_menu_kb())
        await state.clear()
    except Exception as e:
        await status.edit_text(f"⚠️ Error generando imagen:\n{e}")
