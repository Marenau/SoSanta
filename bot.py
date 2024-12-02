import telebot
import random
import string
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from mistralai import Mistral
import database
from config import BOT_TOKEN, ADMIN_PASSWORD

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
    bot.reply_to(message, 'Добро пожаловать в волшебный мир "Тайного Санты"! 🎄✨', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if call.data == 'create_room':
        create_room(call)
    elif call.data == 'join_room':
        join_room(call)
    elif call.data == 'join':
        join(call)
    elif call.data == 'leave':
        leave(call)
    elif call.data == 'list':
        list_participants(call)
    elif call.data == 'admin':
        admin_login(call)
    elif call.data == 'snowball':
        throw_snowball(call)
    elif call.data.startswith('snowball_'):
        target_user_id = call.data.split('_')[1]
        throw_snowball_to_user(call, target_user_id)
    elif call.data.startswith('throw_back_'):
        target_user_id = call.data.split('_')[2]
        throw_snowball_to_user(call, target_user_id)
    elif call.data == 'change_wish':
        change_wish(call)
    elif call.data == 'start_game':
        start_game(call)
    elif call.data == 'clear':
        clear_participants(call)
    elif call.data == 'profile':
        show_profile(call)
    elif call.data == 'story':
        generate_story(call)
    elif call.data == 'manage_room':
        manage_room(call)
    elif call.data == 'delete_room':
        delete_room(call)
    elif call.data == 'view_participants':
        view_participants(call)
    elif call.data == 'start_room_game':
        start_room_game(call)

@bot.message_handler(func=lambda message: message.text.lower() == 'меню')
def handle_menu_command(message):
    show_menu(message)

def create_room(call):
    user_id = call.from_user.id
    user_states[user_id] = 'waiting_for_room_name'
    bot.send_message(call.message.chat.id, 'Пожалуйста, введите наименование комнаты:')

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'waiting_for_room_name')
def save_room_name(message):
    user_id = message.from_user.id
    room_name = message.text
    user_states[user_id] = 'waiting_for_room_description'
    bot.send_message(message.chat.id, 'Пожалуйста, введите описание комнаты:')
    user_states[user_id] = {'room_name': room_name}

@bot.message_handler(func=lambda message: isinstance(user_states.get(message.from_user.id), dict) and 'room_name' in user_states[message.from_user.id])
def save_room_description(message):
    user_id = message.from_user.id
    room_description = message.text
    room_name = user_states[user_id]['room_name']
    room_code = generate_room_code()

    database.add_room(room_code, room_name, room_description, user_id)

    # Добавляем создателя комнаты в комнату
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    database.add_participant(user_id, room_code, first_name, last_name, None)

    user_states[user_id] = None
    bot.send_message(message.chat.id, f'Комната создана!\nКод: {room_code}\nНаименование: {room_name}\nОписание: {room_description}')

def generate_room_code():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

def join_room(call):
    user_id = call.from_user.id
    user_states[user_id] = 'waiting_for_room_code'
    bot.send_message(call.message.chat.id, 'Пожалуйста, введите код комнаты:')

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'waiting_for_room_code')
def save_room_code(message):
    user_id = message.from_user.id
    room_code = message.text
    room = database.get_room(room_code)

    if room:
        user_states[user_id] = 'waiting_for_wish'
        bot.send_message(message.chat.id, 'Пожалуйста, напишите ваше новогоднее пожелание (подарок, который вы хотите): 🎁')
        user_states[user_id] = {'room_code': room_code}
    else:
        bot.send_message(message.chat.id, 'Комната с таким кодом не найдена. Пожалуйста, попробуйте снова.')
        user_states[user_id] = None

@bot.message_handler(func=lambda message: isinstance(user_states.get(message.from_user.id), dict) and 'room_code' in user_states[message.from_user.id])
def save_wish(message):
    user_id = message.from_user.id
    room_code = user_states[user_id]['room_code']
    wish = message.text
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    database.add_participant(user_id, room_code, first_name, last_name, wish)

    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(InlineKeyboardButton('Меню'))
    bot.reply_to(message, 'Вы присоединились к игре "Тайный Санта"! 🎉', reply_markup=markup)
    notify_all_participants(f'{message.from_user.first_name} {message.from_user.last_name if message.from_user.last_name else ""} присоединился к игре! 🎅🏻')
    user_states[user_id] = None

    show_menu(message)

