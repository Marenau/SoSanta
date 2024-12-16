import telebot
import random
import string
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from mistralai import Mistral
from database import Database as database
from config import BOT_TOKEN

bot = telebot.TeleBot(BOT_TOKEN)

# Инициализация базы данных
database.init_db()

# Словарь для хранения состояния администраторов
admin_states = {}

# Словарь для хранения состояния пользователей
user_states = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton('Создать комнату 🎅🏻', callback_data='create_room'))
    markup.add(InlineKeyboardButton('Присоединиться к комнате 🎅🏻', callback_data='join_room'))
    markup.add(InlineKeyboardButton('Мои комнаты 🎅🏻', callback_data='my_rooms'))
    bot.reply_to(message, 'Добро пожаловать в волшебный мир "Тайного Санты"! 🎄✨\nПусть этот Новый Год будет полон сюрпризов и радости! 🎅🏻🎁', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if call.data == 'create_room':
        create_room(call)
    elif call.data == 'join_room':
        join_room(call)
    elif call.data.startswith('leave_room_'):
        room_code = call.data.split('_')[-1]
        leave_room(call, room_code)
    elif call.data == 'my_rooms':
        show_my_rooms(call)
    elif call.data.startswith('show_room_info_'):
        room_code = call.data.split('_')[-1]
        show_room_info(call.message.chat.id, room_code)
    elif call.data.startswith('start_game_'):
        room_code = call.data.split('_')[-1]
        start_game(call.message.chat.id, room_code, call.from_user.id)
    elif call.data.startswith('change_wish_'):
        room_code = call.data.split('_')[-1]
        change_wish(call, room_code)
    elif call.data.startswith('throw_snowball_to_'):
        _, _, _, target_user_id, room_code = call.data.split('_')
        throw_snowball_to_user(call, int(target_user_id), room_code)
    elif call.data.startswith('throw_snowball_'):
        room_code = call.data.split('_')[-1]
        show_throw_snowball_options(call.message.chat.id, room_code)

def create_room(call):
    user_id = call.from_user.id
    user_states[user_id] = 'waiting_for_room_name'
    bot.send_message(call.message.chat.id, 'Пожалуйста, введите название комнаты: 🎅🏻')

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'waiting_for_room_name')
def save_room_name(message):
    user_id = message.from_user.id
    room_name = message.text
    user_states[user_id] = {'room_name': room_name}
    bot.send_message(message.chat.id, 'Пожалуйста, введите описание комнаты: 🎄')
    user_states[user_id]['state'] = 'waiting_for_room_description'

@bot.message_handler(func=lambda message: isinstance(user_states.get(message.from_user.id), dict) and 'room_name' in user_states[message.from_user.id] and user_states[message.from_user.id]['state'] == 'waiting_for_room_description')
def save_room_description(message):
    user_id = message.from_user.id
    room_description = message.text
    user_states[user_id]['room_description'] = room_description
    bot.send_message(message.chat.id, 'Пожалуйста, введите место и дату проведения: 📅')
    user_states[user_id]['state'] = 'waiting_for_room_location_and_date'

@bot.message_handler(func=lambda message: isinstance(user_states.get(message.from_user.id), dict) and 'room_name' in user_states[message.from_user.id] and user_states[message.from_user.id]['state'] == 'waiting_for_room_location_and_date')
def save_room_location_and_date(message):
    user_id = message.from_user.id
    room_location_and_date = message.text
    room_name = user_states[user_id]['room_name']
    room_description = user_states[user_id]['room_description']
    room_code = generate_room_code()

    # Создаем комнату
    database.create_room(room_code, room_name, room_location_and_date, room_description, user_id)

    # Добавляем создателя комнаты в комнату
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    wish = ""  # Можно добавить логику для получения желания создателя @TODO

    database.add_participant(user_id, room_code, first_name, last_name, wish)

    user_states[user_id] = None
    bot.send_message(message.chat.id, f'Комната создана! 🎉\nТеперь можно приглашать друзей и готовиться к веселью! 🎅🏻')

    # Отображаем информацию о комнате
    show_room_info(message.chat.id, room_code)

def generate_room_code():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

