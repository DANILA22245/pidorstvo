import telebot
import random
import os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import json

user_states = {}  # хранит текущий шаг квеста для каждого пользователя
kvest_data = {}  # структура квеста качалочки
user_selected_ryazanka = {}
user_passed_paths = {}
user_gay_sex_count = {}  # chat_id -> int
user_nataha_sex_count = {}
last_ne_ponyal = {}  # chat_id -> индекс или текст последней фразы

# === СОСТОЯНИЕ ДЛЯ ТИНДЕР-КВЕСТА ===
TINDER_FOLDER = r"C:\MyPythonProjects\Илюха бот\tinder"
TINDER_STORIES_PATH = r"C:\MyPythonProjects\Илюха бот\TinderStories.json"
TINDER_CHARACTERS_PATH = r"C:\MyPythonProjects\Илюха бот\TinderCharacters.json"

# chat_id -> текущий файл-картинка при свайпе
tinder_current_photo = {}
# chat_id -> список файлов, отложенных на потом
tinder_later = {}
# chat_id -> индекс текущего элемента в tinder_later при просмотре мэтчей
tinder_later_index = {}
# chat_id -> состояние сюжета с персонажем
# {
#   "character_id": str,
#   "liked": int,
#   "disliked": int,
#   "turns": int,
# }
tinder_story_state = {}

# конфиг сюжета: загружается из JSON, где ключ - имя файла картинки
# {
#   "870908908089980.jpg": {"character_id": "anna", "has_story": true},
#   ...
# }
tinder_story_config = {}

# описание персонажей тиндера: грузим из отдельного JSON
# структура в файле:
# {
#   "anna": {
#     "name": "...",
#     "intro": "...",
#     "max_turns": 5,
#     "buttons": {
#       "kind": {"text": "...", "liked": true, "replies": ["...", "..."]},
#       ...
#     },
#     "final_good": "...",
#     "final_bad": "..."
#   },
#   ...
# }
TINDER_CHARACTERS = {}


# Токен бота
TOKEN = "8340860006:AAGO0-atj7zQNimUm0HWdnP1UyA_Vv7c_DA"

# Создаем бота
bot = telebot.TeleBot(TOKEN)


with open(
    r"C:\MyPythonProjects\Илюха бот\Kvest\Kvest.json", "r", encoding="utf-8"
) as f:
    kvest_data = json.load(f)

# Загружаем конфиг тиндер-сюжетов
try:
    with open(TINDER_STORIES_PATH, "r", encoding="utf-8") as f:
        tinder_story_config = json.load(f)
except FileNotFoundError:
    tinder_story_config = {}
except Exception as e:
    print(f"Ошибка загрузки TinderStories.json: {e}")
    tinder_story_config = {}

# Загружаем описание персонажей тиндера
try:
    with open(TINDER_CHARACTERS_PATH, "r", encoding="utf-8") as f:
        TINDER_CHARACTERS = json.load(f)
except FileNotFoundError:
    TINDER_CHARACTERS = {}
except Exception as e:
    print(f"Ошибка загрузки TinderCharacters.json: {e}")
    TINDER_CHARACTERS = {}


# === ЗАПУСК МИНИ-ИГРЫ ПО СЛОВУ "МАК" ===

# 🔗 ЗАМЕНИТЕ НА ВАШУ РЕАЛЬНУЮ ССЫЛКУ С GITHUB PAGES!
GAME_URL = "https://danila22245.github.io/yourname.github.io-sergey-game/"


def get_random_tinder_photo():
    """Возвращает случайный файл-картинку из папки тиндер или None."""
    if not os.path.isdir(TINDER_FOLDER):
        return None
    files = [
        f
        for f in os.listdir(TINDER_FOLDER)
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))
    ]
    if not files:
        return None
    return random.choice(files)


def send_tinder_swipe_photo(chat_id, delete_message=None):
    """
    Отправляет пользователю фото для свайпа с кнопками 'Заебись' и 'Хуйня'.
    Если delete_message передан, пытается удалить предыдущее сообщение с фото.
    """
    if delete_message is not None:
        try:
            bot.delete_message(chat_id, delete_message.message_id)
        except Exception:
            pass

    filename = get_random_tinder_photo()
    if not filename:
        bot.send_message(chat_id, "Не нашёл ни одной фотки в тиндер-папке, кореш.")
        return

    tinder_current_photo[chat_id] = filename
    full_path = os.path.join(TINDER_FOLDER, filename)

    if not os.path.exists(full_path):
        bot.send_message(chat_id, "Фотка куда-то пропала, попробуй ещё раз позже.")
        return

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("Заебись", callback_data="tinder_swipe_good"),
        InlineKeyboardButton("Хуйня", callback_data="tinder_swipe_bad"),
    )

    with open(full_path, "rb") as photo:
        bot.send_photo(
            chat_id,
            photo,
            caption="Свайпай, кореш.",
            reply_markup=markup,
        )


def send_tinder_start_menu(chat_id):
    """
    Меню перед стартом: 'Начать свайпать' / 'Просмотреть мэтчи',
    если есть отложенные мэтчи.
    """
    later_list = tinder_later.get(chat_id) or []
    if not later_list:
        # Если мэтчей нет, сразу идём в свайп
        send_tinder_swipe_photo(chat_id)
        return

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("Начать свайпать", callback_data="tinder_start_swipe"),
        InlineKeyboardButton("Просмотреть мэтчи", callback_data="tinder_view_matches"),
    )
    bot.send_message(
        chat_id,
        "У тебя уже есть сохранённые мэтчи. Что делаем?",
        reply_markup=markup,
    )


