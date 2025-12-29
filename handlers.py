from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from db import add_or_update_user, get_user_profile, get_random_profile, update_username, add_pending_action, get_pending_for, check_reverse_pending, create_match, send_match_notification
import sqlite3

DB_PATH = 'database/dating_bot.db'

RULES, NAME, AGE, GENDER, CITY, PHOTO, DESCRIPTION, SUPER_MESSAGE = range(8)
EDIT_PHOTO, EDIT_DESC, CONFIRM_EDIT, CONFIRM_DELETE = range(8, 12)

MAIN_KEYBOARD = ReplyKeyboardMarkup([
    [KeyboardButton('❤️'), KeyboardButton('💔'), KeyboardButton('⚙️')]
], resize_keyboard=True)

LIKE_RESPONSE_KEYBOARD = ReplyKeyboardMarkup([
    [KeyboardButton('Посмотреть')]
], resize_keyboard=True)

CONFIRM_MATCH_KEYBOARD = ReplyKeyboardMarkup([
    [KeyboardButton('✅ Подтвердить симпатию'), KeyboardButton('❌ Отказаться')]
], resize_keyboard=True)

SUPER_RESPONSE_KEYBOARD = ReplyKeyboardMarkup([
    [KeyboardButton('✅ Посмотреть'), KeyboardButton('❌ Пропустить')]
], resize_keyboard=True)

CONFIRM_EDIT_KEYBOARD = ReplyKeyboardMarkup([
    [KeyboardButton('✅ Подтвердить'), KeyboardButton('❌ Отмена')]
], resize_keyboard=True)

CONFIRM_DELETE_KEYBOARD = ReplyKeyboardMarkup([
    [KeyboardButton('✅ Да'), KeyboardButton('❌ Отмена')]
], resize_keyboard=True)

START_SEARCH_KEYBOARD = ReplyKeyboardMarkup([
    [KeyboardButton('Начать поиск')]
], resize_keyboard=True)

INVITE_TEXT = ("Хватит скучать в одиночестве!\n"
               "В Башкирии есть бот для знакомств — @bashserle_bot")

RULES_TEXT = """Правила сообщества

Добро пожаловать в наше сообщество! Здесь люди встречаются для серьезных отношений, искреннего общения, дружбы и поиска единомышленников.

Чтобы всем было комфортно и безопасно, мы установили несколько простых, но строгих правил.

❌ Запрещено:

1. Контент «18+» и предложение интимных услуг. Любые намёки, предложения, реклама или обсуждение услуг сексуального характера строго запрещены.
2. Реклама и коммерция. Запрещена реклама любых товаров, услуг, сайтов, других чатов, каналов, ботов (фриланс, крипта, MLM, Casino и т.д.).
3. Анонимность и фейковые аккаунты. Для безопасности мы против аккаунтов без фото, имени или с явно фейковой информацией.

🚨 Важно: как сообщить о нарушении?
Если вам написали в личные сообщения или вы увидели в чате нарушение этих правил 

1. Сразу напишите в поддержку: @serleinfo
2. Обязательно укажите: username нарушителя  и пришлите скриншот его сообщения.
3. Не вступайте в конфликт и не отвечайте провокатору.

✅ Что мы делаем:
Получив жалобу с доказательствами, мы немедленно и навсегда заблокируем нарушителя в боте и всех связанных чатах без предупреждения.

Цель наших правил — создать безопасное и приятное пространство для всех.
Спасибо, что вы с нами и соблюдаете эти простые принципы!"""

async def get_settings_keyboard(user_id):
    profile = get_user_profile(user_id)
    is_active = profile[7] if profile else 0
    pause_button = '▶️' if is_active == 0 else '🟰'
    return ReplyKeyboardMarkup([
        [KeyboardButton('🔍'), KeyboardButton('👤'), KeyboardButton(pause_button), KeyboardButton('🗣️')]
    ], resize_keyboard=True)

async def get_settings_text(user_id):
    profile = get_user_profile(user_id)
    is_active = profile[7] if profile else 0
    if is_active == 0:
        return ("🔍 - Поиск анкет\n"
                "👤 - Моя анкета\n"
                "▶️ - Возобновить анкету\n"
                "🗣️ - Пригласить друзей")
    else:
        return ("🔍 - Поиск анкет\n"
                "👤 - Моя анкета\n"
                "🟰 - Сделать паузу\n"
                "🗣️ - Пригласить друзей")

# Убраны все кнопки - меню "Моя анкета" теперь только показывает анкету

