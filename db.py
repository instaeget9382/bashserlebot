import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = 'database/dating_bot.db'

def init_db():
    os.makedirs('database', exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                 user_id INTEGER PRIMARY KEY,
                 name TEXT,
                 age INTEGER,
                 gender TEXT,
                 city TEXT,
                 photo_id TEXT,
                 description TEXT,
                 username TEXT,
                 is_active INTEGER DEFAULT 1)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS pending_actions (
                 from_user_id INTEGER,
                 to_user_id INTEGER,
                 action_type TEXT,
                 message TEXT,
                 timestamp TEXT,
                 PRIMARY KEY (from_user_id, to_user_id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS matches (
                 user1_id INTEGER,
                 user2_id INTEGER,
                 timestamp TEXT,
                 PRIMARY KEY (user1_id, user2_id))''')
    
    conn.commit()
    conn.close()

def add_or_update_user(user_id, name, age, gender, city, photo_id, description, username=''):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO users 
                 (user_id, name, age, gender, city, photo_id, description, username, is_active)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT is_active FROM users WHERE user_id = ?), 1))''',
              (user_id, name, age, gender, city, photo_id, description, username, user_id))
    conn.commit()
    conn.close()

def get_user_profile(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT name, age, gender, city, photo_id, description, username, is_active FROM users WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    conn.close()
    return row

def update_username(user_id, username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE users SET username = ? WHERE user_id = ?', (username or '', user_id))
    conn.commit()
    conn.close()

def get_random_profile(exclude_user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT gender FROM users WHERE user_id = ?', (exclude_user_id,))
    row = c.fetchone()
    if not row:
        return None
    user_gender = row[0]
    target_gender = 'female' if user_gender == 'male' else 'male'
    
    c.execute('''SELECT user_id, name, age, city, photo_id, description, gender 
                 FROM users 
                 WHERE user_id != ? AND gender = ? AND is_active = 1 
                 ORDER BY RANDOM() LIMIT 1''', (exclude_user_id, target_gender))
    row = c.fetchone()
    conn.close()
    return row

def add_pending_action(from_user, to_user, action_type='like', message=''):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO pending_actions (from_user_id, to_user_id, action_type, message, timestamp) VALUES (?, ?, ?, ?, ?)',
              (from_user, to_user, action_type, message, ts))
    conn.commit()
    conn.close()

def get_pending_for(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT from_user_id, action_type, message FROM pending_actions WHERE to_user_id = ? ORDER BY timestamp DESC LIMIT 1', (user_id,))
    row = c.fetchone()
    conn.close()
    return row

def check_reverse_pending(user_id, target_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT action_type, message FROM pending_actions WHERE from_user_id = ? AND to_user_id = ?', (target_id, user_id))
    row = c.fetchone()
    conn.close()
    return row

def create_match(user1, user2):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO matches (user1_id, user2_id, timestamp) VALUES (?, ?, ?)', (min(user1, user2), max(user1, user2), ts))
    c.execute('DELETE FROM pending_actions WHERE (from_user_id = ? AND to_user_id = ?) OR (from_user_id = ? AND to_user_id = ?)', (user1, user2, user2, user1))
    conn.commit()
    conn.close()

async def send_match_notification(bot, recipient, partner, extra_message=None):
    profile = get_user_profile(partner)
    if not profile:
        return
    name, age, gender, city, photo_id, desc, username, _ = profile
    gender_emoji = '♂' if gender == 'male' else '♀'
    caption = f'<b>У вас взаимная симпатия! ❤️</b>\n\n<b>{name}</b>, {age} лет, {gender_emoji}, {city}\n\n{desc}'
    if extra_message:
        caption += f'\n\nСообщение: {extra_message}'
    link = f'\n\nСвязаться: t.me/{username}' if username else '\n\n(Нет @username)'
    await bot.send_photo(recipient, photo=photo_id, caption=caption + link, parse_mode='HTML')