def send_tinder_later_photo(chat_id, delete_message=None):
    """
    Показывает сохранённый мэтч из списка later по порядку
    с кнопками 'Написать' и 'Следующая'.
    """
    later_list = tinder_later.get(chat_id) or []
    if not later_list:
        bot.send_message(chat_id, "У тебя пока нет отложенных мэтчей, кореш.")
        return

    if delete_message is not None:
        try:
            bot.delete_message(chat_id, delete_message.message_id)
        except Exception:
            pass

    idx = tinder_later_index.get(chat_id, 0)
    if not later_list:
        bot.send_message(chat_id, "Мэтчей нет.")
        return

    # Зацикливаемся по списку
    if idx >= len(later_list):
        idx = 0
    tinder_later_index[chat_id] = idx

    filename = later_list[idx]
    full_path = os.path.join(TINDER_FOLDER, filename)
    if not os.path.exists(full_path):
        bot.send_message(chat_id, "Эта фотка куда-то пропала, скипаем её.")
        tinder_later_index[chat_id] = (idx + 1) % len(later_list)
        return send_tinder_later_photo(chat_id)

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("Написать", callback_data="tinder_view_write"),
        InlineKeyboardButton("Следующая", callback_data="tinder_view_next"),
    )

    with open(full_path, "rb") as photo:
        bot.send_photo(
            chat_id,
            photo,
            caption="Твой сохранённый мэтч.",
            reply_markup=markup,
        )


def start_tinder_story(chat_id, filename, photo_message_id):
    """Запуск сюжета по конкретной картинке, если он есть."""
    story_info = tinder_story_config.get(filename)
    if not story_info or not story_info.get("has_story"):
        bot.send_message(chat_id, "Мэтча нету.")
        send_tinder_swipe_photo(chat_id)
        return

    character_id = story_info.get("character_id")
    character = TINDER_CHARACTERS.get(character_id)
    if not character:
        bot.send_message(chat_id, "Сюжет для этого мэтча ещё не дописан, кореш.")
        send_tinder_swipe_photo(chat_id)
        return

    state = {
        "character_id": character_id,
        "liked": 0,
        "disliked": 0,
        "turns": 0,
        "photo_message_id": photo_message_id,
    }

    if character.get("stages"):
        state.update({"mode": "tree", "stage_index": 0, "messages": []})
        tinder_story_state[chat_id] = state
        _send_tree_greeting_prompt(chat_id, character_id, character)
    else:
        state.update({"mode": "flat"})
        tinder_story_state[chat_id] = state
        _send_flat_story_intro(chat_id, character_id, character)


def _send_tree_greeting_prompt(chat_id, character_id, character):
    """Показывает выбор приветствия для веточного сценария."""
    greetings = character.get("greetings") or {}
    if not greetings:
        bot.send_message(chat_id, "Этот персонаж пока в ступоре, попробуй другого.")
        tinder_story_state.pop(chat_id, None)
        send_tinder_swipe_photo(chat_id)
        return

    markup = InlineKeyboardMarkup()
    for key, cfg in greetings.items():
        # Формат callback_data: "tstart_<character_id>|<greeting_key>"
        markup.add(
            InlineKeyboardButton(
                cfg["text"],
                callback_data=f"tstart_{character_id}|{key}",
            )
        )

    msg = bot.send_message(
        chat_id,
        "Что напишешь?",
        reply_markup=markup,
    )

    state = tinder_story_state.get(chat_id)
    if state:
        state["messages"] = [msg.message_id]
        tinder_story_state[chat_id] = state


def _send_flat_story_intro(chat_id, character_id, character):
    """Начинает простой сценарий (старый формат)."""
    buttons = character.get("buttons") or {}
    if not buttons:
        bot.send_message(chat_id, "Этот персонаж пока молчит. Попробуй позже.")
        tinder_story_state.pop(chat_id, None)
        send_tinder_swipe_photo(chat_id)
        return

    intro_text = character.get("intro", "Ну что, поговорим?")
    markup = InlineKeyboardMarkup()
    for key, cfg in buttons.items():
        # Формат callback_data: "tstory_<character_id>|<answer_key>"
        markup.add(
            InlineKeyboardButton(
                cfg["text"],
                callback_data=f"tstory_{character_id}|{key}",
            )
        )

    bot.send_message(chat_id, intro_text, reply_markup=markup)


def _send_tree_stage_message(chat_id, character_id, stage_index, reply_text):
    """Отправляет ответ персонажа и следующую клавиатуру."""
    state = tinder_story_state.get(chat_id)
    if not state:
        return

    character = TINDER_CHARACTERS.get(character_id)
    stages = (character or {}).get("stages") or []

    if stage_index >= len(stages):
        msg = bot.send_message(chat_id, reply_text)
        state["messages"] = [msg.message_id]
        tinder_story_state[chat_id] = state
        return

    stage_options = stages[stage_index].get("options", {})
    if not stage_options:
        msg = bot.send_message(chat_id, reply_text)
        state["messages"] = [msg.message_id]
        tinder_story_state[chat_id] = state
        return

    markup = InlineKeyboardMarkup()
    for key, cfg in stage_options.items():
        # Формат callback_data: "tstory_<character_id>|<stage_index>|<option_key>"
        markup.add(
            InlineKeyboardButton(
                cfg["text"],
                callback_data=f"tstory_{character_id}|{stage_index}|{key}",
            )
        )

    msg = bot.send_message(chat_id, reply_text, reply_markup=markup)
    state["messages"] = [msg.message_id]
    tinder_story_state[chat_id] = state