def leave(call):
    user_id = call.from_user.id
    user_info = database.get_participant(user_id)

    if user_info is None:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton('Присоединиться к игре 🎅🏻', callback_data='join'))
        bot.send_message(call.message.chat.id, 'Вы еще не присоединились к игре. Пожалуйста, присоединитесь к игре, чтобы всё заработало.', reply_markup=markup)
        return

    database.delete_participant(user_id)
    bot.reply_to(call.message, 'Вы покинули игру "Тайный Санта". 😞')

def admin_login(call):
    user_id = call.from_user.id
    user_info = database.get_participant(user_id)

    if user_info is None:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton('Присоединиться к игре 🎅🏻', callback_data='join'))
        bot.send_message(call.message.chat.id, 'Вы еще не присоединились к игре. Пожалуйста, присоединитесь к игре, чтобы всё заработало.', reply_markup=markup)
        return

    user_id = call.from_user.id
    admin_states[user_id] = 'waiting_for_password'
    bot.reply_to(call.message, 'Пожалуйста, введите пароль администратора: 🔒')

@bot.message_handler(func=lambda call: admin_states.get(call.from_user.id) == 'waiting_for_password')
def check_admin_password(call):
    user_id = call.from_user.id
    if call.text == ADMIN_PASSWORD:
        admin_states[user_id] = 'admin_logged_in'
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton('Начать игру 🎅🏻', callback_data='start_game'))
        markup.add(InlineKeyboardButton('Список участников 🎄', callback_data='list'))
        markup.add(InlineKeyboardButton('Очистить список участников 🗑️', callback_data='clear'))
        markup.add(InlineKeyboardButton('Управление комнатой 🏠', callback_data='manage_room'))
        bot.reply_to(call, 'Вы вошли в режим администратора. 👑', reply_markup=markup)
    else:
        admin_states[user_id] = None
        bot.reply_to(call, 'Неверный пароль. ❌')

def manage_room(call):
    user_id = call.from_user.id
    room_id = database.get_room_id_by_user(user_id)

    if room_id is None:
        bot.send_message(call.message.chat.id, 'Вы не являетесь участником комнаты.')
        return

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton('Просмотреть участников 🎄', callback_data='view_participants'))
    markup.add(InlineKeyboardButton('Начать игру 🎅🏻', callback_data='start_room_game'))
    bot.send_message(call.message.chat.id, 'Меню управления комнатой:', reply_markup=markup)

def delete_room(call):
    user_id = call.from_user.id
    room_id = database.get_room_id_by_user(user_id)

    if room_id is None:
        bot.send_message(call.message.chat.id, 'Вы не являетесь участником комнаты.')
        return

    participants = database.get_participants_by_room(room_id)

    if participants and participants[0][0] == user_id:
        bot.send_message(call.message.chat.id, 'Вы не можете удалить комнату, так как являетесь её создателем.')
        return

    database.delete_room(room_id)
    bot.send_message(call.message.chat.id, 'Комната удалена. 🗑️')

def view_participants(call):
    user_id = call.from_user.id
    room_id = database.get_room_id_by_user(user_id)

    if room_id is None:
        bot.send_message(call.message.chat.id, 'Вы не являетесь участником комнаты.')
        return

    participants = database.get_participants_by_room(room_id)
    if participants:
        participant_names = [f'{row[0]} {row[1]}' if row[1] else row[0] for row in participants]
        bot.send_message(call.message.chat.id, 'Текущие участники:\n✨\n' + '\n'.join(participant_names) + '\n✨')
    else:
        bot.send_message(call.message.chat.id, 'Пока нет участников. 😞')

def start_room_game(call):
    user_id = call.from_user.id
    room_id = database.get_room_id_by_user(user_id)

    if room_id is None:
        bot.send_message(call.message.chat.id, 'Вы не являетесь участником комнаты.')
        return

    if not database.start_room_game(room_id):
        bot.send_message(call.message.chat.id, 'Недостаточно участников для начала игры. 😕')
        return

    assignments = database.get_assignments(room_id)
    for giver, receiver in assignments:
        receiver_info = database.get_participant(receiver)
        if receiver_info:
            receiver_full_name = f'{receiver_info[0]} {receiver_info[1]}'
            wish = receiver_info[2] if receiver_info[2] else 'не указано'
            bot.send_message(giver, f'Вы Тайный Санта для {receiver_full_name}! 🎅🏻\nПожелание: {wish}')

    bot.send_message(call.message.chat.id, 'Игра "Тайный Санта" началась! Проверьте свои личные сообщения, чтобы узнать, кому вы Тайный Санта. 🎁')