def join_room(call):
    user_id = call.from_user.id
    user_states[user_id] = 'waiting_for_room_code'
    bot.send_message(call.message.chat.id, 'Пожалуйста, введите код комнаты: 🔑')

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'waiting_for_room_code')
def save_room_code(message):
    user_id = message.from_user.id
    room_code = message.text
    room = database.get_room(room_code)

    if room:
        if not database.is_user_in_room(user_id, room_code):
            if room[4] == 0:  # room[4] - status
                bot.send_message(message.chat.id, '🎁 Пожалуйста, напишите ваше новогоднее пожелание (подарок, который вы хотите): 🎁')
                user_states[user_id] = {'room_code': room_code, 'state': 'waiting_for_wish'}
            else:
                bot.send_message(message.chat.id, 'Игра уже началась. Вы не можете присоединиться к этой комнате. 🎄')
                user_states[user_id] = None
        else:
            bot.send_message(message.chat.id, 'Вы уже присоединились к этой комнате. 🎅🏻')
            user_states[user_id] = None
    else:
        bot.send_message(message.chat.id, 'Комната с таким кодом не найдена. Пожалуйста, попробуйте снова. 🎄')
        user_states[user_id] = None

@bot.message_handler(func=lambda message: isinstance(user_states.get(message.from_user.id), dict) and 'room_code' in user_states[message.from_user.id] and user_states[message.from_user.id]['state'] == 'waiting_for_wish')
def save_wish(message):
    user_id = message.from_user.id
    wish = message.text
    room_code = user_states[user_id]['room_code']
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    # Проверка на отсутствие фамилии у пользователя
    user_full_name = f'{first_name} {last_name}' if last_name else first_name

    # Добавляем участника в комнату
    database.add_participant(user_id, room_code, first_name, last_name, wish)

    # Уведомляем всех участников комнаты о новом участнике
    notify_participants(room_code, f'{user_full_name} присоединился к комнате! 🎉')

    user_states[user_id] = None
    bot.send_message(message.chat.id, 'Вы успешно присоединились к комнате! 🎉\nТеперь можно готовиться к веселью! 🎅🏻')

    # Отображаем информацию о комнате
    show_room_info(message.chat.id, room_code)

def leave_room(call, room_code):
    user_id = call.from_user.id
    room = database.get_room(room_code)

    if room[4] == 1:
        bot.send_message(call.message.chat.id, 'Вы не можете покинуть комнату во время игры! 🎄')
        return

    if room:
        if room[5] == user_id:  # room[5] is the owner_id
            # Уведомляем всех участников комнаты о распуске комнаты
            notify_participants(room_code, 'Комната распущена, так как владелец покинул её. 🎄')

            # Удаляем комнату и всех участников
            database.delete_room(room_code)
        else:
            # Удаляем участника из комнаты
            database.remove_participant(user_id, room_code)

            # Уведомляем всех участников комнаты о выходе участника
            user_full_name = f'{call.from_user.first_name} {call.from_user.last_name}' if call.from_user.last_name else call.from_user.first_name
            notify_participants(room_code, f'{user_full_name} покинул комнату. 🎄')

            bot.send_message(call.message.chat.id, 'Вы успешно покинули комнату. 🎄')

        user_states[user_id] = None
    else:
        bot.send_message(call.message.chat.id, 'Комната не найдена. 🎄')

def show_my_rooms(call):
    user_id = call.from_user.id
    rooms = database.get_user_rooms(user_id)

    if rooms:
        markup = InlineKeyboardMarkup()
        for room in rooms:
            room_code = room[0]
            room_name = room[1]
            button = InlineKeyboardButton(f"Комната \"{room_name}\"", callback_data=f'show_room_info_{room_code}')
            markup.add(button)

        bot.send_message(call.message.chat.id, "Вы участвуете в следующих комнатах:", reply_markup=markup)
    else:
        bot.send_message(call.message.chat.id, "Вы не участвуете ни в одной комнате. 🎄")