# Функция show_my_profile удалена - логика встроена в обработчик кнопки "👤"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    username = update.effective_user.username or ''
    profile = get_user_profile(user_id)
    if profile:
        if profile[6] != username:
            update_username(user_id, username)
        await update.message.reply_text('Привет! Выбери действие:', reply_markup=MAIN_KEYBOARD)
        context.user_data.clear()
        return ConversationHandler.END

    context.user_data['username'] = username
    context.user_data['recreate'] = False
    await update.message.reply_text(RULES_TEXT, reply_markup=ReplyKeyboardMarkup([[KeyboardButton('Ознакомлен✅')]], resize_keyboard=True))
    return RULES

async def rules_agree(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == 'Ознакомлен✅':
        await update.message.reply_text('Привет! Давай создадим анкету.\nВведи имя:', reply_markup=ReplyKeyboardRemove())
        return NAME
    return RULES

async def register_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['name'] = update.message.text.strip()
    await update.message.reply_text('Сколько тебе лет?')
    return AGE

async def register_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        age = int(update.message.text)
        if age < 16 or age > 100:
            await update.message.reply_text('Возраст от 16 до 100 лет. Попробуй ещё:')
            return AGE
        context.user_data['age'] = age
        keyboard = [[KeyboardButton('Мужской'), KeyboardButton('Женский')]]
        await update.message.reply_text('Выбери пол:', reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True))
        return GENDER
    except:
        await update.message.reply_text('Введи число:')
        return AGE

async def register_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if text == 'Мужской':
        context.user_data['gender'] = 'male'
    elif text == 'Женский':
        context.user_data['gender'] = 'female'
    else:
        await update.message.reply_text('Выбери из кнопок:', reply_markup=ReplyKeyboardMarkup([[KeyboardButton('Мужской'), KeyboardButton('Женский')]], one_time_keyboard=True))
        return GENDER
    await update.message.reply_text('Из какого ты города?', reply_markup=ReplyKeyboardRemove())
    return CITY

async def register_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['city'] = update.message.text.strip()
    await update.message.reply_text('Отправь своё фото:')
    return PHOTO

async def register_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['photo'] = update.message.photo[-1].file_id
    await update.message.reply_text('Напиши о себе (описание):')
    return DESCRIPTION

async def register_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    was_recreate = context.user_data.get('recreate', False)
    if was_recreate:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
    add_or_update_user(user_id, context.user_data['name'], context.user_data['age'], context.user_data['gender'],
                       context.user_data['city'], context.user_data['photo'], update.message.text.strip(), context.user_data['username'])
    
    # Очищаем контекст перед возвратом
    context.user_data.clear()
    
    if was_recreate:
        # После пересоздания анкеты возвращаем в главное меню поиска
        await update.message.reply_text('✅ Анкета создана заново! Возвращаемся к поиску.', reply_markup=MAIN_KEYBOARD)
        # Показываем следующую анкету
        await show_next_profile(update, context)
    else:
        # Первое создание анкеты
        await update.message.reply_text('✅ Анкета создана! Теперь ищи пару ❤️', reply_markup=START_SEARCH_KEYBOARD)
    
    return ConversationHandler.END

async def show_next_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    profile = get_user_profile(user_id)
    if not profile or profile[7] == 0:
        await update.message.reply_text('🔍 Чтобы просматривать анкеты других пользователей, нужно сначала активировать свою.\nЗайдите в «Настройки» → «Моя анкета» и нажмите «Возобновить показ»', reply_markup=MAIN_KEYBOARD)
        return
    prof = get_random_profile(user_id)
    if not prof:
        await update.message.reply_text('😔 Нет подходящих анкет. Пригласи друзей!', reply_markup=MAIN_KEYBOARD)
        return
    to_user_id, name, age, city, photo_id, desc, gender = prof
    gender_emoji = '♂' if gender == 'male' else '♀'
    caption = f'<b>{name}</b>, {age} лет, {gender_emoji}, {city}\n\n{desc}'
    context.user_data['current_profile_id'] = to_user_id
    await update.message.reply_photo(photo=photo_id, caption=caption, parse_mode='HTML', reply_markup=MAIN_KEYBOARD)

