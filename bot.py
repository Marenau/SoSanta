import telebot
import sqlite3
import random
import string
from config import BOT_TOKEN, DATABASE, ADMIN_PASSWORD
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from mistralai import Mistral

bot = telebot.TeleBot(BOT_TOKEN)

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS participants (
            id INTEGER PRIMARY KEY,
            user_id INTEGER UNIQUE,
            first_name TEXT,
            last_name TEXT,
            wish TEXT,
            room_code TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assignments (
            giver_id INTEGER,
            receiver_id INTEGER,
            FOREIGN KEY (giver_id) REFERENCES participants (user_id),
            FOREIGN KEY (receiver_id) REFERENCES participants (user_id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rooms (
            code TEXT PRIMARY KEY,
            name TEXT,
            description TEXT,
            status TEXT DEFAULT 'not_started'
        )
    ''')
    conn.commit()
    conn.close()

init_db()

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

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO rooms (code, name, description) VALUES (?, ?, ?)', (room_code, room_name, room_description))
    conn.commit()
    conn.close()

    # Добавляем создателя комнаты в комнату
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO participants (user_id, first_name, last_name, room_code) VALUES (?, ?, ?, ?)', (user_id, first_name, last_name, room_code))
    conn.commit()
    conn.close()

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
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM rooms WHERE code = ?', (room_code,))
    room = cursor.fetchone()
    conn.close()

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

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO participants (user_id, first_name, last_name, wish, room_code) VALUES (?, ?, ?, ?, ?)', (user_id, first_name, last_name, wish, room_code))
    conn.commit()
    conn.close()

    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(InlineKeyboardButton('Меню'))
    bot.reply_to(message, 'Вы присоединились к игре "Тайный Санта"! 🎉', reply_markup=markup)
    notify_all_participants(f'{message.from_user.first_name} {message.from_user.last_name if message.from_user.last_name else ""} присоединился к игре! 🎅🏻')
    user_states[user_id] = None

    show_menu(message)

def leave(call):
    user_id = call.from_user.id
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT first_name, last_name, wish FROM participants WHERE user_id = ?', (user_id,))
    user_info = cursor.fetchone()
    conn.close()

    if user_info is None:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton('Присоединиться к игре 🎅🏻', callback_data='join'))
        bot.send_message(call.message.chat.id, 'Вы еще не присоединились к игре. Пожалуйста, присоединитесь к игре, чтобы всё заработало.', reply_markup=markup)
        return

    user_id = call.from_user.id
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM participants WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    bot.reply_to(call.message, 'Вы покинули игру "Тайный Санта". 😞')

def admin_login(call):
    user_id = call.from_user.id
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT first_name, last_name, wish FROM participants WHERE user_id = ?', (user_id,))
    user_info = cursor.fetchone()
    conn.close()

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
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (user_id,))
        conn.commit()
        conn.close()
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
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT room_code FROM participants WHERE user_id = ?', (user_id,))
    room_code = cursor.fetchone()
    conn.close()

    if room_code is None:
        bot.send_message(call.message.chat.id, 'Вы не являетесь участником комнаты.')
        return

    room_code = room_code[0]
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton('Просмотреть участников 🎄', callback_data='view_participants'))
    markup.add(InlineKeyboardButton('Начать игру 🎅🏻', callback_data='start_room_game'))
    bot.send_message(call.message.chat.id, 'Меню управления комнатой:', reply_markup=markup)

def delete_room(call):
    user_id = call.from_user.id
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT room_code FROM participants WHERE user_id = ?', (user_id,))
    room_code = cursor.fetchone()
    conn.close()

    if room_code is None:
        bot.send_message(call.message.chat.id, 'Вы не являетесь участником комнаты.')
        return

    room_code = room_code[0]
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM participants WHERE room_code = ?', (room_code,))
    participants = cursor.fetchall()
    conn.close()

    if participants and participants[0][0] == user_id:
        bot.send_message(call.message.chat.id, 'Вы не можете удалить комнату, так как являетесь её создателем.')
        return

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM rooms WHERE code = ?', (room_code,))
    cursor.execute('DELETE FROM participants WHERE room_code = ?', (room_code,))
    conn.commit()
    conn.close()
    bot.send_message(call.message.chat.id, 'Комната удалена. 🗑️')

def view_participants(call):
    user_id = call.from_user.id
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT room_code FROM participants WHERE user_id = ?', (user_id,))
    room_code = cursor.fetchone()
    conn.close()

    if room_code is None:
        bot.send_message(call.message.chat.id, 'Вы не являетесь участником комнаты.')
        return

    room_code = room_code[0]
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT first_name, last_name FROM participants WHERE room_code = ?', (room_code,))
    participants = cursor.fetchall()
    conn.close()
    if participants:
        participant_names = [f'{row[0]} {row[1]}' if row[1] else row[0] for row in participants]
        bot.send_message(call.message.chat.id, 'Текущие участники:\n✨\n' + '\n'.join(participant_names) + '\n✨')
    else:
        bot.send_message(call.message.chat.id, 'Пока нет участников. 😞')

def start_room_game(call):
    user_id = call.from_user.id
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT room_code FROM participants WHERE user_id = ?', (user_id,))
    room_code = cursor.fetchone()
    conn.close()

    if room_code is None:
        bot.send_message(call.message.chat.id, 'Вы не являетесь участником комнаты.')
        return

    room_code = room_code[0]
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, first_name, last_name, wish FROM participants WHERE room_code = ?', (room_code,))
    participants = cursor.fetchall()
    if len(participants) < 3:
        bot.send_message(call.message.chat.id, 'Недостаточно участников для начала игры. 😕')
        return

    participants = [(row[0], row[1], row[2], row[3]) for row in participants]
    random.shuffle(participants)
    assignments = []
    for i in range(len(participants)):
        giver = participants[i]
        receiver = participants[(i + 1) % len(participants)]
        assignments.append((giver[0], receiver[0]))

    cursor.execute('DELETE FROM assignments WHERE giver_id IN (SELECT user_id FROM participants WHERE room_code = ?) OR receiver_id IN (SELECT user_id FROM participants WHERE room_code = ?)', (room_code, room_code))
    cursor.executemany('INSERT INTO assignments (giver_id, receiver_id) VALUES (?, ?)', assignments)
    cursor.execute('UPDATE rooms SET status = "started" WHERE code = ?', (room_code,))
    conn.commit()

    for giver, receiver in assignments:
        cursor.execute('SELECT first_name, last_name, wish FROM participants WHERE user_id = ?', (receiver,))
        receiver_info = cursor.fetchone()
        if receiver_info:
            receiver_full_name = f'{receiver_info[0]} {receiver_info[1]}'
            wish = receiver_info[2] if receiver_info[2] else 'не указано'
            bot.send_message(giver, f'Вы Тайный Санта для {receiver_full_name}! 🎅🏻\nПожелание: {wish}')

    conn.close()
    bot.send_message(call.message.chat.id, 'Игра "Тайный Санта" началась! Проверьте свои личные сообщения, чтобы узнать, кому вы Тайный Санта. 🎁')

def list_participants(call):
    user_id = call.from_user.id
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT first_name, last_name, wish FROM participants WHERE user_id = ?', (user_id,))
    user_info = cursor.fetchone()
    conn.close()

    if user_info is None:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton('Присоединиться к игре 🎅🏻', callback_data='join'))
        bot.send_message(call.message.chat.id, 'Вы еще не присоединились к игре. Пожалуйста, присоединитесь к игре, чтобы всё заработало.', reply_markup=markup)
        return

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT first_name, last_name FROM participants')
    participants = cursor.fetchall()
    conn.close()
    if participants:
        participant_names = [f'{row[0]} {row[1]}' if row[1] else row[0] for row in participants]
        bot.reply_to(call.message, 'Текущие участники:\n✨\n' + '\n'.join(participant_names) + '\n✨')
    else:
        bot.reply_to(call.message, 'Пока нет участников. 😞')

def clear_participants(call):
    user_id = call.from_user.id
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT first_name, last_name, wish FROM participants WHERE user_id = ?', (user_id,))
    user_info = cursor.fetchone()
    conn.close()

    if user_info is None:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton('Присоединиться к игре 🎅🏻', callback_data='join'))
        bot.send_message(call.message.chat.id, 'Вы еще не присоединились к игре. Пожалуйста, присоединитесь к игре, чтобы всё заработало.', reply_markup=markup)
        return

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM participants')
    cursor.execute('DELETE FROM assignments')
    cursor.execute('UPDATE rooms SET status = "not_started"')
    conn.commit()
    conn.close()
    bot.reply_to(call.message, 'Список участников очищен. 🗑️')

def throw_snowball(call):
    user_id = call.from_user.id
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT first_name, last_name, wish FROM participants WHERE user_id = ?', (user_id,))
    user_info = cursor.fetchone()
    conn.close()

    if user_info is None:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton('Присоединиться к игре 🎅🏻', callback_data='join'))
        bot.send_message(call.message.chat.id, 'Вы еще не присоединились к игре. Пожалуйста, присоединитесь к игре, чтобы всё заработало.', reply_markup=markup)
        return

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, first_name, last_name FROM participants')
    participants = cursor.fetchall()
    conn.close()

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
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT first_name, last_name, wish FROM participants WHERE user_id = ?', (user_id,))
    user_info = cursor.fetchone()
    conn.close()

    if user_info is None:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton('Присоединиться к игре 🎅🏻', callback_data='join'))
        bot.send_message(call.message.chat.id, 'Вы еще не присоединились к игре. Пожалуйста, присоединитесь к игре, чтобы всё заработало.', reply_markup=markup)
        return

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT first_name, last_name FROM participants WHERE user_id = ?', (target_user_id,))
    target_user_name = cursor.fetchone()
    cursor.execute('SELECT COUNT(*) FROM participants')
    participant_count = cursor.fetchone()[0]
    conn.close()

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
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, first_name, last_name FROM participants WHERE user_id != ? AND user_id != ?', (user_id, target_user_id))
            other_participants = cursor.fetchall()
            conn.close()
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
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM participants')
    participants = cursor.fetchall()
    conn.close()
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
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT first_name, last_name, wish FROM participants WHERE user_id = ?', (user_id,))
    user_info = cursor.fetchone()
    conn.close()

    if user_info is None:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton('Присоединиться к игре 🎅🏻', callback_data='join'))
        bot.send_message(call.message.chat.id, 'Вы еще не присоединились к игре. Пожалуйста, присоединитесь к игре, чтобы всё заработало.', reply_markup=markup)
        return

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT status FROM rooms WHERE code = (SELECT room_code FROM participants WHERE user_id = ?)', (user_id,))
    status = cursor.fetchone()[0]
    conn.close()
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
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('UPDATE participants SET wish = ? WHERE user_id = ?', (wish, user_id))
    conn.commit()
    conn.close()
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton('Мой профиль', callback_data='profile'))
    bot.send_message(message.chat.id, 'Ваше пожелание изменено! 🎁', reply_markup=markup)
    user_states[user_id] = None

def show_profile(call):
    user_id = call.from_user.id
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT first_name, last_name, wish FROM participants WHERE user_id = ?', (user_id,))
    user_info = cursor.fetchone()
    conn.close()

    if user_info is None:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton('Присоединиться к игре 🎅🏻', callback_data='join'))
        bot.send_message(call.message.chat.id, 'Вы еще не присоединились к игре. Пожалуйста, присоединитесь к игре, чтобы всё заработало.', reply_markup=markup)
        return

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT first_name, last_name, wish FROM participants WHERE user_id = ?', (user_id,))
    user_info = cursor.fetchone()
    conn.close()

    first_name, last_name, wish = user_info
    full_name = f'{first_name} {last_name}' if last_name else first_name
    profile_text = f'Имя: {full_name}\nПожелание: {wish if wish else "не указано"}'

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton('Изменить пожелание', callback_data='change_wish'))
    markup.add(InlineKeyboardButton('Админ', callback_data='admin'))

    bot.send_message(call.message.chat.id, profile_text, reply_markup=markup)

def generate_story(call):
    user_id = call.from_user.id
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT first_name, last_name, wish FROM participants WHERE user_id = ?', (user_id,))
    user_info = cursor.fetchone()
    conn.close()

    if user_info is None:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton('Присоединиться к игре 🎅🏻', callback_data='join'))
        bot.send_message(call.message.chat.id, 'Вы еще не присоединились к игре. Пожалуйста, присоединитесь к игре, чтобы всё заработало.', reply_markup=markup)
        return

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT first_name, last_name FROM participants')
    participants = cursor.fetchall()
    conn.close()

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
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT first_name, last_name, wish FROM participants WHERE user_id = ?', (user_id,))
    user_info = cursor.fetchone()
    conn.close()

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
    bot.send_message(message.chat.id, 'Меню действий:', reply_markup=markup)

if __name__ == '__main__':
    bot.polling()