def _clear_tinder_dialog_messages(chat_id):
    """Удаляет все сообщения диалога после фотографии персонажа."""
    state = tinder_story_state.get(chat_id)
    if not state:
        return
    msg_ids = state.get("messages") or []
    for mid in msg_ids:
        try:
            bot.delete_message(chat_id, mid)
        except Exception:
            pass
    state["messages"] = []
    tinder_story_state[chat_id] = state


def handle_tinder_story_answer(call):
    """Обработка ответов в сюжете."""
    chat_id = call.message.chat.id
    data = call.data

    # Ожидаемые форматы:
    #  - "tstart_<character_id>|<greeting_key>"
    #  - "tstory_<character_id>|<answer_key>"
    #  - "tstory_<character_id>|<stage_index>|<option_key>"
    try:
        prefix, payload = data.split("_", 1)
    except ValueError:
        return

    payload_parts = payload.split("|")
    if not payload_parts:
        return

    character_id = payload_parts[0]
    remainder_parts = payload_parts[1:]
    remainder = "|".join(remainder_parts) if remainder_parts else ""

    state = tinder_story_state.get(chat_id)
    if not state or state.get("character_id") != character_id:
        return

    character = TINDER_CHARACTERS.get(character_id)
    if not character:
        return

    mode = state.get("mode", "flat")

    if prefix == "tstart":
        if mode != "tree":
            return
        if not remainder_parts:
            return
        greeting_key = remainder_parts[0]
        _handle_tree_greeting(call, state, character_id, character, greeting_key)
        return

    if prefix == "tstory":
        if mode == "tree":
            if len(remainder_parts) < 2:
                return
            stage_part = remainder_parts[0]
            option_key = remainder_parts[1]
            try:
                stage_index = int(stage_part)
            except ValueError:
                return
            _handle_tree_stage(
                call, state, character_id, character, stage_index, option_key
            )
        else:
            if not remainder_parts:
                return
            answer_key = remainder_parts[0]
            _handle_flat_story_turn(call, state, character_id, character, answer_key)


def _handle_tree_greeting(call, state, character_id, character, greeting_key):
    chat_id = call.message.chat.id
    greetings = character.get("greetings") or {}
    gcfg = greetings.get(greeting_key)
    if not gcfg:
        return

    if gcfg.get("liked"):
        state["liked"] += 1
    else:
        state["disliked"] += 1
    state["turns"] += 1
    tinder_story_state[chat_id] = state

    _clear_tinder_dialog_messages(chat_id)

    reply_text = random.choice(gcfg.get("replies", ["..."]))
    _send_tree_stage_message(
        chat_id, character_id, state.get("stage_index", 0), reply_text
    )


def _handle_tree_stage(call, state, character_id, character, stage_index, option_key):
    chat_id = call.message.chat.id
    current_stage = state.get("stage_index", 0)
    stages = character.get("stages") or []

    if stage_index != current_stage or stage_index >= len(stages):
        return

    stage_options = stages[stage_index].get("options", {})
    option_cfg = stage_options.get(option_key)
    if not option_cfg:
        return

    if option_cfg.get("liked"):
        state["liked"] += 1
    else:
        state["disliked"] += 1
    state["turns"] += 1
    state["stage_index"] = current_stage + 1
    tinder_story_state[chat_id] = state

    _clear_tinder_dialog_messages(chat_id)

    reply_text = option_cfg.get("reply", "...")
    max_turns = character.get("max_turns", 10)

    if state["turns"] >= max_turns:
        final_text = (
            character["final_good"]
            if state["liked"] > state["disliked"]
            else character["final_bad"]
        )
        bot.send_message(chat_id, reply_text)
        bot.send_message(chat_id, final_text)
        tinder_story_state.pop(chat_id, None)

        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("Начать свайпать", callback_data="tinder_start_swipe"),
            InlineKeyboardButton(
                "Просмотреть мэтчи", callback_data="tinder_view_matches"
            ),
        )
        bot.send_message(chat_id, "Что делаем дальше, кореш?", reply_markup=markup)
    else:
        _send_tree_stage_message(
            chat_id, character_id, state["stage_index"], reply_text
        )


def _handle_flat_story_turn(call, state, character_id, character, answer_key):
    chat_id = call.message.chat.id
    buttons = character.get("buttons") or {}
    btn_cfg = buttons.get(answer_key)
    if not btn_cfg:
        return

    if btn_cfg.get("liked"):
        state["liked"] += 1
    else:
        state["disliked"] += 1
    state["turns"] += 1
    tinder_story_state[chat_id] = state

    reply_text = random.choice(btn_cfg.get("replies", ["..."]))

    max_turns = character.get("max_turns", 5)
    if state["turns"] >= max_turns:
        final_text = (
            character["final_good"]
            if state["liked"] > state["disliked"]
            else character["final_bad"]
        )
        bot.send_message(chat_id, reply_text)
        bot.send_message(chat_id, final_text)
        tinder_story_state.pop(chat_id, None)

        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("Начать свайпать", callback_data="tinder_start_swipe"),
            InlineKeyboardButton(
                "Просмотреть мэтчи", callback_data="tinder_view_matches"
            ),
        )
        bot.send_message(chat_id, "Что делаем дальше, кореш?", reply_markup=markup)
    else:
        markup = InlineKeyboardMarkup()
        for key, cfg in buttons.items():
            markup.add(
                InlineKeyboardButton(
                    cfg["text"], callback_data=f"tstory_{character_id}|{key}"
                )
            )
        bot.send_message(chat_id, reply_text, reply_markup=markup)