async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Если ConversationHandler находится в активном состоянии, не обрабатываем здесь
    # Это fallback handler, который обрабатывает только когда ConversationHandler не активен
    text = update.message.text
    user_id = update.effective_user.id
    current_id = context.user_data.get('current_profile_id')

    profile = get_user_profile(user_id)
    is_active = profile[7] if profile else 0

    if text in ['❤️', '💔'] and is_active == 0:
        await update.message.reply_text('🔍 Чтобы просматривать анкеты других пользователей, нужно сначала активировать свою.\nЗайдите в «Настройки» → «Моя анкета» и нажмите «Возобновить показ»', reply_markup=MAIN_KEYBOARD)
        return

    if text == 'Начать поиск':
        await update.message.reply_text('Поиск анкет ❤️', reply_markup=MAIN_KEYBOARD)
        await show_next_profile(update, context)
        return

    if text == '❤️':
        if not current_id:
            await show_next_profile(update, context)
            return
        reverse = check_reverse_pending(user_id, current_id)
        if reverse:
            create_match(user_id, current_id)
            super_msg = None if reverse[0] == 'like' else reverse[1]
            await send_match_notification(context.bot, user_id, current_id, super_msg)
            await send_match_notification(context.bot, current_id, user_id, super_msg)
            await update.message.reply_text('🎉 Взаимная симпатия!', reply_markup=MAIN_KEYBOARD)
            await show_next_profile(update, context)
        else:
            add_pending_action(user_id, current_id, 'like')
            await update.message.reply_text('Лайк отправлен! Ждём взаимности ❤️')
            await context.bot.send_message(current_id, 'Вы кому-то понравились, посмотрите кто это', reply_markup=LIKE_RESPONSE_KEYBOARD)
            await show_next_profile(update, context)
        return

    elif text == '💔':
        await show_next_profile(update, context)
        return

    elif text == 'Посмотреть':
        pending = get_pending_for(user_id)
        if pending and pending[1] == 'like':
            liker_id = pending[0]
            prof = get_user_profile(liker_id)
            if prof:
                name, age, gender, city, photo_id, desc, username, _ = prof
                gender_emoji = '♂' if gender == 'male' else '♀'
                caption = f'<b>{name}</b>, {age} лет, {gender_emoji}, {city}\n\n{desc}\n\nПодтвердить взаимную симпатию?'
                await update.message.reply_photo(photo=photo_id, caption=caption, parse_mode='HTML', reply_markup=CONFIRM_MATCH_KEYBOARD)
            context.user_data['pending_liker'] = liker_id
            context.user_data['pending_type'] = 'like'
        else:
            await update.message.reply_text('Нет активного лайка.', reply_markup=MAIN_KEYBOARD)
            await show_next_profile(update, context)

    elif text == '✅ Посмотреть':
        pending = get_pending_for(user_id)
        if pending and pending[1] == 'superlike':
            liker_id = pending[0]
            message = pending[2] or ''
            prof = get_user_profile(liker_id)
            if prof:
                name, age, gender, city, photo_id, desc, username, _ = prof
                gender_emoji = '♂' if gender == 'male' else '♀'
                caption = f'<b>{name}</b>, {age} лет, {gender_emoji}, {city}\n\n{desc}\n\nСообщение: {message}\n\nПодтвердить взаимную симпатию?'
                await update.message.reply_photo(photo=photo_id, caption=caption, parse_mode='HTML', reply_markup=CONFIRM_MATCH_KEYBOARD)
            context.user_data['pending_liker'] = liker_id
            context.user_data['pending_type'] = 'superlike'
            context.user_data['super_message'] = message  # Сохраняем сообщение для использования при подтверждении
        else:
            await update.message.reply_text('Нет активного суперлайка.', reply_markup=MAIN_KEYBOARD)
            await show_next_profile(update, context)

    elif text == '❌ Пропустить':
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('DELETE FROM pending_actions WHERE to_user_id = ? AND action_type = ?', (user_id, 'superlike'))
        conn.commit()
        conn.close()
        await update.message.reply_text('Суперлайк пропущен.', reply_markup=START_SEARCH_KEYBOARD)
        return

    elif text == '✅ Подтвердить симпатию':
        liker_id = context.user_data.get('pending_liker')
        pending_type = context.user_data.get('pending_type')
        if liker_id:
            # Получаем сообщение из context.user_data, если это суперлайк
            super_message = context.user_data.get('super_message') if pending_type == 'superlike' else None
            
            create_match(liker_id, user_id)
            await send_match_notification(context.bot, liker_id, user_id, super_message)
            await send_match_notification(context.bot, user_id, liker_id, super_message)
            await update.message.reply_text('🎉 Взаимная симпатия подтверждена!', reply_markup=MAIN_KEYBOARD)
            del context.user_data['pending_liker']
            del context.user_data['pending_type']
            context.user_data.pop('super_message', None)
        await show_next_profile(update, context)

    elif text == '❌ Отказаться':
        liker_id = context.user_data.get('pending_liker')
        if liker_id:
            del context.user_data['pending_liker']
            del context.user_data['pending_type']
            context.user_data.pop('super_message', None)
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('DELETE FROM pending_actions WHERE from_user_id = ? AND to_user_id = ?', (liker_id, user_id))
            conn.commit()
            conn.close()
        await update.message.reply_text('Симпатия отклонена.', reply_markup=START_SEARCH_KEYBOARD)
        return

    # Кнопка суперлайка "💌" убрана

    elif text == '⚙️':
        # Если пользователь уже в настройках или другом подменю, очищаем контекст и открываем настройки
        context.user_data.pop('in_edit_profile', None)
        settings_text = await get_settings_text(user_id)
        await update.message.reply_text(settings_text, reply_markup=await get_settings_keyboard(user_id))
        context.user_data['in_settings'] = True

    elif context.user_data.get('in_settings'):
        if text == '🔍':
            # Возврат в главное меню поиска анкет
            del context.user_data['in_settings']
            await update.message.reply_text('Возвращаемся к поиску.', reply_markup=MAIN_KEYBOARD)
            await show_next_profile(update, context)

        elif text == '👤':
            # Показываем анкету пользователя (без кнопок)
            user_id = update.effective_user.id
            profile = get_user_profile(user_id)
            
            if not profile:
                # Если анкеты нет
                await update.message.reply_text(
                    '❌ У вас пока нет анкеты. Создайте её, чтобы начать поиск.',
                    reply_markup=await get_settings_keyboard(user_id)
                )
            else:
                # Показываем анкету с фото и текстом (без кнопок)
                name, age, gender, city, photo_id, desc, username, is_active = profile
                gender_emoji = '♂' if gender == 'male' else '♀'
                
                # Формируем текст анкеты
                caption = (
                    f'👤 Имя: {name}\n'
                    f'🎂 Возраст: {age}\n'
                    f'📍 Город: {city}\n'
                    f'📝 Описание:\n{desc}'
                )
                
                # Отправляем фото с текстом (без кнопок)
                await update.message.reply_photo(
                    photo=photo_id,
                    caption=caption
                )
            
            # Пользователь остается в настройках, состояние не меняется

        elif text in ['🟰', '▶️']:
            # Возобновление/пауза анкеты
            profile = get_user_profile(user_id)
            current_active = profile[7] if profile else 0
            new_active = 0 if current_active == 1 else 1
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('UPDATE users SET is_active = ? WHERE user_id = ?', (new_active, user_id))
            conn.commit()
            conn.close()
            
            if new_active == 1:
                # Анкета возобновлена - возвращаем в главное меню
                del context.user_data['in_settings']
                await update.message.reply_text('✅ Анкета возобновлена! Теперь вас могут видеть другие пользователи.', reply_markup=MAIN_KEYBOARD)
                await show_next_profile(update, context)
            else:
                # Анкета приостановлена - остаемся в настройках
                settings_text = await get_settings_text(user_id)
                await update.message.reply_text('⏸️ Анкета приостановлена. Вас не будут видеть другие пользователи.', reply_markup=await get_settings_keyboard(user_id))

        elif text == '🗣️':
            # Приглашение друзей - просто отправляем текст, остаемся в настройках
            await update.message.reply_text(INVITE_TEXT, reply_markup=await get_settings_keyboard(user_id))
            # Пользователь остается в меню настроек, состояние не меняется

    # Убрана обработка меню "Моя анкета" - теперь кнопка "👤" просто показывает анкету без кнопок



