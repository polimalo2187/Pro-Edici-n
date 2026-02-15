import asyncio
from io import BytesIO
from typing import List, Optional

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from app.ui.keyboards import (
    main_menu_kb,
    edit_mode_kb,
    BTN_EDIT,
    BTN_DONE,
    BTN_HD,
    BTN_MENU,
)
from app.db.mongo import Mongo, get_user_api_key_enc, get_user_quality, upsert_user
from app.security.crypto import CryptoBox
from app.services.gemini_media import GeminiMedia

router = Router()

class EditState(StatesGroup):
    waiting_photos = State()
    waiting_instruction = State()

async def _download_photo_bytes(m: Message) -> Optional[bytes]:
    """
    Foto de Telegram -> bytes
    """
    if not m.photo:
        return None
    photo = m.photo[-1]  # mejor resolución disponible
    # aiogram puede descargar directo:
    buf = BytesIO()
    await m.bot.download(photo.file_id, destination=buf)
    return buf.getvalue()

@router.message(F.text == BTN_EDIT)
async def edit_mode(m: Message, state: FSMContext, mongo: Mongo):
    await state.set_state(EditState.waiting_photos)
    await state.update_data(photos=[], instruction=None)

    q = await get_user_quality(mongo, m.from_user.id)
    await m.answer(
        "🧩 *Editar imágenes (montaje realista por defecto)*\n\n"
        "1) Envíame *hasta 2 fotos*\n"
        "2) Toca ✅ Listo\n"
        "3) Escribe la instrucción (ej: “foto natural abrazados, sin cambiar rostros”).\n\n"
        f"Calidad: `{q}` (toca ✨ HD para cambiar)\n"
        "Para salir: 🏠 Menú",
        reply_markup=edit_mode_kb(),
        parse_mode="Markdown",
    )

@router.message(F.text == BTN_HD)
async def toggle_hd_edit(m: Message, mongo: Mongo):
    q = await get_user_quality(mongo, m.from_user.id)
    new_q = "hd" if q != "hd" else "normal"
    await upsert_user(mongo, m.from_user.id, {"quality": new_q})
    await m.answer(f"✨ Calidad cambiada a: *{new_q}*", reply_markup=edit_mode_kb(), parse_mode="Markdown")

@router.message(EditState.waiting_photos, F.photo)
async def receive_photo(m: Message, state: FSMContext):
    data = await state.get_data()
    photos: List[bytes] = data.get("photos", [])

    if len(photos) >= 2:
        return await m.answer("Por ahora solo 2 fotos. Toca 🏠 Menú para reiniciar.", reply_markup=edit_mode_kb())

    b = await _download_photo_bytes(m)
    if not b:
        return await m.answer("No pude leer esa foto. Intenta de nuevo.", reply_markup=edit_mode_kb())

    photos.append(b)
    await state.update_data(photos=photos)

    if len(photos) == 1:
        await m.answer("📥 Foto 1/2 recibida. Envía la segunda o toca ✅ Listo.", reply_markup=edit_mode_kb())
    else:
        await m.answer("📥 Foto 2/2 recibida. Ahora toca ✅ Listo.", reply_markup=edit_mode_kb())

@router.message(EditState.waiting_photos, F.text == BTN_DONE)
async def done_photos(m: Message, state: FSMContext):
    data = await state.get_data()
    photos: List[bytes] = data.get("photos", [])
    if not photos:
        return await m.answer("Aún no he recibido fotos. Envíame 1 o 2.", reply_markup=edit_mode_kb())
    if len(photos) == 1:
        # Para fase 1: solo 2 fotos para montaje realista.
        # Si quieres 1 foto edición, lo activamos después.
        return await m.answer("Para montaje realista necesito 2 fotos. Envíame la segunda.", reply_markup=edit_mode_kb())

    await state.set_state(EditState.waiting_instruction)
    await m.answer(
        "📝 Perfecto. Ahora escribe *qué montaje realista quieres*.\n\n"
        "Ejemplos:\n"
        "• “Foto natural abrazados, sin cambiar rostros, luz cálida”\n"
        "• “Que parezca selfie, fondo cafetería, realista”\n",
        reply_markup=edit_mode_kb(),
        parse_mode="Markdown",
    )

@router.message(EditState.waiting_instruction, F.text)
async def do_edit(
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

    instruction = (m.text or "").strip()
    if not instruction:
        return await m.answer("Escribe la instrucción en texto.", reply_markup=edit_mode_kb())

    data = await state.get_data()
    photos: List[bytes] = data.get("photos", [])
    if len(photos) != 2:
        await state.set_state(EditState.waiting_photos)
        return await m.answer("Me faltan fotos (necesito 2). Envía las fotos otra vez.", reply_markup=edit_mode_kb())

    q = await get_user_quality(mongo, m.from_user.id)
    hd = (q == "hd")

    status = await m.answer("🪄 Creando montaje realista… (puede tardar)", reply_markup=edit_mode_kb())
    try:
        api_key = crypto.decrypt(enc)
        out_bytes = await asyncio.to_thread(gemini.edit_images_realistic_montage, api_key, instruction, photos, hd)
        await status.delete()
        await m.answer_photo(photo=out_bytes, caption="✅ Montaje listo", reply_markup=main_menu_kb())
        await state.clear()
    except Exception as e:
        await status.edit_text(f"⚠️ Error creando montaje:\n{e}")