def handle_tinder_callback(call):
    """Роутинг всех callback'ов, связанных с тиндер-квестом."""
    chat_id = call.message.chat.id
    data = call.data

    if data == "tinder_start_swipe":
        send_tinder_swipe_photo(chat_id, delete_message=call.message)
        return

    if data == "tinder_view_matches":
        send_tinder_later_photo(chat_id, delete_message=call.message)
        return

    if data == "tinder_swipe_bad":
        # Хуйня — удаляем старую фотку и шлём новую
        send_tinder_swipe_photo(chat_id, delete_message=call.message)
        return

    if data == "tinder_swipe_good":
        # Заебись — проверяем, есть ли связанный сюжет
        filename = tinder_current_photo.get(chat_id)
        try:
            bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=None,
            )
        except Exception:
            pass

        if not filename:
            bot.send_message(
                chat_id, "Что-то пошло не так с этой фоткой, попробуем другую."
            )
            send_tinder_swipe_photo(chat_id)
            return

        story_info = tinder_story_config.get(filename)
        if not story_info or not story_info.get("has_story"):
            # фото убирается из переписки
            try:
                bot.delete_message(chat_id, call.message.message_id)
            except Exception:
                pass
            bot.send_message(chat_id, "Мэтча нету.")
            send_tinder_swipe_photo(chat_id)
            return

        # есть сюжет — поздравляем, показываем кнопки
        bot.send_message(
            chat_id,
            "Поздравляю! У вас мэтч! 💞💞💞💞💞💞💞💞💞💞💞💞💞💞💞💞💞💞💞💞💞💞💞💞💞",
        )
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("Написать", callback_data="tinder_match_write"),
            InlineKeyboardButton("Позже", callback_data="tinder_match_later"),
        )
        try:
            bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=markup,
            )
        except Exception:
            pass
        return

    if data == "tinder_match_later":
        # добавляем текущую картинку в список later
        filename = tinder_current_photo.get(chat_id)
        if filename:
            later_list = tinder_later.setdefault(chat_id, [])
            if filename not in later_list:
                later_list.append(filename)
        try:
            bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=None,
            )
        except Exception:
            pass
        bot.send_message(chat_id, "Ок, отложили этого персонажа на потом.")
        # продолжаем свайп
        send_tinder_swipe_photo(chat_id)
        return

    if data == "tinder_match_write":
        filename = tinder_current_photo.get(chat_id)
        if not filename:
            bot.send_message(chat_id, "Не могу найти этот мэтч, попробуй ещё раз.")
            send_tinder_swipe_photo(chat_id)
            return
        # картинка остаётся, просто запускаем сюжет
        start_tinder_story(chat_id, filename, photo_message_id=call.message.message_id)
        return

    if data == "tinder_view_next":
        # следующая сохранённая фотка
        later_list = tinder_later.get(chat_id) or []
        if not later_list:
            bot.send_message(chat_id, "У тебя больше нет сохранённых мэтчей.")
            try:
                bot.delete_message(chat_id, call.message.message_id)
            except Exception:
                pass
            return
        idx = tinder_later_index.get(chat_id, 0)
        idx = (idx + 1) % len(later_list)
        tinder_later_index[chat_id] = idx
        send_tinder_later_photo(chat_id, delete_message=call.message)
        return

    if data == "tinder_view_write":
        # начинаем сюжет по текущему элементу из later
        later_list = tinder_later.get(chat_id) or []
        if not later_list:
            bot.send_message(chat_id, "Мэтчей нет.")
            return
        idx = tinder_later_index.get(chat_id, 0)
        if idx >= len(later_list):
            idx = 0
            tinder_later_index[chat_id] = idx
        filename = later_list[idx]
        start_tinder_story(chat_id, filename, photo_message_id=call.message.message_id)
        return


@bot.message_handler(
    func=lambda message: message.text and "мак" in message.text.lower()
)
def launch_game(message):
    markup = InlineKeyboardMarkup()
    web_app = WebAppInfo(url=GAME_URL)
    button = InlineKeyboardButton(text="▶️ Я сегодня занят, дел много", web_app=web_app)
    markup.add(button)
    bot.send_message(message.chat.id, "На семенный ужин! 🏃‍♂️", reply_markup=markup)


def noer(chat_id):
    try:
        # Текстовые ответы на слово "Ноер"
        noer_texts = [
            "Hey, Grachev, where is my money?",
            "Aaaaaa, Danila mashina",
            "Feruz blyat",
            "Send me one thousand rubles",
            "Diiiiin",
            "sinii dogonyat myach",
            "zelyonii manishki",
            "Ha, Grachev, kostym сosts 15000 rubles",
            "Grachev, where is my money? you stupid piece of snezhock",
            "niggas play good",
            "feruz drink vodka",
            "i am russkii",
            "who is seryoga?",
            "gawucho blyat",
            "Vibranium silah!",
            "David sucks my dick",
            "Ha? Grachev didn't pay for training",
            "pay me 1000 rubles or suck my dick",
            "you wanna suck my dick? No? if no? pay me 1000 rubles",
            "if you wanna train, pay me 1000 rubles",
            "pochemu ti ne skinul mne dengi?",
            "give me your money, white pidor",
            "my cock is 54 santimetra. wanna see? pay me 1000 rubles",
        ]
        # Путь к папке с медиа
        noer_media = r"C:\MyPythonProjects\Илюха бот\Neuer"

        # Поддерживаемые форматы
        image_noer = [
            f
            for f in os.listdir(noer_media)
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))
        ]
        video_noer = [
            f
            for f in os.listdir(noer_media)
            if f.lower().endswith((".mp4", ".avi", ".mov", ".mkv"))
        ]
        all_noer = image_noer + video_noer

        # Решаем: что отправить — медиа или текст (10% на 90%)
        if all_noer and random.random() < 0.1:  # 10% — медиа, 90% — текст
            chosen_file = random.choice(all_noer)
            file_path = os.path.join(noer_media, chosen_file)
            with open(file_path, "rb") as media_file:
                special_noer = {
                    "5337260966188021789.jpg": "there is VIBRANIUM MAZA FAKA! send me 1000 rubles for photo, blyat",
                    "5337260966188021788.jpg": "there is nigga with big ass, named Din",
                    "5337260966188021786.jpg": "1000 ruuuuuubleeeees",
                    "5337260966188021787.jpg": "one of my niggas, that pay me 1000 rubles",
                    "IMG_1459.mp4": "hey, din, wake up",
                }

                # Получаем подпись, если файл в словаре
                caption = special_noer.get(chosen_file.lower())

                if chosen_file.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
                    bot.send_video(chat_id, media_file, caption=caption)
                else:
                    bot.send_photo(chat_id, media_file, caption=caption)
        else:
            # Отправляем просто текст
            response = random.choice(noer_texts)
            bot.send_message(chat_id, response)
    except Exception as e:
        print(f"Ошибка при отправке ответа про Серегу: {e}")
        # Если всё сломалось — хотя бы текст
        bot.send_message(chat_id, "Серега... это долгая история, кореш.")