async def superlike_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    target = context.user_data.get('super_target')
    if not target:
        await update.message.reply_text('Ошибка. Начни заново.', reply_markup=MAIN_KEYBOARD)
        return ConversationHandler.END
    message = update.message.text
    user_id = update.effective_user.id
    
    reverse = check_reverse_pending(user_id, target)
    if reverse:
        create_match(user_id, target)
        super_msg = message if reverse[0] == 'superlike' else None
        await send_match_notification(context.bot, user_id, target, super_msg)
        await send_match_notification(context.bot, target, user_id, super_msg)
        await update.message.reply_text('🎉 Суперлайк взаимный!', reply_markup=MAIN_KEYBOARD)
        await show_next_profile(update, context)
    else:
        add_pending_action(user_id, target, 'superlike', message)
        await update.message.reply_text('Сообщение отправлено, ждем взаимности', reply_markup=MAIN_KEYBOARD)
        await context.bot.send_message(target, 'Вам отправили суперлайк с сообщением! Посмотрите кто это', reply_markup=SUPER_RESPONSE_KEYBOARD)
        await show_next_profile(update, context)
    return ConversationHandler.END

async def edit_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    
    # Проверяем, что мы ожидаем фото (защита от повторной обработки)
    if not context.user_data.get('change_photo_waiting'):
        # Если флаг не установлен, значит фото уже было обработано - игнорируем
        return ConversationHandler.END
    
    # Проверяем, что это фото
    if not update.message.photo:
        # Если не фото - показываем ошибку и продолжаем ждать
        await update.message.reply_text('⚠️ Пожалуйста, отправьте именно фотографию.')
        return EDIT_PHOTO
    
    # Если пользователь отправил несколько фото в одном сообщении - берем последнее (самое большое качество)
    new_photo_id = update.message.photo[-1].file_id
    
    # Сохраняем новое фото и обновляем в базе данных
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE users SET photo_id = ? WHERE user_id = ?', (new_photo_id, user_id))
    conn.commit()
    conn.close()
    
    # Убираем флаг ожидания фото
    context.user_data.pop('change_photo_waiting', None)
    
    # ОБЯЗАТЕЛЬНО отправляем подтверждающее сообщение
    await update.message.reply_text('✅ Фото анкеты успешно обновлено.')
    
    # Показываем обновленную анкету
    profile = get_user_profile(user_id)
    if profile:
        name, age, gender, city, photo_id, desc, username, is_active = profile
        gender_emoji = '♂' if gender == 'male' else '♀'
        caption = (
            f'👤 Имя: {name}\n'
            f'🎂 Возраст: {age}\n'
            f'📍 Город: {city}\n'
            f'📝 Описание:\n{desc}'
        )
        await update.message.reply_photo(
            photo=photo_id,
            caption=caption
        )
    
    # Возвращаем пользователя в настройки
    context.user_data.pop('in_edit_profile', None)
    context.user_data['in_settings'] = True
    
    # Сбрасываем состояние после подтверждения
    return ConversationHandler.END