def start_game(chat_id, room_code, user_id):
    """
    Запускает игру, если пользователь является владельцем комнаты.

    :param chat_id: Идентификатор чата
    :param room_code: Идентификатор комнаты
    :param user_id: Идентификатор пользователя
    """
    room = database.get_room(room_code)
    if room[4] == 1:  # room[4] - status
        bot.send_message(chat_id, "Игра уже началась! 🎄")
        return

    # Устанавливаем флаг активной игры в комнате
    database.set_room_active(room_code)

    # Получаем список участников комнаты
    participants = database.get_participants(room_code)
    participant_ids = [participant[0] for participant in participants]

    # Перемешиваем список участников для случайного назначения
    random.shuffle(participant_ids)

    # Назначаем участников друг другу
    assignments = []
    for i in range(len(participant_ids)):
        giver_id = participant_ids[i]
        receiver_id = participant_ids[(i + 1) % len(participant_ids)]  # Циклическое назначение
        assignments.append((giver_id, receiver_id, room_code))

    # Сохраняем назначения в базе данных
    database.save_assignments(assignments)

    # Уведомляем участников о начале игры и их назначениях
    for giver_id, receiver_id, room_id in assignments:
        receiver = database.get_participant_by_id(receiver_id)
        receiver_full_name = f"{receiver[1]} {receiver[2]}" if receiver[2] else receiver[1]
        receiver_wish = database.get_wish(receiver_id, room_code)
        bot.send_message(giver_id, f"Мои олени выбрали для тебя классного подопечного.\nЭто __{receiver_full_name}__, правда здорово?\n😙 Однажды этот человек, сидя на моих коленях, шепнул мне на ушко, что хочет:\n__{receiver_wish}__\nНо выбор, конечно, за тобой! 🎉")

    bot.send_message(chat_id, "Игра началась!\nВсе участники уведомлены о своих подопечных. 🎉")

def change_wish(call, room_code):
    user_id = call.from_user.id
    room = database.get_room(room_code)

    if room[4] == 1:  # room[4] - status
        bot.send_message(call.message.chat.id, "Игра уже началась! 🎄")
        return
    
    user_states[user_id] = {'room_code': room_code, 'state': 'waiting_for_new_wish'}
    bot.send_message(call.message.chat.id, 'Пожалуйста, введите новое желание: 🎁')

@bot.message_handler(func=lambda message: isinstance(user_states.get(message.from_user.id), dict) and 'room_code' in user_states[message.from_user.id] and user_states[message.from_user.id]['state'] == 'waiting_for_new_wish')
def save_new_wish(message):
    user_id = message.from_user.id
    new_wish = message.text
    room_code = user_states[user_id]['room_code']

    # Обновляем желание участника в базе данных
    database.update_wish(user_id, room_code, new_wish)

    bot.send_message(message.chat.id, 'Ваше желание успешно обновлено! 🎉')
    user_states[user_id] = None

    show_room_info(user_id, room_code)

def show_room_info(chat_id, room_code):
    """
    Отображает информацию о комнате.

    :param chat_id: Идентификатор чата
    :param room_code: Идентификатор комнаты
    """
    room = database.get_room(room_code)
    if room:
        participants = database.get_participants(room_code)
        participants_list = []
        for participant in participants:
            # Проверка на отсутствие фамилии у участника
            user_full_name = f"{participant[1]} {participant[2]}" if participant[2] else participant[1]
            participants_list.append(user_full_name)
        participants_list_str = "\n".join(participants_list)

        # Получаем ваше пожелание из базы данных
        your_wish = database.get_wish(chat_id, room_code)

        # Проверяем, активна ли игра
        is_game_active = room[4] == 1  # room[4] - status

        game_status_text = "🚫 Игра не начата" if not is_game_active else "✅ Игра началась"

        room_info = (
            f"{room[1]}\n\n"
            f"{game_status_text}\n\n"
            f"Код комнаты:\n"
            f"`{room[0]}`\n\n"
            f"📆 Место и время\n"
            f"{room[2]}\n\n"
            f"🔆 Описание\n"
            f"{room[3]}\n\n"
            f"👨‍👩‍👧‍👦 Участники:\n"
            f"{participants_list_str}\n\n"
            f"🎁 Ваше пожелание:\n"
            f"{your_wish}"
        )

        if is_game_active:
            # Получаем информацию о подопечном и его желании
            assignee = database.get_assignee(chat_id, room_code)
            if assignee:
                assignee_wish = database.get_wish(assignee[0], room_code)
                user_full_name = f"{assignee[1]} {assignee[2]}" if assignee[2] else assignee[1]
                room_info += (
                    f"\n\n🎅🏻 Ваш подопечный:\n"
                    f"__{user_full_name}__\n"
                    f"🎁 Его пожелание:\n"
                    f"__{assignee_wish}__"
                )

        # Создаем кнопки
        markup = InlineKeyboardMarkup()

        # Кнопка "Начать игру" для владельца комнаты
        if room[5] == chat_id and not is_game_active:  # room[5] - owner_id
            start_game_button = InlineKeyboardButton("🎄 Начать игру 🎄", callback_data=f"start_game_{room_code}")
            markup.add(start_game_button)

        # Кнопка "Изменить желание"
        if not is_game_active:
            change_wish_button = InlineKeyboardButton("✨ Изменить желание ✨", callback_data=f"change_wish_{room_code}")
            markup.add(change_wish_button)

        # Кнопка "Кинуть снежок"
        throw_snowball_button = InlineKeyboardButton("❄️ Кинуть снежок ❄️", callback_data=f"throw_snowball_{room_code}")
        markup.add(throw_snowball_button)

        # Кнопка "Покинуть комнату"
        if not is_game_active:
            leave_room_button = InlineKeyboardButton("🚫 Покинуть комнату 🚫", callback_data=f"leave_room_{room_code}")
            markup.add(leave_room_button)

        # Отправляем сообщение с кнопками
        bot.send_message(chat_id, room_info, parse_mode='Markdown', reply_markup=markup)
    else:
        bot.send_message(chat_id, 'Комната не найдена. 🎄')

