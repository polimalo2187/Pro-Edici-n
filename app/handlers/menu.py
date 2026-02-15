from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from app.ui.keyboards import main_menu_kb, BTN_MENU

router = Router()

WELCOME = (
    "🤖 *Gemini Media Bot*\n\n"
    "Botones:\n"
    "• 🎬 Video\n"
    "• 🖼️ Imagen\n"
    "• 🧩 Editar imágenes (2 fotos -> montaje realista)\n"
    "• 🔑 Conectar API Key\n"
    "• 🗑️ Desconectar API Key\n\n"
    "Primero conecta tu API Key 🔑 y luego usa los modos.\n"
)

@router.message(F.text.in_({"/start", "/help"}))
async def start(m: Message, state: FSMContext):
    await state.clear()
    await m.answer(WELCOME, reply_markup=main_menu_kb(), parse_mode="Markdown")

@router.message(F.text == BTN_MENU)
async def menu(m: Message, state: FSMContext):
    await state.clear()
    await m.answer("🏠 Menú", reply_markup=main_menu_kb())