async def edit_desc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    
    # Проверяем, что мы ожидаем описание (защита от повторной обработки)
    if not context.user_data.get('change_description_waiting'):
        # Если флаг не установлен, значит описание уже было обработано - игнорируем
        return ConversationHandler.END
    
    # Проверяем, что это текстовое сообщение
    if not update.message.text:
        # Если не текст - показываем ошибку и продолжаем ждать
        await update.message.reply_text('⚠️ Пожалуйста, отправьте корректный текст описания.')
        return EDIT_DESC
    
    # Получаем текст описания
    new_desc = update.message.text.strip()
    
    # Валидация текста
    if not new_desc:
        # Пустое сообщение
        await update.message.reply_text('⚠️ Пожалуйста, отправьте корректный текст описания.')
        return EDIT_DESC
    
    if len(new_desc) < 10:
        # Слишком короткое описание
        await update.message.reply_text('⚠️ Пожалуйста, отправьте корректный текст описания.')
        return EDIT_DESC
    
    # Текст валиден - сохраняем новое описание
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE users SET description = ? WHERE user_id = ?', (new_desc, user_id))
    conn.commit()
    conn.close()
    
    # Убираем флаг ожидания описания
    context.user_data.pop('change_description_waiting', None)
    
    # ОБЯЗАТЕЛЬНО отправляем подтверждающее сообщение
    await update.message.reply_text('✅ Описание анкеты успешно обновлено.')
    
    # Показываем обновленную анкету
    profile = get_user_profile(user_id)
    if profile:
        name, age, gender, city, photo_id, desc, username, is_active = profile
        gender_emoji = '♂' if gender == 'male' else '♀'
        caption = (
            f'👤 Имя: {name}\n'
            f'🎂 Возраст: {age}\n'
            f'📍 Город: {city}\n'
            f'📝 Описание:\n{desc}'
        )
        await update.message.reply_photo(
            photo=photo_id,
            caption=caption
        )
    
    # Возвращаем пользователя в настройки
    context.user_data.pop('in_edit_profile', None)
    context.user_data['in_settings'] = True
    
    # Сбрасываем состояние после подтверждения
    return ConversationHandler.END

