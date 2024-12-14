import telebot
import os
from instaloader import Instaloader, Post
import shutil
import schedule
import telebot
import threading
import time

from telebot import types

# Initialize the bot with your token
BOT_TOKEN = '7883730636:AAFIF-XnnnlTS1SI2utYZ22l7kniOipbM7U'
bot = telebot.TeleBot(BOT_TOKEN)
import sqlite3

# Create a connection to the SQLite database
conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# Create a table to store user data
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users
    (id INTEGER PRIMARY KEY, username TEXT,name Text,   chat_id INTEGER, usage_count INTEGER DEFAULT 0)
''')

# Initialize Instaloader
loader = Instaloader()

def add_user(username,name, chat_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE chat_id = ?', (chat_id,))
    if cursor.fetchone() is None:
        cursor.execute('INSERT INTO users (username,name, chat_id) VALUES (?, ?,?)', (username,name, chat_id,))
        conn.commit()
    conn.close()

@bot.message_handler(commands=['start'])
def start_command(message):
    keyboard = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton("Download a Reel", callback_data="download_reel")
    keyboard.add(button)
    bot.send_message(message.chat.id, "Welcome to the Instagram Reel Downloader bot!\n\nAbout this bot: This bot can download Instagram Reels and send them to you.\n\nClick the button below to download a Reel:", reply_markup=keyboard)
    add_user(message.from_user.username, message.from_user.first_name, message.chat.id)


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "download_reel" or call.data == "download_again":
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.id, text="Paste the link of the Reel you want to download:")
        bot.register_next_step_handler(call.message, download_reel)

def download_reel(message):
    url = message.text.strip()

    if "instagram.com/reel/" not in url:
        bot.reply_to(message, "Please send a valid Instagram Reel link.")
        return

    try:
        shortcode = url.split("/reel/")[1].split("/")[0]

        target_dir = "reels"
        os.makedirs(target_dir, exist_ok=True)

        post = Post.from_shortcode(loader.context, shortcode)
        loader.download_post(post, target=target_dir)

        video_file = None
        for file in os.listdir(target_dir):
            if file.endswith('.mp4'):
                video_file = os.path.join(target_dir, file)
                break

        if video_file:
            bot.delete_message(chat_id=message.chat.id, message_id=message.id)

            with open(video_file, 'rb') as video:
                bot.send_video(message.chat.id, video)
                            # Update usage count
                conn = sqlite3.connect('users.db')
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET usage_count = usage_count + 1 WHERE chat_id = ?', (message.chat.id,))
                conn.commit()
                conn.close()
                markup = types.InlineKeyboardMarkup()
                button = types.InlineKeyboardButton("Download Again", callback_data="download_again")
                markup.add(button)

                bot.send_message(message.chat.id, "Your Reel has been downloaded! What can I download for you next?",
                                 reply_markup=markup)

            shutil.rmtree('reels')
            os.mkdir('reels')

        else:
            bot.reply_to(message, "Could not find the video file.")

        if os.path.exists(video_file):
            os.remove(video_file)

    except Exception as e:
        bot.reply_to(message, f"Error downloading the Reel: {e}")


# Fetch users from the database
def get_users_from_db():
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id FROM users")
        users = cursor.fetchall()
        conn.close()
        return [user[0] for user in users]
    except Exception as e:
        print(f"Database error: {e}")
        return []


# Send messages to all users
def send_message_to_users():
    users = get_users_from_db()
    if users:
        for user_id in users:
            try:
                keyboard = types.InlineKeyboardMarkup()
                button = types.InlineKeyboardButton("Download a Reel", callback_data="download_reel")
                keyboard.add(button)

                bot.send_message(user_id, "Hi its time to download some funny reels", reply_markup=keyboard)

                print(f"Message sent to {user_id}")
            except Exception as e:
                print(f"Error sending message to {user_id}: {e}")
    else:
        print("No users found to send messages.")

# Schedule the messages
def schedule_messages():
    schedule.every().day.at("19:43").do(send_message_to_users)

    while True:
        schedule.run_pending()
        time.sleep(1)



# Start the bot
def start_bot_polling():
    bot.polling(none_stop=True)


if __name__ == "__main__":
    # Start the scheduler in a separate thread
    scheduler_thread = threading.Thread(target=schedule_messages)
    scheduler_thread.daemon = True
    scheduler_thread.start()

    # Start the bot polling
    start_bot_polling()
