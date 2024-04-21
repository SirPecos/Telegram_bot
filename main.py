# Импортируем необходимые классы.
import logging
import json
from telegram.ext import Application, MessageHandler, filters, CommandHandler
from telegram import ReplyKeyboardMarkup
from towns import towns
import pandas as pd
import random
import sqlite3
from config import BOT_TOKEN

# Запускаем логгирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.ERROR
)

logger = logging.getLogger(__name__)


# функция добавляет в словарь towns города из википедии
def download_goroda():
    for key, _ in towns.items():
        towns[key] = []
    url = 'https://ru.wikipedia.org/wiki/%D0%A1%D0%BF%D0%B8%D1%81%D0%BE%D0%BA' \
          '_%D0%B3%D0%BE%D1%80%D0%BE%D0%B4%D0%BE%D0%B2_%D0%A0%D0%BE%D1%81%D1%81%D0%B8%D0%B8'
    df = pd.read_html(url)[0]

    for i in df['Город']:
        if i[-1] == '.':
            i = i[0:-9]
        if i not in towns[i[0]]:
            towns[i[0]].append(i.upper())

    data_towns = json.dumps(towns)

    return data_towns


# приветствие, добавляем в бд chat_id и словарь towns в виде строки
async def start(update, context):
    data_towns = download_goroda()
    user = update.effective_user
    await update.message.reply_html(f'Привет, {user.mention_html()}! Я умею играть в города! Если захочешь поиграть,'
                                    f' то вызови команду /play')
    with sqlite3.connect('users_info.db') as connect:
        cursor = connect.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users(id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                                                            chat_id INTEGER NOT NULL,
                                                            last_letter TEXT,
                                                            named_words TEXT,
                                                            towns TEXT NOT NULL)''')
        connect.commit()

        chat_id = update.message.chat_id
        cursor.execute(f'SELECT id FROM users WHERE chat_id = {chat_id}')
        data = cursor.fetchone()
        if data is None:
            cursor.execute(f'INSERT INTO users (chat_id, last_letter, towns) VALUES(?, ?, ?);',
                           (chat_id, 'Ь', data_towns))
        connect.commit()


# получаем все переменные из бд по chat_id
async def select_info(update):
    with sqlite3.connect('users_info.db') as connect:
        cursor = connect.cursor()
        chat_id = update.message.chat_id
        cursor.execute(f'SELECT last_letter FROM users WHERE chat_id = {chat_id}')
        data = cursor.fetchone()
        data = list(data)
        data = data[0]
        if data == 'Ь':
            last_letter = ''
        else:
            last_letter = data
        cursor.execute(f'SELECT named_words FROM users WHERE chat_id = {chat_id}')
        data = cursor.fetchone()[0]
        if data:
            named_words = data.split(', ')
        else:
            named_words = []
        cursor.execute(f'SELECT towns FROM users WHERE chat_id = {chat_id}')
        data = cursor.fetchone()[0]
        towns = json.loads(data)

        return last_letter, named_words, towns


# основная функция, которая позволяет играть в города
async def goroda(update, context):
    connect = sqlite3.connect('users_info.db')
    cursor = connect.cursor()
    chat_id = update.message.chat_id
    last_letter, named_words, towns = await select_info(update)
    word = update.message.text.upper()
    if not last_letter:

        if word in towns[word[0]]:
            named_words.append(word)

            if word[-1] == 'Ь' or word[-1] == 'Ы':
                last_letter = word[-2]

            else:
                last_letter = word[-1]
            cursor.execute('''UPDATE users SET last_letter = ? WHERE chat_id = ?''', (last_letter, chat_id))
            connect.commit()

            if not towns[last_letter]:
                for i in reversed(list(word)):
                    last_letter = i
                    if not towns[last_letter]:
                        continue
                    else:
                        break
                cursor.execute('''UPDATE users SET last_letter = ? WHERE chat_id = ?''', (last_letter, chat_id))
                connect.commit()
                cursor.execute(f'SELECT last_letter FROM users WHERE chat_id = {chat_id}')
                last_letter = list(cursor.fetchone())[0]
                await update.message.reply_text(f'Закончились российские города на определённые буквы, поэтому мне на'
                                                f' {last_letter}')

            cursor.execute('''UPDATE users SET last_letter = ? WHERE chat_id = ?''', (last_letter, chat_id))
            named_words = ', '.join(named_words)
            cursor.execute('''UPDATE users SET named_words = ? WHERE chat_id = ?''', (named_words, chat_id))
            towns[word[0]].remove(word)
            data_towns = json.dumps(towns)
            cursor.execute('''UPDATE users SET towns = ? WHERE chat_id = ?''', (data_towns, chat_id))
            connect.commit()

        elif word not in towns[word[0]]:
            await update.message.reply_text('Такого российского города не существует, попробуйте ещё раз')
            cursor.close()
            return goroda

    else:
        if word in towns[word[0]] and word not in named_words and last_letter == word[0]:
            named_words.append(word)

            if word[-1] == 'Ь' or word[-1] == 'Ы':
                last_letter = word[-2]

            else:
                last_letter = word[-1]
            cursor.execute('''UPDATE users SET last_letter = ? WHERE chat_id = ?''', (last_letter, chat_id))
            connect.commit()

            if not towns[last_letter]:
                for i in reversed(list(word)):
                    last_letter = i
                    if not towns[last_letter]:
                        continue
                    else:
                        break
                cursor.execute('''UPDATE users SET last_letter = ? WHERE chat_id = ?''', (last_letter, chat_id))
                connect.commit()
                cursor.execute(f'SELECT last_letter FROM users WHERE chat_id = {chat_id}')
                last_letter = list(cursor.fetchone())[0]
                await update.message.reply_text(f'Закончились российские города на определённые буквы, поэтому мне на'
                                                f' {last_letter}')

            if not towns[last_letter]:
                await update.message.reply_text('Закончились все российские города на буквы в вашем слове,'
                                                ' вы выиграли!')
                cursor.close()
                return stop

            cursor.execute('''UPDATE users SET last_letter = ? WHERE chat_id = ?''', (last_letter, chat_id))
            named_words = ', '.join(named_words)
            cursor.execute('''UPDATE users SET named_words = ? WHERE chat_id = ?''', (named_words, chat_id))
            towns[word[0]].remove(word)
            data_towns = json.dumps(towns)
            cursor.execute('''UPDATE users SET towns = ? WHERE chat_id = ?''', (data_towns, chat_id))
            connect.commit()

        elif word in named_words:
            await update.message.reply_text('Такой город уже был, попробуйте ещё раз')
            cursor.close()
            return goroda

        elif word not in towns[word[0]]:
            await update.message.reply_text('Такого российского города не существует, попробуйте ещё раз')
            cursor.close()
            return goroda

        elif last_letter != word[0]:
            cursor.execute(f'SELECT last_letter FROM users WHERE chat_id = {chat_id}')
            last_letter = list(cursor.fetchone())[0]
            await update.message.reply_text(f'Город должен начинаться на букву {last_letter}, попробуйте ещё раз')
            cursor.close()
            return goroda

    last_letter, named_words, towns = await select_info(update)

    number = random.randint(0, len(towns[last_letter]))
    word_of_bot = towns[last_letter][number - 1]
    towns[last_letter].remove(word_of_bot)
    named_words.append(word_of_bot)

    named_words = ', '.join(named_words)
    cursor.execute('''UPDATE users SET named_words = ? WHERE chat_id = ?''', (named_words, chat_id))
    data_towns = json.dumps(towns)
    cursor.execute('''UPDATE users SET towns = ? WHERE chat_id = ?''', (data_towns, chat_id))
    connect.commit()

    if word_of_bot[-1] == 'Ь' or word_of_bot[-1] == 'Ы':
        last_letter = word_of_bot[-2]

    else:
        last_letter = word_of_bot[-1]

    if not towns[last_letter]:
        for i in reversed(list(word_of_bot)):
            last_letter = i
            if not towns[last_letter]:
                continue
            else:
                break

    cursor.execute('''UPDATE users SET last_letter = ? WHERE chat_id = ?''', (last_letter, chat_id))
    connect.commit()

    if not towns[last_letter]:
        await update.message.reply_text(f'{word_of_bot.capitalize()}')
        await update.message.reply_text('Закончились все российские города на буквы в моём слове, вы проиграли!')
        cursor.close()
        return stop

    cursor.execute(f'SELECT last_letter FROM users WHERE chat_id = {chat_id}')
    last_letter = list(cursor.fetchone())[0]
    await update.message.reply_text(f'{word_of_bot.capitalize()}, вам на {last_letter}')
    cursor.close()
    return goroda


# правила, начинаем играть
async def play(update, context):
    data_towns = download_goroda()
    with sqlite3.connect('users_info.db') as connect:
        cursor = connect.cursor()
        chat_id = update.message.chat_id
        cursor.execute('''UPDATE users SET last_letter = ? WHERE chat_id = ?''', ("Ь", chat_id))
        cursor.execute('''UPDATE users SET named_words = ? WHERE chat_id = ?''', (None, chat_id))
        cursor.execute('''UPDATE users SET towns = ? WHERE chat_id = ?''', (data_towns, chat_id))
        connect.commit()
        await update.message.reply_text(
            "Давай сыграем в города, прервать игру можно командой /stop")
        await update.message.reply_text(
            'Правила: участники выстраивают цепочку российских городов: каждый новый начинается'
            ' на ту же букву, на какую оканчивается предыдущий.'
            ' Назовите город на любую букву.')
        return goroda


# окончание игры, очищаем словарь
async def stop(update, context):
        await update.message.reply_html(
            f"Спасибо, что поиграли со мной!")


# запускаем бота
def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("play", play))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT, goroda))

    application.run_polling()


if __name__ == '__main__':
    main()
