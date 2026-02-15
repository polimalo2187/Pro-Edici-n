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
        "Tip: luego podrás generar Video/Imagen/Edición.\n"
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
    if len(key) < 20:
        return await m.answer("Esa key se ve muy corta. Pégala completa.", reply_markup=main_menu_kb())

    await m.answer("🔎 Verificando API Key…", reply_markup=main_menu_kb())

    try:
        ok = await (  # no bloquear event loop
            __import__("asyncio").to_thread(gemini.validate_api_key, key)
        )
        if not ok:
            await m.answer("❌ No pude validar esa key. Revisa y vuelve a intentar.", reply_markup=main_menu_kb())
            return

        enc = crypto.encrypt(key)
        await upsert_user(mongo, m.from_user.id, {"api_key_enc": enc})
        await state.clear()
        await m.answer("✅ API Key guardada y verificada.", reply_markup=main_menu_kb())
    except Exception as e:
        await m.answer(f"⚠️ Error validando key: {e}", reply_markup=main_menu_kb())

@router.message(F.text == BTN_KEY_DEL)
async def del_key(m: Message, state: FSMContext, mongo: Mongo):
    await state.clear()
    removed = await delete_user_key(mongo, m.from_user.id)
    if removed:
        await m.answer("🗑️ API Key eliminada.", reply_markup=main_menu_kb())
    else:
        await m.answer("No tenía API Key guardada.", reply_markup=main_menu_kb())