def show_throw_snowball_options(chat_id, room_code):
    """
    Отображает кнопки с участниками комнаты для выбора, в кого кинуть снежок.

    :param chat_id: Идентификатор чата
    :param room_code: Идентификатор комнаты
    """
    # Проверяем, находится ли пользователь в комнате
    user_id = chat_id
    if not database.is_user_in_room(user_id, room_code):
        bot.send_message(chat_id, 'Вы не находитесь в этой комнате. Пожалуйста, присоединитесь к комнате, чтобы кинуть снежок. ❄️')
        return

    participants = database.get_participants(room_code)

    # Проверяем, есть ли другие участники в комнате
    if len(participants) <= 1:
        bot.send_message(chat_id, 'В комнате нет других участников, в кого можно кинуть снежок. ❄️')
        return

    markup = InlineKeyboardMarkup()

    for participant in participants:
        participant_id = participant[0]
        user_full_name = f"{participant[1]} {participant[2]}" if participant[2] else participant[1]
        # Пропускаем текущего пользователя
        if participant_id != user_id:
            button = InlineKeyboardButton(user_full_name, callback_data=f"throw_snowball_to_{participant_id}_{room_code}")
            markup.add(button)

    bot.send_message(chat_id, "Выберите участника, в кого кинуть снежок:", reply_markup=markup)

def throw_snowball_to_user(call, target_user_id, room_code):
    """
    Обрабатывает действие "Кинуть снежок" в выбранного участника.

    :param call: Объект вызова
    :param target_user_id: Идентификатор целевого пользователя
    :param room_code: Идентификатор комнаты
    """
    user_id = call.from_user.id

    # Получаем информацию о целевом пользователе
    target_user_name = database.get_user_name(target_user_id)
    participant_count = database.get_participant_count(room_code)

    if target_user_name:
        target_full_name = f'{target_user_name[0]} {target_user_name[1]}' if target_user_name[1] else target_user_name[0]
    else:
        bot.reply_to(call.message, 'Участник не найден. 😞')
        return

    outcome = random.randint(1, 100)

    if outcome <= 50:
        # Попал в цель
        bot.send_message(target_user_id, f'{call.from_user.first_name} кинул в вас снежок и попал! ❄️')
        bot.reply_to(call.message, f'Вы попали в {target_full_name} снежком! ❄️')
    elif outcome <= 80:
        # Промазал
        bot.reply_to(call.message, f'Вы промазали и не попали в {target_full_name}. 🎯')
    else:
        # Попал в кого-то другого
        if participant_count > 2:
            other_participants = database.get_other_participants(user_id, target_user_id, room_code)
            if other_participants:
                other_user_id, other_first_name, other_last_name = random.choice(other_participants)
                other_user_name = f'{other_first_name} {other_last_name}' if other_last_name else other_first_name
                bot.send_message(other_user_id, f'{call.from_user.first_name} кинул снежок и попал в вас! ❄️')
                bot.reply_to(call.message, f'Вы промазали и попали в кого-то другого! Это был {other_user_name}! ❄️')
            else:
                bot.reply_to(call.message, f'Вы промазали и не попали в {target_full_name}. 🎯')
        else:
            bot.reply_to(call.message, f'Вы промазали и не попали в {target_full_name}. 🎯')

def notify_participants(room_code, message_text):
    """
    Уведомляет всех участников комнаты.

    :param room_code: Идентификатор комнаты
    :param message_text: Текст уведомления
    """
    participants = database.get_participants(room_code)
    for participant in participants:
        participant_id = participant[0]
        bot.send_message(participant_id, message_text)

if __name__ == '__main__':
    bot.polling()