def list_participants(call):
    user_id = call.from_user.id
    user_info = database.get_participant(user_id)

    if user_info is None:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton('Присоединиться к игре 🎅🏻', callback_data='join'))
        bot.send_message(call.message.chat.id, 'Вы еще не присоединились к игре. Пожалуйста, присоединитесь к игре, чтобы всё заработало.', reply_markup=markup)
        return

    participants = database.get_all_participants()
    if participants:
        participant_names = [f'{row[0]} {row[1]}' if row[1] else row[0] for row in participants]
        bot.reply_to(call.message, 'Текущие участники:\n✨\n' + '\n'.join(participant_names) + '\n✨')
    else:
        bot.reply_to(call.message, 'Пока нет участников. 😞')

def clear_participants(call):
    user_id = call.from_user.id
    user_info = database.get_participant(user_id)

    if user_info is None:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton('Присоединиться к игре 🎅🏻', callback_data='join'))
        bot.send_message(call.message.chat.id, 'Вы еще не присоединились к игре. Пожалуйста, присоединитесь к игре, чтобы всё заработало.', reply_markup=markup)
        return

    database.clear_participants()
    bot.reply_to(call.message, 'Список участников очищен. 🗑️')

def throw_snowball(call):
    user_id = call.from_user.id
    user_info = database.get_participant(user_id)

    if user_info is None:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton('Присоединиться к игре 🎅🏻', callback_data='join'))
        bot.send_message(call.message.chat.id, 'Вы еще не присоединились к игре. Пожалуйста, присоединитесь к игре, чтобы всё заработало.', reply_markup=markup)
        return

    participants = database.get_all_participants()

    # Проверка, есть ли другие участники кроме текущего пользователя
    other_participants = [participant for participant in participants if participant[0] != user_id]

    if other_participants:
        markup = InlineKeyboardMarkup()
        for participant in other_participants:
            target_user_id, first_name, last_name = participant
            full_name = f'{first_name} {last_name}' if last_name else first_name
            markup.add(InlineKeyboardButton(full_name, callback_data=f'snowball_{target_user_id}'))
        bot.reply_to(call.message, 'Выберите участника, в которого хотите кинуть снежок:', reply_markup=markup)
    else:
        bot.reply_to(call.message, 'Пока нет других участников. 😞')

def throw_snowball_to_user(call, target_user_id):
    user_id = call.from_user.id
    user_info = database.get_participant(user_id)

    if user_info is None:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton('Присоединиться к игре 🎅🏻', callback_data='join'))
        bot.send_message(call.message.chat.id, 'Вы еще не присоединились к игре. Пожалуйста, присоединитесь к игре, чтобы всё заработало.', reply_markup=markup)
        return

    target_user_name = database.get_participant(target_user_id)
    participant_count = len(database.get_all_participants())

    if target_user_name:
        target_full_name = f'{target_user_name[0]} {target_user_name[1]}' if target_user_name[1] else target_user_name[0]
    else:
        bot.reply_to(call.message, 'Участник не найден. 😞')
        return

    outcome = random.randint(1, 100)

    if outcome <= 50:
        # Попал в цель
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton('Кинуть в ответ', callback_data=f'throw_back_{user_id}_{target_user_id}'))
        bot.send_message(target_user_id, f'{call.from_user.first_name} кинул в вас снежок и попал! ❄️', reply_markup=markup)
        bot.reply_to(call.message, f'Вы попали в {target_full_name} снежком! ❄️')
    elif outcome <= 80:
        # Промазал
        bot.reply_to(call.message, f'Вы промазали и не попали в {target_full_name}. 🎯')
    else:
        # Попал в кого-то другого
        if participant_count > 2:
            other_participants = [participant for participant in database.get_all_participants() if participant[0] != user_id and participant[0] != target_user_id]
            if other_participants:
                other_user_id, other_first_name, other_last_name = random.choice(other_participants)
                other_user_name = f'{other_first_name} {other_last_name}' if other_last_name else other_first_name
                bot.send_message(other_user_id, f'{call.from_user.first_name} кинул снежок и попал в вас! ❄️')
                bot.reply_to(call.message, f'Вы промазали и попали в кого-то другого! Это был {other_user_name}! ❄️')
            else:
                bot.reply_to(call.message, f'Вы промазали и не попали в {target_full_name}. 🎯')
        else:
            bot.reply_to(call.message, f'Вы промазали и не попали в {target_full_name}. 🎯')