def pidora_otvet(chat_id):
    try:
        # Текстовые ответы на слово "Нет"
        pidors_texts = [
            "Пидора ответ",
            "Не меня ответ",
            "Поляка ответ",
            "Сделай мне минет(я представлю что ты баба, я же не пидр)",
            "петушары ответ",
            "педика ответ",
            "пошел нахуй педик",
        ]
        # Путь к папке с медиа
        pidor_media = r"C:\MyPythonProjects\Илюха бот\Pidora_otvet"

        # Поддерживаемые форматы
        image_pidor = [
            f
            for f in os.listdir(pidor_media)
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))
        ]

        # Решаем: что отправить — медиа или текст (30% на 70%)
        if image_pidor and random.random() < 0.3:  # 30% — медиа, 70% — текст
            chosen_file = random.choice(image_pidor)
            file_path = os.path.join(pidor_media, chosen_file)
            with open(file_path, "rb") as photo:
                bot.send_photo(chat_id, photo)
        else:
            # Отправляем просто текст
            response = random.choice(pidors_texts)
            bot.send_message(chat_id, response)
    except Exception as e:
        print(f"Ошибка при отправке ответа про Серегу: {e}")
        # Если всё сломалось — хотя бы текст
        bot.send_message(chat_id, "Серега... это долгая история, кореш.")


def send_seryoga_response(chat_id):
    try:
        # Текстовые ответы про Серегу (Илюха базарит)
        seryoga_texts = [
            "Серега мой кореш",
            "Серега петушара",
            "Чепурных залутал самку",
            "Серго — не человек, это легенда",
            "Говорят, Серега — натурал. А я говорю, что я - натурал",
            "Серега не пидор... он просто особенный.",
            "Серега заебал мыться час",
            "Бля, Серега заебал сливаться",
            "У него сегодня семенный ужин",
            "Не, пацаны, я сегодня занят",
            "пошел контент",
            "хахвхахаыхывахы бля",
            "залутанный кореш",
            "уууу пиздабол местный",
            "люблю кореша",
            "бляяя серго петушара",
            "авыхвыхавыхвых смотри на этого додика",
            "Серега опять слился, когда я его в зал позвал",
            "сливной петушара серега",
        ]
        special_texts_with_cringe = {
            "пошел контент",
            "хахвхахаыхывахы бля",
            "залутанный кореш",
            "уууу пиздабол местный",
            "люблю кореша",
            "бляяя серго петушара",
            "авыхвыхавыхвых смотри на этого додика",
        }

        # Путь к папке с медиа
        media_seryoga = r"C:\MyPythonProjects\Илюха бот\Seryoga"
        cringe_seryoga = r"C:\MyPythonProjects\Илюха бот\Seryoga\Sergo_cringe"

        # Поддерживаемые форматы
        image_seryoga = [
            f
            for f in os.listdir(media_seryoga)
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))
        ]
        video_seryoga = [
            f
            for f in os.listdir(media_seryoga)
            if f.lower().endswith((".mp4", ".avi", ".mov", ".mkv"))
        ]
        all_seryoga = image_seryoga + video_seryoga

        # Решаем: что отправить — медиа или текст (40% на 60%)
        if all_seryoga and random.random() < 0.4:  # 40% — медиа, 60% — текст
            chosen_file = random.choice(all_seryoga)
            file_path = os.path.join(media_seryoga, chosen_file)

            with open(file_path, "rb") as media:
                if chosen_file.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
                    bot.send_video(chat_id, media)
                else:
                    bot.send_photo(chat_id, media)
        else:
            # Отправляем просто текст
            response = random.choice(seryoga_texts)
            bot.send_message(chat_id, response)
            # Если выбран особый текст — добавить рандомное медиа из cringe-папки
            if response in special_texts_with_cringe:
                cringe_files = [
                    f
                    for f in os.listdir(cringe_seryoga)
                    if f.lower().endswith(
                        (
                            ".png",
                            ".jpg",
                            ".jpeg",
                            ".gif",
                            ".webp",
                            ".mp4",
                            ".avi",
                            ".mov",
                            ".mkv",
                        )
                    )
                ]

                if cringe_files:
                    cringe_file = random.choice(cringe_files)
                    cringe_path = os.path.join(cringe_seryoga, cringe_file)

                    with open(cringe_path, "rb") as media:
                        if cringe_file.lower().endswith(
                            (".mp4", ".avi", ".mov", ".mkv")
                        ):
                            bot.send_video(chat_id, media)
                        else:
                            bot.send_photo(chat_id, media)

    except Exception as e:
        print(f"Ошибка при отправке ответа про Серегу: {e}")
        # Если всё сломалось — хотя бы текст
        bot.send_message(chat_id, "Серега... это долгая история, кореш.")


