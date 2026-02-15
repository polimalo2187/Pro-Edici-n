from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

BTN_VIDEO = "🎬 Video"
BTN_IMAGE = "🖼️ Imagen"
BTN_EDIT  = "🧩 Editar imágenes"
BTN_KEY_SET = "🔑 Conectar API Key"
BTN_KEY_DEL = "🗑️ Desconectar API Key"
BTN_MENU  = "🏠 Menú"

BTN_DONE  = "✅ Listo"
BTN_HD    = "✨ HD"

def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_VIDEO), KeyboardButton(text=BTN_IMAGE)],
            [KeyboardButton(text=BTN_EDIT)],
            [KeyboardButton(text=BTN_KEY_SET), KeyboardButton(text=BTN_KEY_DEL)],
            [KeyboardButton(text=BTN_MENU)],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Toca un botón…",
    )

def edit_mode_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_DONE), KeyboardButton(text=BTN_HD)],
            [KeyboardButton(text=BTN_MENU)],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Envía fotos o toca Listo…",
    )

def gen_mode_kb() -> ReplyKeyboardMarkup:
    # para Imagen/Video: HD + Menú (HD solo afecta Imagen)
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_HD)],
            [KeyboardButton(text=BTN_MENU)],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Envía tu prompt…",
    )
