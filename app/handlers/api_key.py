# app/handlers/api_key.py

import asyncio
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from app.ui.keyboards import main_menu_kb, BTN_KEY_SET, BTN_KEY_DEL
from app.db.mongo import Mongo, upsert_user, delete_user_key
from app.security.crypto import CryptoBox
from app.services.gemini_media import GeminiMedia

router = Router()


class KeyState(StatesGroup):
    waiting_key = State()


@router.message(F.text == BTN_KEY_SET)
async def ask_key(m: Message, state: FSMContext):
    await state.set_state(KeyState.waiting_key)
    await m.answer(
        "🔑 Envíame tu *Gemini API Key* en un mensaje.\n\n"
        "✅ Se guardará en MongoDB *encriptada*.\n"
        "⚠️ Si tu key no tiene cuota/billing, igual la guardo y te aviso.\n\n"
        "Para cancelar: 🏠 Menú",
        reply_markup=main_menu_kb(),
        parse_mode="Markdown",
    )


@router.message(KeyState.waiting_key)
async def save_key(
    m: Message,
    state: FSMContext,
    mongo: Mongo,
    crypto: CryptoBox,
    gemini: GeminiMedia,
):
    key = (m.text or "").strip()

    # Validación mínima (solo para evitar basura)
    if len(key) < 20:
        return await m.answer(
            "Esa key se ve muy corta. Pégala completa.",
            reply_markup=main_menu_kb(),
        )

    await m.answer("🔎 Guardando y verificando API Key…", reply_markup=main_menu_kb())

    # Siempre intentamos verificar, pero si falla por cuota (429) u otros,
    # igual guardamos la key y solo avisamos.
    try:
        ok = await asyncio.to_thread(gemini.validate_api_key, key)

        enc = crypto.encrypt(key)
        await upsert_user(mongo, m.from_user.id, {"api_key_enc": enc})
        await state.clear()

        if ok:
            await m.answer("✅ API Key guardada y verificada.", reply_markup=main_menu_kb())
        else:
            await m.answer(
                "✅ API Key guardada.\n"
                "⚠️ No pude verificarla ahora mismo (puede ser cuota/billing o restricciones del proyecto).",
                reply_markup=main_menu_kb(),
            )

    except Exception as e:
        # Guardamos igual aunque falle la verificación
        enc = crypto.encrypt(key)
        await upsert_user(mongo, m.from_user.id, {"api_key_enc": enc})
        await state.clear()

        msg = str(e)

        # Caso típico: 429 RESOURCE_EXHAUSTED (no hay cuota/billing)
        if ("429" in msg) or ("RESOURCE_EXHAUSTED" in msg) or ("Quota exceeded" in msg):
            await m.answer(
                "✅ API Key guardada.\n"
                "⚠️ Tu key/proyecto está sin cuota o sin billing (429 RESOURCE_EXHAUSTED).\n"
                "Cuando actives plan/billing, ya podrás generar imagen/video/edición.",
                reply_markup=main_menu_kb(),
            )
        else:
            await m.answer(
                "✅ API Key guardada.\n"
                f"⚠️ No pude verificarla ahora mismo: {e}",
                reply_markup=main_menu_kb(),
            )


@router.message(F.text == BTN_KEY_DEL)
async def del_key(m: Message, state: FSMContext, mongo: Mongo):
    await state.clear()
    removed = await delete_user_key(mongo, m.from_user.id)
    if removed:
        await m.answer("🗑️ API Key eliminada.", reply_markup=main_menu_kb())
    else:
        await m.answer("No tenía API Key guardada.", reply_markup=main_menu_kb())