def notify_all_participants(message_text):
    participants = database.get_all_participants()
    for participant in participants:
        user_id = participant[0]
        try:
            bot.send_message(user_id, message_text)
        except telebot.apihelper.ApiTelegramException as e:
            if e.result_json['error_code'] == 403:
                print(f"Не удалось отправить сообщение пользователю с ID {user_id}: {e.result_json['description']}")
            else:
                raise e

def change_wish(call):
    global game_started

    user_id = call.from_user.id
    user_info = database.get_participant(user_id)

    if user_info is None:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton('Присоединиться к игре 🎅🏻', callback_data='join'))
        bot.send_message(call.message.chat.id, 'Вы еще не присоединились к игре. Пожалуйста, присоединитесь к игре, чтобы всё заработало.', reply_markup=markup)
        return

    room_id = database.get_room_id_by_user(user_id)
    status = database.get_room_status(room_id)
    if status == 'started':
        bot.reply_to(call.message, 'Извините, игра уже началась. Вы не можете изменить свое пожелание. 🚫')
        return

    user_id = call.from_user.id
    bot.reply_to(call.message, 'Пожалуйста, напишите ваше новое пожелание (подарок, который вы хотите): 🎁')
    user_states[user_id] = 'waiting_for_wish_change'

@bot.message_handler(func=lambda call: user_states.get(call.from_user.id) == 'waiting_for_wish_change')
def save_changed_wish(message):
    user_id = message.from_user.id
    wish = message.text
    database.update_participant_wish(user_id, wish)
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton('Мой профиль', callback_data='profile'))
    bot.send_message(message.chat.id, 'Ваше пожелание изменено! 🎁', reply_markup=markup)
    user_states[user_id] = None

def show_profile(call):
    user_id = call.from_user.id
    user_info = database.get_participant(user_id)

    if user_info is None:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton('Присоединиться к игре 🎅🏻', callback_data='join'))
        bot.send_message(call.message.chat.id, 'Вы еще не присоединились к игре. Пожалуйста, присоединитесь к игре, чтобы всё заработало.', reply_markup=markup)
        return

    first_name, last_name, wish = user_info
    full_name = f'{first_name} {last_name}' if last_name else first_name
    profile_text = f'Имя: {full_name}\nПожелание: {wish if wish else "не указано"}'

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton('Изменить пожелание', callback_data='change_wish'))
    markup.add(InlineKeyboardButton('Админ', callback_data='admin'))

    bot.send_message(call.message.chat.id, profile_text, reply_markup=markup)

def generate_story(call):
    user_id = call.from_user.id
    user_info = database.get_participant(user_id)

    if user_info is None:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton('Присоединиться к игре 🎅🏻', callback_data='join'))
        bot.send_message(call.message.chat.id, 'Вы еще не присоединились к игре. Пожалуйста, присоединитесь к игре, чтобы всё заработало.', reply_markup=markup)
        return

    participants = database.get_all_participants()

    if not participants:
        bot.reply_to(call.message, 'Пока нет участников для генерации истории. 😞')
        return

    # Выбираем случайных участников
    selected_participants = random.sample(participants, random.randint(1, len(participants)))
    participant_names = [f'{row[0]} {row[1]}' if row[1] else row[0] for row in selected_participants]

    # Выбираем случайное настроение
    moods = ['Веселая история', 'Смешная история', 'Кринжовая история']
    mood = random.choice(moods)

    # Формируем запрос к Mistral API
    prompt = (
        f"Ты профессиональный писатель историй, ты пишешь очень интересные истории, очень красивым языком, ты владеешь написанием рассказов и историй в мастерстве. "
        f"Тебе нужно написать короткий новогодний рассказ с законченной концовкой. Ты должен ответить мне только историей и ничем больше, ничего лишнего писать не надо, "
        f"от тебя я должен получить только историю. При написании истории ориентируйся на пол участника по имени и используй соответствующие склонения/спряжения и местоимения. "
        f"При каждом моем сообщении пиши разные рассказы, они не должны повторяться. В истории не должно быть романтического подтекста. Тема: Новый год, новогодняя тематика, новогодние развлечения. Участники: {', '.join(participant_names)}. Настроение: {mood}"
    )

    # Отправляем сообщение пользователю, что нужно немного подождать
    bot.send_message(call.message.chat.id, 'Эльфы Санты очень трудятся, чтобы быстро написать рассказ! 🧝🏻\nПожалуйста, подождите немного...')

    # Отправляем запрос к Mistral API
    api_key = 'utxpKKoTJR5vVUs99Y1i5cnfS7eJ7IG5'
    model = "mistral-large-latest"
    client = Mistral(api_key=api_key)
    chat_response = client.chat.complete(
        model=model,
        messages=[
            {
                "role": "user",
                "content": prompt,
            },
        ]
    )

    # Отправляем ответ пользователю
    bot.send_message(call.message.chat.id, chat_response.choices[0].message.content)