def mems_wegym(chat_id):
    try:
        mem_wegymm = r"C:\MyPythonProjects\Илюха бот\mems_meeem"
        mems_meeeem = [
            f
            for f in os.listdir(mem_wegymm)
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))
        ]
        if mems_meeeem:
            image_path = os.path.join(mem_wegymm, random.choice(mems_meeeem))
            with open(image_path, "rb") as photo:
                bot.send_photo(chat_id, photo)
    except Exception as e:
        print(f"Ошибка при отправке фото из Telo_kachka: {e}")


def send_telo_photo(chat_id):
    try:
        image_folder = r"C:\MyPythonProjects\Илюха бот\Telo_kachka"
        images = [
            f
            for f in os.listdir(image_folder)
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))
        ]
        if images:
            image_path = os.path.join(image_folder, random.choice(images))
            with open(image_path, "rb") as photo:
                bot.send_photo(chat_id, photo)
    except Exception as e:
        print(f"Ошибка при отправке фото из Telo_kachka: {e}")


def send_fuck_off_image(message):
    try:
        # Указываем полный путь к папке
        image_folder = r"C:\MyPythonProjects\Илюха бот\Nahui"

        # Получаем список файлов в папке
        images = [
            f
            for f in os.listdir(image_folder)
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))
        ]

        # Если есть картинки — выбираем случайную и отправляем
        if images:
            image_path = os.path.join(image_folder, random.choice(images))
            with open(image_path, "rb") as photo:
                bot.send_photo(message.chat.id, photo)  # без подписи — только фото
    except Exception as e:
        print(f"Ошибка при отправке фото 'иди нахуй': {e}")
        # Ничего не отправляем дальше — молчим, как Илюха после зала


# Ответы Илюхи на "залутал"
zalutal = [
    "залутал залутал залутал залутал залутал залутал залутал залутал залутал залутал залутал залутал залутал залутал залутал залутал залутал залутал залутал залутал",
    "залутал кореша",
    "уууу залутал кореша",
    "никого я не залутал сегодня",
    "коооореш",
    "залууууутааааааал",
    "ну кореш...",
    "жвшжшвшвжвжвжш",
    "когда уже серега самку залутает... кореш",
    "уууу педик, опять меня троллит",
    "хватит меня подъебывать",
    "думаешь это смешно, педик?",
    "хваыхахавыхваых иди нахуй",
    "кореш, угомонись",
    'скажи "нет"',
    "пошли в зал, хорош хуйней страдать",
    "короче ты меня заебал кореш",
    "уууу залутал Натаху",
    "мои кореша лутают корешей, понял, кореш? залутал залутал залутал залутал залутал залутал залутал залутал залутал залутал залутал залутал",
]


# Ответы Илюхи на приветствие
privet = [
    "ну здарова, петушара",
    "здарова, кореш",
    "привет, педик",
    "как жизнь, педик?",
    "ооооооо, здарова, педик",
    "ку, че, в зал пойдешь?",
    "здарова, во скок в зал идешь?",
    "уууу, залутал кореша",
    "кооооореш",
    "овщваовов",
]

# Ответы Илюхи на слово пидор
ilyha = [
    "я не пидор",
    "пидоры тоже люди, но я не пидор, поэтому я не человек",
    "серега пидор, а я нет",
    "да не пидор я",
    "ты пидор, а я не пидор",
    "я сейчас представлю, что ты натурал, и выебу тебя",
    "кореш на работе сказал, что я пидор, я его выебал, так что аккуратнее со словами",
    "иди нахуй",
    "не пидор я бля",
    "я тебя ща выебу, пидор",
    "я тебя ща залутаю, кореш",
    "как же ты заебал, пидор. но не меня, я натурал",
    "даже не знаю, че тебе сказать... просто, знай, что я натурал(точно)",
    "мне показалось, или ты хочешь мне пососать?",
]


# Ответы Илюхи, когда его зовут в зал
Zal = [
    "я уже иду в зал",
    "я сейчас иду в зал, зацени мое натуральное тело",
    "иду ща в зал, присоединяйся",
    "я к 21 00 иду",
    "бля, я сегодня уже не пойду, заебался качаться",
    "не, я не пойду, не чувствую нагрузку с этими весами",
    "погнали лучше в баньку посмотрим на натуральные члены как натуралы",
    "деды заебали в сауне подливать",
    "видел, как дед вчера яйца сушил феном? у меня еще тогда встал, ну это я вспомнил про Наташу просто",
    "погнали педик через 30 мин(посрать надо)",
]
# Ответы Илюхи, когда он не понял, че ему написали
Ne_ponyal = [
    "Нихуя не понял",
    "Хочешь пройти квест? Если да, напиши 'WeGym'",
    "че?",
    "Напиши 'мак', если хочешь войти в режим ебанутого берсерка",
    "поляк еще не научил меня на такую хуйню отвечать",
    'Если хочешь, чтобы я тебе рассказал, о чем я люблю базарить напиши "валына"',
    'Хочешь найти бабу - напиши "тиндер"',
]

RYAZANKA_OPTIONS = {
    "Подойти к Новикову": "novikov",
    "Подойти к Урюпину": "urupin",
    "Подойти к Самиру": "samir",
    "Подойти к Алишеру": "alisher",
    "Подойти к Родиону": "rodion2",
    "Пойти домой": "rodion1488",
}