async def confirm_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    user_id = update.effective_user.id
    if text == '✅ Подтвердить':
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        if 'new_photo' in context.user_data:
            # Обновляем фото в базе данных (старое фото автоматически удаляется, так как хранится только file_id)
            c.execute('UPDATE users SET photo_id = ? WHERE user_id = ?', (context.user_data['new_photo'], user_id))
            conn.commit()
            conn.close()
            await update.message.reply_text('✅ Фото анкеты успешно обновлено!')
            # Показываем обновленную анкету
            profile = get_user_profile(user_id)
            if profile:
                name, age, gender, city, photo_id, desc, username, is_active = profile
                caption = (
                    f'👤 Имя: {name}\n'
                    f'🎂 Возраст: {age}\n'
                    f'📍 Город: {city}\n'
                    f'📝 Описание:\n{desc}'
                )
                await update.message.reply_photo(photo=photo_id, caption=caption)
        elif 'new_desc' in context.user_data:
            # Обновляем описание в базе данных
            c.execute('UPDATE users SET description = ? WHERE user_id = ?', (context.user_data['new_desc'], user_id))
            conn.commit()
            conn.close()
            await update.message.reply_text('✅ Описание анкеты обновлено!')
            # Показываем обновленную анкету
            profile = get_user_profile(user_id)
            if profile:
                name, age, gender, city, photo_id, desc, username, is_active = profile
                caption = (
                    f'👤 Имя: {name}\n'
                    f'🎂 Возраст: {age}\n'
                    f'📍 Город: {city}\n'
                    f'📝 Описание:\n{desc}'
                )
                await update.message.reply_photo(photo=photo_id, caption=caption)
        context.user_data.pop('new_photo', None)
        context.user_data.pop('new_desc', None)
    elif text == '❌ Отмена':
        context.user_data.pop('new_photo', None)
        context.user_data.pop('new_desc', None)
        await update.message.reply_text('❌ Изменение отменено.', reply_markup=await get_settings_keyboard(user_id))
        # Возвращаем в настройки
        context.user_data.pop('in_edit_profile', None)
        context.user_data['in_settings'] = True
    return ConversationHandler.END

async def confirm_delete_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    user_id = update.effective_user.id
    
    if not context.user_data.get('waiting_delete_confirm'):
        # Если не ожидаем подтверждения, возвращаем в настройки
        await update.message.reply_text('Возвращаемся в настройки.', reply_markup=await get_settings_keyboard(user_id))
        context.user_data.pop('waiting_delete_confirm', None)
        context.user_data['in_settings'] = True
        return ConversationHandler.END
    
    if text == '✅ Да':
        # ШАГ 1: Удаляем анкету из базы данных
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
        c.execute('DELETE FROM pending_actions WHERE from_user_id = ? OR to_user_id = ?', (user_id, user_id))
        c.execute('DELETE FROM matches WHERE user1_id = ? OR user2_id = ?', (user_id, user_id))
        conn.commit()
        conn.close()
        
        # ШАГ 2: Сохраняем username перед очисткой
        username = update.effective_user.username or ''
        
        # ШАГ 3: Очищаем состояние пользователя
        context.user_data.clear()
        
        # ШАГ 4: Устанавливаем флаги для нового сценария регистрации
        context.user_data['recreate'] = False
        context.user_data['username'] = username
        
        # ШАГ 5: ОБЯЗАТЕЛЬНО отправляем подтверждающее сообщение об удалении
        await update.message.reply_text('✅ Старая анкета удалена.')
        
        # ШАГ 6: НЕМЕДЛЕННО запускаем сценарий регистрации с самого начала
        await update.message.reply_text('Давайте создадим новую анкету.\nВведи имя:', reply_markup=ReplyKeyboardRemove())
        
        # ВАЖНО: Возвращаем состояние NAME для начала регистрации
        return NAME
        
    elif text == '❌ Отмена':
        # Отменяем удаление, возвращаемся в настройки
        context.user_data.pop('waiting_delete_confirm', None)
        await update.message.reply_text('Создание анкеты отменено.', reply_markup=await get_settings_keyboard(user_id))
        context.user_data['in_settings'] = True
        return ConversationHandler.END
    else:
        # Неизвестная команда - остаемся в состоянии подтверждения
        await update.message.reply_text('Пожалуйста, выберите "✅ Да" или "❌ Отмена"', reply_markup=CONFIRM_DELETE_KEYBOARD)
        return CONFIRM_DELETE