def show_menu(message):
    user_id = message.from_user.id
    user_info = database.get_participant(user_id)

    if user_info is None:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton('Присоединиться к игре', callback_data='join'))
        bot.send_message(message.chat.id, 'Вы еще не присоединились к игре. Пожалуйста, присоединитесь к игре, чтобы открыть меню действий.', reply_markup=markup)
        return

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton('Покинуть игру 😞', callback_data='leave'))
    markup.add(InlineKeyboardButton('Список участников 🎄', callback_data='list'))
    markup.add(InlineKeyboardButton('Кинуть снежок ❄️', callback_data='snowball'))
    markup.add(InlineKeyboardButton('Новогодний рассказ ☃️', callback_data='story'))
    markup.add(InlineKeyboardButton('Мой профиль 🪪', callback_data='profile'))

    room_id = database.get_room_id_by_user(user_id)
    status = database.get_room_status(room_id)

    if status == '1':
        markup.add(InlineKeyboardButton('Отправить сообщение получателю', callback_data='send_to_receiver'))
        markup.add(InlineKeyboardButton('Отправить сообщение отправителю', callback_data='send_to_giver'))
    else:
        bot.send_message(message.chat.id, 'Игра еще не началась. Получатель вашего подарка еще не назначен.')

    bot.send_message(message.chat.id, 'Меню действий:', reply_markup=markup)

@bot.message_handler(func=lambda message: message.text.lower().startswith('/send_to_receiver '))
def handle_send_to_receiver(message):
    user_id = message.from_user.id
    user_info = database.get_participant(user_id)

    if user_info is None:
        bot.send_message(message.chat.id, 'Вы еще не присоединились к игре. Пожалуйста, присоединитесь к игре, чтобы отправить сообщение.')
        return

    room_id = database.get_room_id_by_user(user_id)
    status = database.get_room_status(room_id)

    if status != '1':
        bot.send_message(message.chat.id, 'Игра еще не началась. Получатель вашего подарка еще не назначен.')
        return

    assignments = database.get_assignments(room_id)
    receiver_id = None
    for giver, receiver in assignments:
        if giver == user_id:
            receiver_id = receiver
            break

    if receiver_id is None:
        bot.send_message(message.chat.id, 'Вы еще не назначены Тайным Сантой. Пожалуйста, подождите начала игры.')
        return

    message_text = message.text[len('/send_to_receiver '):]
    if not message_text:
        bot.send_message(message.chat.id, 'Пожалуйста, введите текст сообщения после команды /send_to_receiver.')
        return

    bot.send_message(receiver_id, f'Сообщение от вашего Тайного Санты: {message_text}')
    bot.send_message(message.chat.id, 'Ваше сообщение отправлено!')

@bot.message_handler(func=lambda message: message.text.lower().startswith('/send_to_giver '))
def handle_send_to_giver(message):
    user_id = message.from_user.id
    user_info = database.get_participant(user_id)

    if user_info is None:
        bot.send_message(message.chat.id, 'Вы еще не присоединились к игре. Пожалуйста, присоединитесь к игре, чтобы отправить сообщение.')
        return

    room_id = database.get_room_id_by_user(user_id)
    status = database.get_room_status(room_id)

    if status != '1':
        bot.send_message(message.chat.id, 'Игра еще не началась. Отправитель вашего подарка еще не назначен.')
        return

    assignments = database.get_assignments(room_id)
    giver_id = None
    for giver, receiver in assignments:
        if receiver == user_id:
            giver_id = giver
            break

    if giver_id is None:
        bot.send_message(message.chat.id, 'Вы еще не назначены Тайным Сантой. Пожалуйста, подождите начала игры.')
        return

    message_text = message.text[len('/send_to_giver '):]
    if not message_text:
        bot.send_message(message.chat.id, 'Пожалуйста, введите текст сообщения после команды /send_to_giver.')
        return

    bot.send_message(giver_id, f'Сообщение от вашего получателя: {message_text}')
    bot.send_message(message.chat.id, 'Ваше сообщение отправлено!')

if __name__ == '__main__':
    bot.polling()