# Обработчик команды /start
@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(
        message,
        "Я - Илюха и я - самый натуральный натурал\nЗадавай любой вопрос. Ответ будет честным — потому что врут только пидоры.",
    )


# Обработчик команды /stop
@bot.message_handler(commands=["stop"])
def stop(message):
    bot.reply_to(message, "💪 Брат, ты молодец. Теперь иди в зал. Пока!")


# Квест качалочки
@bot.message_handler(func=lambda message: message.text.lower() == "wegym")
def start_kvest(message):
    chat_id = message.chat.id
    user_states.pop(chat_id, None)
    user_passed_paths.pop(chat_id, None)
    user_states[chat_id] = "intro"  # начинаем с блока "интро"
    send_kvest_step(chat_id, "intro")


def send_kvest_step(chat_id, step_key):
    global user_gay_sex_count, kvest_data, user_nataha_sex_count
    step = kvest_data.get(step_key)

    if not step:
        bot.send_message(chat_id, "Ошибка: шаг квеста не найден.")
        return

    # Подсчёт гейского секса
    if step.get("is_gay_sex", False):
        user_gay_sex_count[chat_id] = user_gay_sex_count.get(chat_id, 0) + 1
    if step.get("is_nataha_sex", False):
        user_nataha_sex_count[chat_id] = user_nataha_sex_count.get(chat_id, 0) + 1

    text = step.get("text", "")
    options = step.get("options", {})

    # Фильтрация для ryazanka
    if step_key == "ryazanka":
        passed = user_passed_paths.get(chat_id, [])
        filtered_options = {
            label: nxt for label, nxt in options.items() if label not in passed
        }
    else:
        filtered_options = options

    # Медиа
    image_path = step.get("image")
    video_path = step.get("video")

    # Клавиатура
    markup = None
    if filtered_options:
        markup = InlineKeyboardMarkup()
        for label, next_step in filtered_options.items():
            markup.add(InlineKeyboardButton(label, callback_data=next_step))

    # Отправка контента
    sent = False
    if image_path and os.path.exists(image_path):
        with open(image_path, "rb") as photo:
            bot.send_photo(chat_id, photo, caption=text, reply_markup=markup)
        sent = True
    elif video_path and os.path.exists(video_path):
        with open(video_path, "rb") as video:
            bot.send_video(chat_id, video, caption=text, reply_markup=markup)
        sent = True

    if not sent:
        bot.send_message(chat_id, text, reply_markup=markup)

    # 🔚 ФИНАЛ: нет вариантов ответа
    if not filtered_options:
        total_gay = user_gay_sex_count.get(chat_id, 0)
        nataha_sex = user_nataha_sex_count.get(chat_id, 0)

        if total_gay == 0 and nataha_sex >= 1:
            # ✅ Правильный финал
            final_text = "Браво, ты потрахался с женщиной! Только один секс за день и он - натуральный!"
            bot.send_message(chat_id, final_text)

            secret_video = r"C:\MyPythonProjects\Илюха бот\Kvest\photos\IMG_5582.MOV"
            if os.path.exists(secret_video):
                with open(secret_video, "rb") as vid:
                    bot.send_video(
                        chat_id,
                        vid,
                        caption="Поздравляю! ты это сделал! Теперь ты понял, как сложно быть меганатуральным качком?",
                    )

            # Сброс всего
            user_states.pop(chat_id, None)
            user_passed_paths.pop(chat_id, None)
            user_gay_sex_count.pop(chat_id, None)
            user_nataha_sex_count.pop(chat_id, None)

        else:
            # ❌ Неправильный финал
            if nataha_sex >= 1:
                # Был секс с Натахой, но и гей-секс тоже
                if total_gay == 1:
                    summary = "Ты занялся любовью со своей избранницей! Браво! Но... есть маленький нюанс... У тебя была еще одна ебля с мужиком... Так что, попробуй еще раз, педик."
                elif total_gay <= 4:
                    summary = f"Ты занялся любовью со своей избранницей! Браво! Но... есть маленький нюанс... Ты поебался еще {total_gay} раза с мужиками... Так что, попробуй еще раз, педик."
                else:
                    summary = f"Ты занялся любовью со своей избранницей! Браво! Но... есть маленький нюанс... Ты поебался {total_gay} раз с мужиками... Так что, попробуй еще раз, педик."
            else:
                # Не было секса с Натахой
                if total_gay == 1:
                    summary = "\n\nОдин раз — не пидорас. Только один секс, но он — не с женщиной. Попробуй ещё раз."
                elif total_gay <= 4:
                    summary = f"\n\nТы поебался {total_gay} раза не с женщиной..."
                else:
                    summary = f"\n\nТы собрал {total_gay} гейских сексов за день. Попробуй еще раз, педик."

            bot.send_message(chat_id, summary)

            # Кнопка перезапуска
            restart_markup = InlineKeyboardMarkup()
            restart_markup.add(
                InlineKeyboardButton("🔄 Следующий день", callback_data="restart_kvest")
            )
            bot.send_message(chat_id, "(the not_blue end)", reply_markup=restart_markup)

            # Состояние НЕ сбрасываем — только при нажатии кнопки


@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    data = call.data

    # Сначала обрабатываем все тиндер-callback'и
    if (
        data.startswith("tinder_")
        or data.startswith("tstory_")
        or data.startswith("tstart_")
    ):
        if data.startswith("tinder_"):
            handle_tinder_callback(call)
        else:
            handle_tinder_story_answer(call)
        return

    next_step = data

    current_step = user_states.get(chat_id)

    # Если пользователь сейчас в шаге ryazanka — записываем выбранный вариант
    if current_step == "ryazanka":
        ryazanka_options = kvest_data.get("ryazanka", {}).get("options", {})
        chosen_label = None
        for label, step_val in ryazanka_options.items():
            if step_val == next_step:
                chosen_label = label
                break
        if chosen_label:
            passed = user_passed_paths.setdefault(chat_id, [])
            if chosen_label not in passed:
                passed.append(chosen_label)
    elif next_step == "restart_kvest":
        user_states.pop(chat_id, None)
        user_passed_paths.pop(chat_id, None)
        user_gay_sex_count.pop(chat_id, None)
        user_nataha_sex_count.pop(chat_id, None)
        try:
            bot.edit_message_reply_markup(
                chat_id=chat_id, message_id=call.message.message_id, reply_markup=None
            )
        except:
            pass
        send_kvest_step(chat_id, "intro")
        return
    try:
        bot.edit_message_reply_markup(
            chat_id=chat_id, message_id=call.message.message_id, reply_markup=None
        )
    except:
        pass

    send_kvest_step(chat_id, next_step)


# Обработчик всех текстовых сообщений
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    question = message.text.strip().lower()

    # Проверка на пустой ввод (или только пробелы/символы)
    if not question:
        bot.reply_to(message, "Молчишь? Значит, пора на приседания!")
        return

    # Подсказка юзеру
    if any(word in question for word in ["валына"]):
        response = "Короче, больше всего в этой жизни я люблю ходить в качалку. Я 100000% натурал, так что, если ты назовешь меня пидором, получишь по ебалу, кореш. Серега конечно заебал сливаться, но я люблю кореша Серегу, много всего с ним залутали. Знаешь, кто такие Ноер, Дэвид, Грачев? Ноер всех наебал, пиздатый негр. Еще я люблю мемы, могу накидать."
        bot.reply_to(message, f"{response}")
        return

    # === ЗАПУСК ТИНДЕР-КВЕСТА ===
    if "тиндер" in question:
        chat_id = message.chat.id
        send_tinder_start_menu(chat_id)
        return

    # Проверка на слово "пзалутал"
    if any(
        word in question for word in ["залута", "лутаеш", "лутал", "лутат", "кореш"]
    ):
        response = random.choice(zalutal)
        bot.reply_to(message, f"{response}")
        return

    # Проверка на слово "пидор"
    if any(
        word in question
        for word in [
            "пидор",
            "гей",
            "педик",
            "пидо",
            "пдор",
            "гомик",
            "гей",
            "пидр",
            "пидрила",
        ]
    ):
        response = random.choice(ilyha)
        bot.reply_to(message, f"{response}")
        return

    # Проверка на посылание нахуй
    if any(
        word in question
        for word in [
            "иди нахуй",
            "пошел нахуй",
            "пшёл нахуй",
            "хуй",
            "иди",
            "пошел",
            "пшел",
            "пизду",
        ]
    ):
        send_fuck_off_image(message)
        return

    # Проверка на предложение пойти в зал
    if any(
        word in question
        for word in ["зал", "качалк", "виджим", "кач", "кочк", "трен", "жим", "жать"]
    ):
        response = random.choice(Zal)
        bot.reply_to(message, f"{response}")
        # Если выбрана конкретная фраза — отправляем фото
        if response == "я сейчас иду в зал, зацени мое натуральное тело":
            send_telo_photo(message.chat.id)
        return

    # Проверка на упоминание Сереги
    if any(
        word in question
        for word in ["серег", "серго", "чепурных", "серый", "серЁг", "сереж"]
    ):
        send_seryoga_response(message.chat.id)
        return

    if any(
        word in question.lower()
        for word in [
            "neuer",
            "noer",
            "david",
            "feruz",
            "grachev",
            "polyakov",
            "ноер",
            "нойер",
            "дэвид",
            "грачев",
            "грачёв",
            "феруз",
            "дин",
            "din",
            "money",
        ]
    ):
        noer(message.chat.id)
        return

    # Проверка на приветствие
    if any(
        word in question
        for word in ["привет", "ку", "здарова", "илюх", "здравствуй", "здорово", "прив"]
    ):
        response = random.choice(privet)
        bot.reply_to(message, f"{response}")
        return

    # Илюха кидает мем
    if any(word in question for word in ["мем", "картинк", "кинь"]):
        mems_wegym(message.chat.id)
        return

    if any(word in question for word in ["нет", "не"]):
        pidora_otvet(message.chat.id)
        return

        # Проверка на вопрос (вопросительный знак в сообщении)
    if "?" in question:
        try:
            image_folder = r"C:\MyPythonProjects\Илюха бот\Kachok_photo"
            images = [
                f
                for f in os.listdir(image_folder)
                if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))
            ]
            if images:
                image_path = os.path.join(image_folder, random.choice(images))
                with open(image_path, "rb") as photo:
                    bot.send_photo(message.chat.id, photo)
        except Exception as e:
            print(f"Ошибка при отправке фото из Kachok_photo: {e}")
        return  # завершаем обработку, чтобы не переходить к Ne_ponyal

    chat_id = message.chat.id
    last = last_ne_ponyal.get(chat_id)
    available = [r for r in Ne_ponyal if r != last] or Ne_ponyal
    response = random.choice(available)
    last_ne_ponyal[chat_id] = response
    bot.reply_to(message, response)

    # Запуск бота


if __name__ == "__main__":
    print("Бот запущен! Нажмите Ctrl+C для остановки.")
    bot.polling(none_stop=True)
