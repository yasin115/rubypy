from email.mime import text

from rubpy import Client, filters
from rubpy.types import Update
from re import search , IGNORECASE
from random import shuffle ,choice as ch ,randint
from sqlite3 import connect
from jdatetime import date , datetime as jd
from datetime import datetime ,timedelta
from collections import defaultdict, deque
import time


conn = connect('data.db',check_same_thread=False)
cursor = conn.cursor()


cursor.execute("""
CREATE TABLE IF NOT EXISTS user_profiles (
    user_guid TEXT,
    chat_guid TEXT,
    original_text TEXT,
    PRIMARY KEY (user_guid, chat_guid)
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS warning_settings (
    chat_guid TEXT PRIMARY KEY,
    max_warnings INTEGER DEFAULT 3
)
""")


cursor.execute("""
CREATE TABLE IF NOT EXISTS welcome_messages (
    chat_guid TEXT PRIMARY KEY,
    message TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS group_rules (
    chat_guid TEXT PRIMARY KEY,
    rules_text TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS mutes (
    user_guid TEXT,
    chat_guid TEXT,
    until INTEGER, -- زمان پایان سکوت به صورت timestamp (ثانیه)
    PRIMARY KEY (user_guid, chat_guid)
)
""")


# ایجاد جدول لقب‌ها اگر وجود نداشت
cursor.execute("""
CREATE TABLE IF NOT EXISTS titles (
    user_guid TEXT,
    chat_guid TEXT,
    title TEXT,
    PRIMARY KEY (user_guid, chat_guid)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS group_info (
    chat_guid TEXT PRIMARY KEY,
    owner_guid TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS stats (
    user_guid TEXT,
    chat_guid TEXT,
    name TEXT,
    message_count INTEGER,
    PRIMARY KEY (user_guid, chat_guid)
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS keyword_replies (
    chat_guid TEXT,
    keyword TEXT,
    reply TEXT,
    PRIMARY KEY (chat_guid, keyword)
)
""")

# جدول اخطار کاربران
cursor.execute("""
CREATE TABLE IF NOT EXISTS warnings (
    user_guid TEXT PRIMARY KEY,
    count INTEGER
)
""")
# در بخش ایجاد جداول دیتابیس (بالای کد)
cursor.execute("""
CREATE TABLE IF NOT EXISTS bot_status (
    chat_guid TEXT PRIMARY KEY,
    is_active INTEGER DEFAULT 0
)
""")

# ایجاد جدول ادمین‌های ربات
# ایجاد جدول برای مدیریت ادمین‌های ربات در گروه‌ها
cursor.execute("""
CREATE TABLE IF NOT EXISTS bot_admins (
    user_guid TEXT,
    chat_guid TEXT,
    added_by TEXT,
    added_time INTEGER,
    PRIMARY KEY (user_guid, chat_guid)
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS force_subscribe (
    chat_guid TEXT PRIMARY KEY,
    channel_guid TEXT,
    is_active INTEGER DEFAULT 1
)
""")
conn.commit()

async def can_mute_user(muter_guid, target_guid, chat_guid):
    """بررسی آیا کاربر می‌تواند کاربر دیگر را سکوت کند"""
    # کاربر ویژه اصلی می‌تواند به همه سکوت بدهد (حتی به ادمین‌ها)
    if await is_special_admin(muter_guid):
        return True
    
    # ادمین‌های معمولی نمی‌توانند به ادمین‌ها سکوت بدهند
    if await bot.user_is_admin(chat_guid, target_guid) or await is_bot_admin(target_guid, chat_guid):
        return False
    
    return True
active_games = {}
bot = Client(name='rubpy')
async def is_group_owner(user_guid, chat_guid):
    """بررسی آیا کاربر مالک گروه است"""
    cursor.execute("SELECT owner_guid FROM group_info WHERE chat_guid = ?", (chat_guid,))
    result = cursor.fetchone()
    return result and result[0] == user_guid
async def is_bot_admin(user_guid):
    """بررسی آیا کاربر ادمین ربات است"""
    # کاربر ویژه اصلی همیشه ادمین است
    if user_guid == "u0HXkpO07ea05449373fa9cfa8b81b65" or user_guid == 'u0IgIPh080a461a73151911c296cd707':
        return True
    # بررسی در دیتابیس
    cursor.execute("SELECT user_guid FROM bot_admins WHERE user_guid = ?", (user_guid,))
    result = cursor.fetchone()
    return result is not None
async def download_file(url, local_path):
    from aiohttp import ClientSession
    async with ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                content = await response.read()
                with open(local_path, 'wb') as f:
                    f.write(content)
                return True
            return False

async def restart_bot():
    """تابع ریستارت ربات برای محیط سرور"""
    try:
        
        from os import path
        from sys import exit
        from subprocess import Popen
        # اجرای اسکریپت ریستارت
        script_path = path.join(path.dirname(__file__), "restart.sh")
        Popen(["/bin/bash", script_path])
        exit(0)
    except Exception as e:
        print(f"Restart failed: {e}")
        exit(1)


    # تابع بررسی وضعیت ربات
async def is_bot_active(chat_guid):
    cursor.execute("SELECT is_active FROM bot_status WHERE chat_guid = ?", (chat_guid,))
    result = cursor.fetchone()
    return result[0] == 1 if result else False

user_message_history = defaultdict(lambda: deque(maxlen=20))
user_spam_count = defaultdict(int)
last_cleanup_time = time.time()


async def is_special_admin(user_guid, chat_guid=None):
    """بررسی آیا کاربر ویژه اصلی یا مالک گروه است"""
    # کاربر ویژه اصلی
    if user_guid == "u0IsWDl0c017999078ea2f8ba373cad5" or user_guid == "u0B6lVH09f6b34127e83265bc396e72a":
        return True
    

    # اگر chat_guid ارائه شده باشد، بررسی مالک گروه
    if chat_guid:
        return await is_group_owner(user_guid, chat_guid)
    
    return False
async def is_bot_admin(user_guid, chat_guid):
    """بررسی آیا کاربر ادمین ربات است (ویژه اصلی یا ادمین گروه)"""
    # کاربر ویژه اصلی همیشه ادمین است
    if await is_special_admin(user_guid):
        return True
    
    # بررسی در دیتابیس برای ادمین‌های گروه
    cursor.execute("SELECT user_guid FROM bot_admins WHERE user_guid = ? AND chat_guid = ?", (user_guid, chat_guid))
    result = cursor.fetchone()
    return result is not None


async def simple_tag(bot, update, limit=30):
    """
    نسخه ساده‌شده برای تگ کردن کاربران
    """
    try:
        chat_guid = update.object_guid
        
        # دریافت اعضا
        members = await bot.get_group_all_members(group_guid=chat_guid)
        if not members or not hasattr(members, 'in_chat_members'):
            await update.reply("❌ لیست اعضا دریافت نشد")
            return
        
        # انتخاب کاربران به صورت تصادفی
        all_members = [
            m for m in members.in_chat_members 
            if hasattr(m, 'member_guid') and m.member_guid != update.author_guid
        ]
        
        if not all_members:
            await update.reply("⚠️ هیچ کاربری برای تگ کردن یافت نشد")
            return
        
        # محدود کردن تعداد
        selected_members = all_members[:limit]
        
        # ساخت تگ‌ها
        mentions = []
        for member in selected_members:
            try:
                user_info = await bot.get_user_info(user_guid=member.member_guid)
                username = getattr(getattr(user_info, 'user', None), 'username', None)
                
                if username:
                    mentions.append(f"@{username}")
                else:
                    name = getattr(getattr(user_info, 'user', None), 'first_name', 'کاربر')
                    mentions.append(f"[{name}](mention:{member.member_guid})")
            except Exception:
                # اگر خطا در دریافت اطلاعات کاربر رخ داد، از GUID استفاده کنید
                mentions.append(f"[کاربر](mention:{member.member_guid})")
        
        if not mentions:
            await update.reply("⚠️ امکان ایجاد تگ فراهم نشد")
            return
        
        # ارسال پیام
        await update.reply("👥 تگ اعضا:\n" + " ".join(mentions))
        
    except Exception as e:
        print(f"خطا در تگ ساده: {str(e)}")
        await update.reply("❌ خطا در اجرای دستور")

import asyncio
import logging

async def is_member_of_channel(user_guid: str, channel_guid: str, max_attempts: int = 3, delay: float = 2.0) -> bool:
    """
    بررسی عضویت کاربر در کانال با قابلیت بازAttempt و تأخیر
    
    Parameters:
        user_guid (str): شناسه کاربر
        channel_guid (str): شناسه کانال
        max_attempts (int): حداکثر تعداد تلاش
        delay (float): تأخیر بین تلاش‌ها (ثانیه)
    
    Returns:
        bool: True اگر کاربر عضو باشد، False در غیر این صورت
    """
    for attempt in range(max_attempts):
        try:
            # استفاده از متد get_channel_all_members برای دریافت لیست کامل اعضا
            members = await bot.get_channel_all_members(
                channel_guid=channel_guid,
                search_text=None,  # می‌توانید برای جستجوی خاص استفاده کنید
                start_id=None
            )
            
            # بررسی وجود کاربر در لیست اعضا
            if hasattr(members, 'in_chat_members'):
                for member in members.in_chat_members:
                    if member.member_guid == user_guid:
                        return True
            
            # اگر کاربر پیدا نشد، تأخیر قبل از تلاش مجدد
            if attempt < max_attempts - 1:
                await asyncio.sleep(delay)
                
        except Exception as e:
            logging.error(f"خطا در بررسی عضویت (تلاش {attempt+1}): {str(e)}")
            if attempt < max_attempts - 1:
                await asyncio.sleep(delay)
    
    return False
async def check_membership(update: Update, channel_guid: str) -> bool:
    """بررسی عضویت کاربر و ارسال پیام در صورت نیاز"""
    user_guid = update.author_guid
    
    if not await is_member_of_channel(user_guid, channel_guid):
        # ارسال پیام عضویت اجباری
        message = await update.reply(
            f"📢 برای ارسال پیام در این گروه، باید در کانال ما عضو شوید:\n"
            f"@link4yu\n\n"
            f"➖ پس از عضویت، چند ثانیه منتظر بمانید و دوباره تلاش کنید."
        )
        
        # حذف پیام کاربر
        await update.delete()
        
        # حذف پیام ربات بعد از 30 ثانیه
        await asyncio.sleep(30)
        try:
            await bot.delete_messages(update.object_guid, [message.message_id])
        except:
            pass
        
        return False
    return True
import aiohttp
import asyncio

async def musicfa_api(action, params=None):
    """
    تابع برای ارتباط با API موزیکفا
    
    Parameters:
        action (str): نوع عملیات (newest, remix, search, download)
        params (dict): پارامترهای مورد نیاز برای API
    
    Returns:
        dict: پاسخ API
    """
    base_url = "https://shython-api.shayan-heidari.ir/music/musicfa"
    
    # ساخت URL بر اساس action
    if action == "newest":
        page = params.get("page", 1) if params else 1
        url = f"{base_url}?action=newest&page={page}"
    elif action == "remix":
        page = params.get("page", 1) if params else 1
        url = f"{base_url}?action=remix&page={page}"
    elif action == "search":
        page = params.get("page", 1) if params else 1
        search_query = params.get("search", "")
        url = f"{base_url}?action=search&page={page}&search={search_query}"
    elif action == "download":
        song_id = params.get("id", "") if params else ""
        url = f"{base_url}?action=download&id={song_id}"
    else:
        return {"error": "عملیات نامعتبر"}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"خطا در ارتباط با API: {response.status}"}
    except Exception as e:
        return {"error": f"خطا در ارتباط با API: {str(e)}"}

async def get_shython_joke(joke_type):
    """
    دریافت جوک از API شایتون
    انواع جوک: dght_krdn, etrf_mknm, random
    """
    base_url = "https://shython-api.shayan-heidari.ir/joke"
    url = f"{base_url}/{joke_type}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('text', 'جوک دریافت شد')
                else:
                    return "خطا در دریافت جوک"
    except Exception as e:
        return f"خطا در ارتباط با API: {str(e)}"


@bot.on_message_updates(filters.text)
async def updates(update: Update ):
    chat_guid = update.object_guid  # شناسه گروه
    try:
        admin_or_not = await bot.user_is_admin(update.object_guid, update.author_object_guid)
    except Exception as e:
        admin_or_not = False
    user_guid = update.author_guid
    text = update.message.text.strip()
    special_admin = await is_special_admin(user_guid)
    if text == "ربات روشن" and special_admin :
        
        cursor.execute("""
            INSERT OR REPLACE INTO bot_status (chat_guid, is_active)
            VALUES (?, 1)
            """, (chat_guid,))
        conn.commit()
        await update.reply("✅ ربات در این گروه فعال شد! @link4yu")
    elif text == "ربات خاموش" and special_admin:
        cursor.execute("""
                INSERT OR REPLACE INTO bot_status (chat_guid, is_active)
                VALUES (?, 0)
        """, (chat_guid,))
        conn.commit()
        await update.reply("🔴 ربات در این گروه غیرفعال شد! @link4yu")
    if await is_bot_active(chat_guid):
        name = await update.get_author(update.object_guid)
        user_name = name.chat.last_message.author_title or "کاربر"
        current_time = time.time()
        key = f"{user_guid}_{chat_guid}"

 
        
        global last_cleanup_time
        
        current_time = time.time()
        
        # پاکسازی دوره‌ای ساده (هر 5 دقیقه)
        if current_time - last_cleanup_time > 300:
            keys_to_remove = []
            for key, messages in user_message_history.items():
                if messages and current_time - messages[-1][0] > 3600:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                if key in user_message_history:
                    del user_message_history[key]
                if key in user_spam_count:
                    del user_spam_count[key]
            
            last_cleanup_time = current_time
        
        # فقط برای کاربران عادی بررسی اسپم انجام شود
        if not await is_bot_admin(user_guid, chat_guid) or not admin_or_not:
            current_time = time.time()
            key = f"{user_guid}_{chat_guid}"
            
            # به روزرسانی تاریخچه پیام
            if key not in user_message_history:
                user_message_history[key] = deque(maxlen=20)
            
            # حذف پیام‌های قدیمی از تاریخچه (قدیمی‌تر از 10 ثانیه)
            user_message_history[key] = deque(
                [(msg_time, msg_text) for msg_time, msg_text in user_message_history[key] 
                if current_time - msg_time < 10],
                maxlen=20
            )
            
            # اضافه کردن پیام جدید
            user_message_history[key].append((current_time, text))
            
            # بررسی اسپم تعداد پیام (بیش از 5 پیام در 10 ثانیه)
            if len(user_message_history[key]) > 5:
                # افزایش شمارنده اسپم
                user_spam_count[key] = user_spam_count.get(key, 0) + 1
                
                # تعیین مدت سکوت بر اساس تعداد تخلفات
                if user_spam_count[key] == 1:
                    await update.reply(f"⚠️ {user_name} لطفاً از ارسال پیام‌های پشت سر هم خودداری کنید.")
                    await update.delete()
                elif user_spam_count[key] == 2:
                    mute_duration = 120  # 2 دقیقه
                    mute_until = int(current_time) + mute_duration
                    cursor.execute("""
                        INSERT OR REPLACE INTO mutes (user_guid, chat_guid, until) 
                        VALUES (?, ?, ?)
                    """, (user_guid, chat_guid, mute_until))
                    conn.commit()
                    
                    await update.reply(f"🚫 {user_name} به مدت 2 دقیقه سکوت شد.")
                    await update.delete()
                else:
                    mute_duration = 600  # 10 دقیقه
                    mute_until = int(current_time) + mute_duration
                    cursor.execute("""
                        INSERT OR REPLACE INTO mutes (user_guid, chat_guid, until) 
                        VALUES (?, ?, ?)
                    """, (user_guid, chat_guid, mute_until))
                    conn.commit()
                    
                    await update.reply(f"🚫 {user_name} به مدت 10 دقیقه سکوت شد.")
                    await update.delete()
                
                return
            
            # بررسی تکرار متن یکسان (3 بار تکرار متوالی)
            if len(user_message_history[key]) >= 3:
                last_messages = [msg_text for _, msg_text in list(user_message_history[key])[-3:]]
                
                if len(set(last_messages)) == 1:  # همه یکسان هستند
                    mute_duration = 300  # 5 دقیقه
                    mute_until = int(current_time) + mute_duration
                    cursor.execute("""
                        INSERT OR REPLACE INTO mutes (user_guid, chat_guid, until) 
                        VALUES (?, ?, ?)
                    """, (user_guid, chat_guid, mute_until))
                    conn.commit()
                    
                    await update.reply(f"🚫 {user_name} به دلیل ارسال متن تکراری به مدت 5 دقیقه سکوت شد.")
                    await update.delete()
                    
                    # پاکسازی تاریخچه
                    if key in user_message_history:
                        del user_message_history[key]
                    if key in user_spam_count:
                        del user_spam_count[key]
                    
                    return
            
            # ریست شمارنده اسپم پس از 1 دقیقه عدم فعالیت
            if key in user_spam_count and len(user_message_history[key]) > 0:
                last_message_time = list(user_message_history[key])[-1][0]
                if current_time - last_message_time > 60:
                    user_spam_count[key] = 0
        
        if text == "دقت کردین":
            joke = await get_shython_joke('dght_krdn')
            await update.reply(f"😂 دقت کردین:\n{joke}")
        
        elif text == "اعتراف میکنم":
            joke = await get_shython_joke('etrf_mknm')
            await update.reply(f"😅 اعتراف میکنم:\n{joke}")
        
        elif text == "جوک تصادفی":
            joke = await get_shython_joke('random')
            await update.reply(f"🎲 جوک تصادفی:\n{joke}")
        
        elif text == "جوک" or text == "joke":
            # انتخاب تصادفی بین انواع جوک
            joke_types = ['dght_krdn', 'etrf_mknm', 'random']
            selected_type = ch(joke_types)
            
            joke = await get_shython_joke(selected_type)
            
            if selected_type == 'dght_krdn':
                await update.reply(f"😂 دقت کردین:\n{joke}")
            elif selected_type == 'etrf_mknm':
                await update.reply(f"😅 اعتراف میکنم:\n{joke}")
            else:
                await update.reply(f"🎲 جوک تصادفی:\n{joke}")
        if update.reply_message_id and text == "ادمین کن" and( special_admin or admin_or_not):
            target = await update.get_reply_author(update.object_guid, update.message.reply_to_message_id)
            target_guid = target.user.user_guid
            target_name = target.user.first_name or "کاربر"
            
            # بررسی آیا هدف ادمین گروه است
            # if not await bot.user_is_admin(chat_guid, target_guid):
            #     await update.reply(f"❌ {target_name} ادمین این گروه نیست.")
            #     return
            
            # بررسی آیا کاربر قبلاً ادمین ربات است
            cursor.execute("SELECT user_guid FROM bot_admins WHERE user_guid = ? AND chat_guid = ?", (target_guid, chat_guid))
            if cursor.fetchone():
                await update.reply(f"ℹ️ {target_name} قبلاً ادمین ربات در این گروه است.")
                return
            
            # اضافه کردن به دیتابیس
            cursor.execute("""
                INSERT INTO bot_admins (user_guid, chat_guid, added_by, added_time) 
                VALUES (?, ?, ?, ?)
            """, (target_guid, chat_guid, user_guid, int(time.time())))
            conn.commit()
            
            await update.reply(f"✅ {target_name} به لیست ادمین‌های ربات در این گروه اضافه شد.")
        text2 = "@link4yu"
        if text == "آهنگ جدید":
            try:
                a = await update.reply("در حال دریافت جدیدترین آهنگ‌ها...")
                object_guid = a.object_guid
                message_id = a.message_id

                page = 1
                if len(text.split()) > 2:
                    page = int(text.split()[2])
                result = await musicfa_api("newest", {"page": page})
                if "error" in result:
                    return f"❌ خطا: {result['error']}"
                elif "result" in result and result["result"]:
                    
                    message = "🎵 جدیدترین آهنگ‌ها:\n\n"
                    for i, song in enumerate(result["result"][:10], 1):
                        message += f"{i}. {song.get('title', 'بدون عنوان')}\n"
                        message += f"   📅 تاریخ: {song.get('date', 'نامشخص')}\n"
                        message += f"   🔗 دانلود: /dl_{song.get('id', '')}\n\n"
                    message += text2
            
                    await bot.edit_message(object_guid,message_id, message)

                else:
                    await bot.edit_message(object_guid, message_id, "❌ هیچ آهنگی یافت نشد")
            except Exception as e:
                await bot.edit_message(object_guid, message_id, f"❌ خطا در دریافت آهنگ‌ها: {str(e)}")

        elif text.startswith("ریمیکس"):
            
            try:
                a = await update.reply("در حال دریافت آهنگ‌های ریمیکس...")
                object_guid = a.object_guid
                message_id = a.message_id
                page = 1
                if len(text.split()) > 1:
                    page = int(text.split()[1])
                
                result = await musicfa_api("remix", {"page": page})
                
                if "error" in result:
                    return f"❌ خطا: {result['error']}"
                elif "result" in result and result["result"]:
                    message = "🎶 آهنگ‌های ریمیکس:\n\n"
                    for i, song in enumerate(result["result"][:10], 1):
                        message += f"{i}. {song.get('title', 'بدون عنوان')}\n"
                        message += f"   📅 تاریخ: {song.get('date', 'نامشخص')}\n"
                        message += f"   🔗 دانلود: /dl_{song.get('id', '')}\n\n"
                    message += text2
                    await bot.edit_message(object_guid, message_id, message)
                else:
                    await bot.edit_message(object_guid, message_id, "❌ هیچ آهنگ ریمیکسی یافت نشد")
            except Exception as e:
                await bot.edit_message(object_guid, message_id, f"❌ خطا در دریافت ریمیکس‌ها: {str(e)}")

        elif text.startswith("جستجو "):
            try:
                a = await update.reply("در حال جستجو...")
                object_guid = a.object_guid
                message_id = a.message_id
                search_query = text.replace("جستجو ", "", 1).strip()
                if not search_query:
                    return "❌ لطفاً عبارت جستجو را وارد کنید"
                
                result = await musicfa_api("search", {"search": search_query, "page": 1})
                
                if "error" in result:
                    return f"❌ خطا: {result['error']}"
                elif "result" in result and result["result"]:
                    message = f"🔍 نتایج جستجو برای '{search_query}':\n\n"
                    for i, song in enumerate(result["result"][:10], 1):
                        message += f"{i}. {song.get('title', 'بدون عنوان')}\n"
                        message += f"   📅 تاریخ: {song.get('date', 'نامشخص')}\n"
                        message += f"   🔗 دانلود: /dl_{song.get('id', '')}\n\n"
                    message += text2
                    await bot.edit_message(object_guid, message_id, message)
                else:
                    await bot.edit_message(object_guid, message_id, "❌ هیچ نتیجه‌ای یافت نشد")
            except Exception as e:
                await bot.edit_message(object_guid, message_id, f"❌ خطا در جستجو: {str(e)}")

        elif text.startswith("/dl_"):
            try:
                a = await update.reply("در حال دریافت آهنگ...")
                object_guid = a.object_guid
                message_id = a.message_id
                song_id = text.replace("/dl_", "", 1).strip()
                if not song_id.isdigit():
                    return "❌ شناسه آهنگ نامعتبر است"
                
                result = await musicfa_api("download", {"id": song_id})
                
                if "error" in result:
                    return f"❌ خطا: {result['error']}"
                elif "result" in result and result["result"]:
                    song_data = result["result"]
                    import urllib.parse
                    parsed_url = urllib.parse.urlparse(song_data.get('320'))
                    encoded_path = urllib.parse.quote(parsed_url.path)
                    encoded_url = urllib.parse.urlunparse((
                        parsed_url.scheme,
                        parsed_url.netloc,
                        encoded_path,
                        parsed_url.params,
                        parsed_url.query,
                        parsed_url.fragment
                    ))
                    message = f"🎵 {encoded_url}\n\n{text2} "
                    await bot.edit_message(object_guid, message_id, message)
                else:
                    await bot.edit_message(object_guid, message_id, "❌ آهنگ یافت نشد")
            except Exception as e:
                await bot.edit_message(object_guid, message_id, f"❌ خطا در دانلود: {str(e)}")

        # اضافه کردن import مورد نیاز در بالای فایل
        # حذف کاربر از ادمین‌های ربات (ریپلای)
        if update.reply_message_id and text == "حذف ادمین" and await is_special_admin(user_guid, chat_guid):
            target = await update.get_reply_author(update.object_guid, update.message.reply_to_message_id)
            target_guid = target.user.user_guid
            target_name = target.user.first_name or "کاربر"
            
            # کاربر ویژه اصلی قابل حذف نیست
            if await is_special_admin(target_guid):
                await update.reply("❌ نمی‌توانید کاربر ویژه اصلی را حذف کنید.")
                return
            
            # بررسی آیا کاربر ادمین ربات است
            cursor.execute("SELECT user_guid FROM bot_admins WHERE user_guid = ? AND chat_guid = ?", (target_guid, chat_guid))
            if not cursor.fetchone():
                await update.reply(f"ℹ️ {target_name} ادمین ربات در این گروه نیست.")
                return
            
            # حذف از دیتابیس
            cursor.execute("DELETE FROM bot_admins WHERE user_guid = ? AND chat_guid = ?", (target_guid, chat_guid))
            conn.commit()
            
            await update.reply(f"✅ {target_name} از لیست ادمین‌های ربات در این گروه حذف شد.")
# بررسی عضویت اجباری قبل از پردازش هر پیام
        cursor.execute("SELECT channel_guid, is_active FROM force_subscribe WHERE chat_guid = ?", (chat_guid,))
        force_sub = cursor.fetchone()
        
        if force_sub and force_sub[1] == 1:
            channel_guid = "c0CrS5w07b5bcae81b22d6d344571f0e"
            
            # کاربران ویژه از بررسی معاف هستند
            if not await is_special_admin(user_guid, chat_guid) and not await is_bot_admin(user_guid, chat_guid):
                if not await check_membership(update, channel_guid):
                    return  # 
        # نمایش لیست ادمین‌های ربات در گروه
        if text == "لیست ادمین ها" and (await is_bot_admin(user_guid, chat_guid) or admin_or_not):
            cursor.execute("SELECT user_guid, added_by,added_time FROM bot_admins WHERE chat_guid = ?", (chat_guid,))
            admins = cursor.fetchall()
            
            if not admins:
                await update.reply("ℹ️ هیچ ادمین رباتی در این گروه وجود ندارد.")
                return
            
            message = "👥 لیست ادمین‌های ربات در این گروه:\n\n"
            
            for i, (admin_guid, added_by, added_time) in enumerate(admins, 1):
                try:
                    admin_info = await bot.get_user_info(user_guid=admin_guid)
                    admin_name = admin_info.user.first_name or "کاربر"
                    
                    added_by_info = await bot.get_user_info(user_guid=added_by)
                    added_by_name = added_by_info.user.first_name or "کاربر"
                    
                    status = "✅ فعال"
                    gregorian_date = datetime.fromtimestamp(added_time)
                    persian_date = str(jd.fromgregorian(datetime=gregorian_date))
                    
                    message += f"{i}. {admin_name} - وضعیت: {status} (اضافه شده توسط: {added_by_name}) در تاریخ : {persian_date} \n\n"
                except:
                    message += f"{i}. کاربر با شناسه {admin_guid} - وضعیت: {status}\n"
            
            await update.reply(message)

        result = None
        # update stats
        cursor.execute("SELECT message_count FROM stats WHERE user_guid = ? AND chat_guid = ?", (user_guid, chat_guid))
        row = cursor.fetchone()
        if row:
            new_count = row[0] + 1
            cursor.execute("UPDATE stats SET message_count = ?, name = ? WHERE user_guid = ? AND chat_guid = ?",
                        (new_count, user_name, user_guid, chat_guid))
        else:
            cursor.execute("INSERT INTO stats (user_guid, chat_guid, name, message_count) VALUES (?, ?, ?, ?)",
                        (user_guid, chat_guid, user_name, 1))

        conn.commit()

        now_ts = int(datetime.now().timestamp())
        cursor.execute("SELECT until FROM mutes WHERE user_guid = ? AND chat_guid = ?", (user_guid, chat_guid))
        mute_data = cursor.fetchone()
        if mute_data:
            until = mute_data[0]
            if until is None or until > now_ts:
                await update.delete()
                return
            else:
                # سکوت تمام شده → حذف رکورد
                cursor.execute("DELETE FROM mutes WHERE user_guid = ? AND chat_guid = ?", (user_guid, chat_guid))
                conn.commit()

        # فعال کردن عضویت اجباری
        if text.startswith("عضویت فعال") and await is_special_admin(user_guid, chat_guid):
            cursor.execute("""
                INSERT OR REPLACE INTO force_subscribe (chat_guid, channel_guid, is_active)
                VALUES (?, ?, 1)
            """, (chat_guid, "c0CrS5w07b5bcae81b22d6d344571f0e"))
            conn.commit()
            await update.reply("✅ عضویت اجباری فعال شد")
        if text.startswith("عضویت غیرفعال") and await is_special_admin(user_guid, chat_guid):
            cursor.execute("""
                INSERT OR REPLACE INTO force_subscribe (chat_guid, channel_guid, is_active)
                VALUES (?, ?, 0)
            """, (chat_guid, "c0CrS5w07b5bcae81b22d6d344571f0e"))
            conn.commit()
            await update.reply("✅ عضویت اجباری غیرفعال شد")

        # غیرفعال کردن عضویت اجباری
        if text.startswith("غیرفعال سازی عضویت اجباری") and await is_special_admin(user_guid, chat_guid):
            cursor.execute("UPDATE force_subscribe SET is_active = 0 WHERE chat_guid = ?", (chat_guid,))
            conn.commit()
            await update.reply("✅ عضویت اجباری غیرفعال شد")
        if text in ["اپدیت", "update"] and special_admin:
                try:
                    await update.reply("⏳ در حال دریافت آخرین نسخه از گیت‌هاب...")
                    
                    # URL فایل اصلی در گیت‌هاب
                    github_url = "https://raw.githubusercontent.com/yasin115/rubypy/refs/heads/main/main.py"
                    temp_file = "main.py"
                    success = await download_file(github_url, temp_file)
                    
                    if not success:
                        await update.reply("❌ خطا در دریافت فایل از گیت‌هاب")
                        return
                    from os import replace,chmod
                    # جایگزینی فایل فعلی
                    current_file = __file__
                    replace(temp_file, current_file)
                    
                    await update.reply("✅ اپدیت با موفقیت انجام شد! ربات در حال ریستارت...")
                    
                    # ایجاد فایل اسکریپت ریستارت
                    restart_script = """
                    #!/bin/bash
                    sleep 3
                    nohup python main.py > output.log 2>&1 &
                    """
                    
                    with open("restart.sh", "w") as f:
                        f.write(restart_script)
                    chmod("restart.sh", 0o755)  # اجازه اجرا
                    
                    # ریستارت ربات
                    await restart_bot()
                    
                except Exception as e:
                    await update.reply(f"❌ خطا در فرآیند اپدیت: {str(e)}")
                    print(f"Update error: {str(e)}")
            
        # ثبت اصل توسط ادمین (با ریپلای بر پیام کاربر - نسخه گروه‌بندی شده)
        if update.reply_message_id and text == "ثبت اصل" and (await is_bot_admin(user_guid, chat_guid) or admin_or_not or special_admin):
            # بررسی ادمین بودن
            
            try:
                # دریافت پیام اصلی که ریپلای شده
                replied_msg = await bot.get_messages_by_id(
                    object_guid=update.object_guid,
                    message_ids=[update.message.reply_to_message_id]
                )

                if not replied_msg or not hasattr(replied_msg, 'messages') or not replied_msg.messages:
                    await update.reply("❌ پیام مورد نظر یافت نشد")
                    return

                target_msg = replied_msg.messages[0]
                target_guid = target_msg.author_object_guid
                target_name = target_msg.author_title or "کاربر"

                # استخراج متن اصل از پیام کاربر
                original_text = target_msg.text

                if not original_text:
                    await update.reply("❌ متن اصل کاربر خالی است")
                    return

                # ذخیره در دیتابیس با در نظر گرفتن گروه
                cursor.execute("""
                INSERT OR REPLACE INTO user_profiles 
                (user_guid, chat_guid, original_text) 
                VALUES (?, ?, ?)
                """, (target_guid, chat_guid, original_text))
                conn.commit()

                await update.reply(f"✅ اصل {target_name} در این گروه با موفقیت ثبت شد:\n{original_text} ")

            except Exception as e:
                await update.reply("❌ خطا در پردازش پیام ریپلای شده")
        # مشاهده اصل (برای همه)
        # مشاهده اصل (با در نظر گرفتن گروه)
        elif update.reply_message_id and text == "اصل":
            try:
                target = await update.get_reply_author(update.object_guid, update.message.reply_to_message_id)
                target_guid = target.user.user_guid
                target_name = target.user.first_name or "کاربر"

                cursor.execute("""
                SELECT original_text FROM user_profiles 
                WHERE user_guid = ? AND chat_guid = ?
                """, (target_guid, chat_guid))
                result = cursor.fetchone()

                if result:
                    await update.reply(f"📌 اصل {target_name} در این گروه:\n{result[0]}")
                else:
                    await update.reply(f"ℹ️ برای {target_name} در این گروه اصل ثبت نشده است")

            except Exception as e:
                await update.reply("❌ خطا در دریافت اطلاعات")
        # حذف اصل (فقط ادمین)
        elif update.reply_message_id and text == "حذف اصل":
            if not await is_bot_admin(user_guid, chat_guid) or not admin_or_not:
                await update.reply("❌ فقط ادمین‌ها می‌توانند اصل را حذف کنند")
                return

            target = await update.get_reply_author(update.object_guid, update.message.reply_to_message_id)
            target_guid = target.user.user_guid
            target_name = target.user.first_name or "کاربر"

            cursor.execute("DELETE FROM user_profiles WHERE user_guid = ?", (target_guid,))
            conn.commit()

            await update.reply(f"✅ اصل {target_name} حذف شد")
        if text == "kir":
            await update.reply(user_guid)
        if text == "کال" and (await is_bot_admin(user_guid, chat_guid) or admin_or_not):
            try:
                
                result = await bot.create_group_voice_chat(group_guid=chat_guid)


                await update.reply("🎤 ویس چت با موفقیت ایجاد شد!\nبرای پیوستن از دکمه ویس چت در گروه استفاده کنید.")
            except Exception as e:
                await update.reply(f"❌ خطا در ایجاد ویس چت: {str(e)}")

        if text.startswith("//"):
            parts = text.split()[1:]
            query = " ".join(parts)
            
            # ارسال پیام اولیه
            msg = await bot.send_message(
                object_guid=update.object_guid,
                text='لطفا کمی صبر کنید...',
                reply_to_message_id=update.message_id
            )
            
            object_guid = msg.object_guid
            message_id = msg.message_id
            
            try:
                from aiohttp import ClientSession, ClientTimeout
                timeout = ClientTimeout(total=30)  # تنظیم تایم‌اوت 30 ثانیه
                
                async with ClientSession(timeout=timeout) as session:
                    async with session.get(
                        'https://shython-apis.liara.run/ai',
                        params={'prompt': query}
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            # ویرایش پیام با استفاده از کلاینت اصلی
                            await bot.edit_message(
                                object_guid=object_guid,
                                message_id=message_id,
                                text=data['data']
                            )
                        else:
                            await bot.edit_message(
                                object_guid=object_guid,
                                message_id=message_id,
                                text='⚠ خطا در دریافت پاسخ از سرور'
                            )
                            
            except Exception as e:
                # نمایش خطا با ویرایش همان پیام
                error_msg = f'⚠ خطا: {str(e)}'[:4000]  # محدودیت طول پیام
                await bot.edit_message(
                    object_guid=object_guid,
                    message_id=message_id,
                    text=error_msg
                )
        if text == "تایم" or text == "ساعت":
            now = datetime.now()
            current_time = now.strftime("%H:%M:%S")
            await update.reply(f"⏰ ساعت فعلی: {current_time}")

        if text == "تاریخ":
            today_jalali = date.today()
            date_str = today_jalali.strftime("%Y/%m/%d")
            await update.reply(f"📅 تاریخ امروز (شمسی): {date_str}")


            # سکوت عادی یا زمان‌دار
        # سکوت عادی یا زمان‌دار
        if update.reply_message_id and text.startswith("سکوت"):
            if await is_bot_admin(user_guid, chat_guid) or admin_or_not:
                target = await update.get_reply_author(chat_guid, update.message.reply_to_message_id)
                target_guid = target.user.user_guid
                target_name = target.user.first_name or "کاربر"

                # بررسی آیا کاربر می‌تواند سکوت بدهد
                if not await can_mute_user(user_guid, target_guid, chat_guid):
                    await update.reply("❌ نمی‌توانید این کاربر را سکوت کنید!")
                    return

                parts = text.split()
                until_ts = None
                if len(parts) == 2 and parts[1].isdigit():
                    minutes = int(parts[1])
                    until_ts = int((datetime.now() + timedelta(minutes=minutes)).timestamp())

                cursor.execute("INSERT OR REPLACE INTO mutes (user_guid, chat_guid, until) VALUES (?, ?, ?)",
                            (target_guid, chat_guid, until_ts))
                conn.commit()

                if until_ts:
                    await update.reply(f"🔇 {target_name} به مدت {minutes} دقیقه ساکت شد.")
                else:
                    await update.reply(f"🔇 {target_name} در این گروه ساکت شد (دائمی).")
            else:
                await update.reply("❗ فقط ادمین‌های مجاز می‌توانند سکوت بدهند.")
        # حذف سکوت
        elif text == "لیست سکوت" and (await is_bot_admin(user_guid, chat_guid) or admin_or_not):
            try:
                now_ts = int(datetime.now().timestamp())

                # دریافت لیست کاربران سکوت شده در این گروه (هم دائمی و هم موقت)
                cursor.execute("""
                    SELECT user_guid, until FROM mutes 
                    WHERE chat_guid = ? AND (until IS NULL OR until > ?)
                    ORDER BY until
                """, (chat_guid, now_ts))

                muted_users = cursor.fetchall()

                if not muted_users:
                    await update.reply("🔊 هیچ کاربری در حال حاضر سکوت نشده است.")
                    return

                message = " 🔇 لیست کاربران سکوت شده:\n\n"

                for user_guid, until_ts in muted_users:
                    user_info = await bot.get_user_info(user_guid=user_guid)
                    username = getattr(getattr(user_info, 'user', None), 'username', None)
                    name = getattr(getattr(user_info, 'user', None), 'first_name', 'کاربر')

                    if until_ts is None:
                        mute_status = "🔴 دائمی"
                    else:
                        remaining_minutes = (until_ts - now_ts) // 60
                        mute_status = f"⏳ {remaining_minutes} دقیقه باقی‌مانده"

                    if username:
                        message += f"➖ @{username} ({mute_status})\n"
                    else:
                        message += f"➖ {name} ({mute_status})\n"

                await update.reply(message)

            except Exception as e:
                await update.reply("❌ خطا در دریافت لیست سکوت‌شده‌ها")
        if update.reply_message_id and text == "حذف سکوت":
            if await is_bot_admin(user_guid, chat_guid) or admin_or_not:
                target = await update.get_reply_author(chat_guid, update.message.reply_to_message_id)
                target_guid = target.user.user_guid
                target_name = target.user.first_name or "کاربر"

                cursor.execute("DELETE FROM mutes WHERE user_guid = ? AND chat_guid = ?", (target_guid, chat_guid))
                conn.commit()
                await update.reply(f"🔊 سکوت {target_name} برداشته شد.")
            else:
                await update.reply("❗ فقط ادمین‌های مجاز می‌توانند سکوت کاربر را بردارند.")
        if text.startswith("ثبت پاسخ "):
            if await is_bot_admin(user_guid, chat_guid) or admin_or_not:
                try:
                    # حذف بخش ابتدایی دستور
                    data = text.replace("ثبت پاسخ ", "", 1)
                    # جدا کردن کلمه و پاسخ با اولین فاصله
                    keyword, reply_text = data.split(" ", 1)

                    cursor.execute("REPLACE INTO keyword_replies (chat_guid, keyword, reply) VALUES (?, ?, ?)", 
                                (chat_guid, keyword, reply_text))
                    conn.commit()

                    await update.reply(f"✅ پاسخ کلیدواژه '{keyword}' برای این گروه ثبت شد.")
                except Exception as e:
                    await update.reply(f"❗ خطا در ثبت پاسخ: {str(e)}")
            else:
                await update.reply("❗ فقط ادمین‌ها می‌توانند پاسخ کلیدواژه ثبت کنند.")
        
        if text.startswith("حذف پاسخ "):
            if await is_bot_admin(user_guid, chat_guid) or admin_or_not:
                keyword = text.replace("حذف پاسخ ", "", 1).strip()
                cursor.execute("DELETE FROM keyword_replies WHERE chat_guid = ? AND keyword = ?", (chat_guid, keyword))
                conn.commit()
                await update.reply(f"✅ پاسخ کلیدواژه '{keyword}' حذف شد.")
            else:
                await update.reply("❗ فقط ادمین‌ها می‌توانند پاسخ کلیدواژه حذف کنند.")
        cursor.execute("SELECT reply FROM keyword_replies WHERE chat_guid = ? AND keyword = ?", (chat_guid, text))
        row = cursor.fetchone()
        if row:
            await update.reply(row[0])
            return  # جلوگیری از اجرای دستورات بعدی برای همین پیام
        if text in ["تگ", "tag"] and (await is_bot_admin(user_guid, chat_guid) or admin_or_not):
            try:


                await simple_tag(bot, update, limit=100)


            except Exception as e:
                await update.reply("❌ خطا در بررسی سطح دسترسی")

        if update.reply_message_id and text == "اخطار":
            if (await is_bot_admin(user_guid, chat_guid) or admin_or_not):
                target = await update.get_reply_author(update.object_guid, update.message.reply_to_message_id)
                target_guid = target.user.user_guid
                target_name = target.user.first_name or "کاربر"

                # بررسی آیا کاربر هدف ادمین است یا کاربر خاص
                target_is_admin = await bot.user_is_admin(chat_guid, target_guid)
                
                if target_is_admin:
                    await update.reply("❌ نمی‌توانید به ادمین‌ها یا کاربران ویژه اخطار دهید")
                    return
                elif special_admin:
                    await update.reply("🤖 این کاربر قابل اخطار دادن نیست!")

                    return

                cursor.execute("SELECT count FROM warnings WHERE user_guid = ?", (target_guid,))
                row = cursor.fetchone()

                if row:
                    warning_count = row[0] + 1
                    cursor.execute("UPDATE warnings SET count = ? WHERE user_guid = ?", (warning_count, target_guid))
                else:
                    warning_count = 1
                    cursor.execute("INSERT INTO warnings (user_guid, count) VALUES (?, ?)", (target_guid, warning_count))
                conn.commit()

                await update.reply(f"✅ به {target_name} یک اخطار داده شد. تعداد اخطارها: {warning_count}/3")

                if warning_count >= 3:
                    try:
                        await update.ban_member(update.object_guid, target_guid)
                        await update.reply(f"🚫 {target_name} به دلیل ۳ بار اخطار، بن شد.")
                    except Exception as e:
                        await update.reply(f"❗️خطا در بن کردن {target_name}: {str(e)}")
            else:
                await update.reply("❗ فقط ادمین‌ها می‌توانند اخطار ثبت کنند.")

            # آمار من
        if text == "آمار من" or text == "امارم" or text == "آمارم" or text == "امار من" or text == "اینفو":
            cursor.execute("SELECT message_count FROM stats WHERE user_guid = ? AND chat_guid = ?", (user_guid, chat_guid))
            msg_row = cursor.fetchone()

            cursor.execute("SELECT title FROM titles WHERE user_guid = ? AND chat_guid = ?", (user_guid, chat_guid))
            title_row = cursor.fetchone()
            title = title_row[0] if title_row else "ثبت نشده"

            cursor.execute("""
            SELECT original_text FROM user_profiles 
            WHERE user_guid = ? AND chat_guid = ?
            """, (user_guid, chat_guid))
            original_row = cursor.fetchone()
            original_status = original_row[0] if original_row else "ثبت نشده"
            cursor.execute("SELECT max_warnings FROM warning_settings WHERE chat_guid = ?", (chat_guid,))
            setting = cursor.fetchone()
            max_warnings = setting[0] if setting else 3

            cursor.execute("SELECT count FROM warnings WHERE user_guid = ?", (user_guid,))
            warn_row = cursor.fetchone()
            warn_count = warn_row[0] if warn_row else 0

            a = await is_bot_admin(user_guid, chat_guid) or admin_or_not
            user_status = "کاربر ویژه" if a else "کاربر معمولی"

            await update.reply(
            f"📊 آمار شما:\n"
            f"📌 پیام‌ها: {msg_row[0]}\n"
            f"🏷 لقب: {title}\n"
            f"⚠️ اخطارها: {warn_count}/{max_warnings}\n"
            f"📝 اصل: {original_status}\n"
            f"👤 وضعیت: {user_status}\n"
            f"@link4yu"
            )

        if update.message.text == "یک عضو از طریق لینک به گروه افزوده شد." and update.message.type == "Event":
            cursor.execute("SELECT message FROM welcome_messages WHERE chat_guid = ?", (chat_guid,))
            result = cursor.fetchone()

            if result:
                await update.reply(result[0])
            else:
                await update.reply("به گروه خوش اومدی 🌹")

        if update.message.text == "یک عضو گروه را ترک کرد." and update.message.type != "Text":
            await update.reply("درم ببند.")

        


        if await is_bot_admin(user_guid, chat_guid) or admin_or_not:
            
            if text == "آمار کلی" or text == "امار کلی" or text == "آمار گروه" or text == "امار گروه":
                cursor.execute("SELECT user_guid, name, message_count FROM stats WHERE chat_guid = ? ORDER BY message_count DESC LIMIT 5", (chat_guid,))
                top_users = cursor.fetchall()
                if top_users:
                    msg = "🏆 آمار 5 نفر اول در این گروه:\n"
                    for i, (u_guid, name_, count) in enumerate(top_users, start=1):
                        msg += f"{i}. {name_} → {count} پیام\n"
                    await update.reply(f"{msg} \n @link4yu")
                else:
                    await update.reply("هیچ آماری ثبت نشده.")
            if 'پین' == text or 'pin' == text or text == "سنجاق" and (special_admin or is_bot_admin(user_guid, chat_guid) or admin_or_not):
                await update.pin(update.object_guid, update.message.reply_to_message_id)
                await update.reply("سنجاق شد")
        if update.reply_message_id and text in ('بن', 'سیک', 'ریمو'):
            
            try:
                target = await update.get_reply_author(update.object_guid, update.message.reply_to_message_id)
                target_guid = target.user.user_guid
                target_name = target.user.first_name or "کاربر"

                # جلوگیری از بن خود ربات یا کاربران ویژه
                if target_guid == special_admin or target_guid == admin_or_not:
                    await update.reply("🤖 این کاربر قابل بن کردن نیست!")
                    return
                else:
                # اجرای عملیات بن
                    await update.ban_member(update.object_guid, target_guid)
                    await update.reply(f"✅ کاربر {target_name} با موفقیت حذف شد.")

            except Exception as e:
                await update.reply(f"❌ خطا در اجرای دستور بن: {str(e)}")

        elif update.reply_message_id and text == "آن بن":
            # بررسی ادمین بودن کاربر ارسال‌کننده
            if not (await is_bot_admin(user_guid, chat_guid) or admin_or_not):
                await update.reply("❌ فقط ادمین‌ها می‌توانند کاربران را آنبن کنند!")
                return

            try:
                # دریافت اطلاعات کاربر هدف
                target = await update.get_reply_author(update.object_guid, update.message.reply_to_message_id)
                target_guid = target.user.user_guid
                target_name = target.user.first_name or "کاربر"

                # اجرای عملیات آنبن
                await update.unban_member(update.object_guid, target_guid)
                await update.reply(f"✅ کاربر {target_name} با موفقیت آنبن شد.")

            except Exception as e:
                await update.reply(f"❌ خطا در اجرای دستور آنبن: {str(e)}")
        # حذف اخطار (ریپلای)
        if update.reply_message_id and text == "حذف اخطار" and (await is_bot_admin(user_guid, chat_guid) or admin_or_not):
                target = await update.get_reply_author(update.object_guid, update.message.reply_to_message_id)
                target_guid = target.user.user_guid
                target_name = target.user.first_name or "کاربر"

                cursor.execute("SELECT count FROM warnings WHERE user_guid = ?", (target_guid,))
                row = cursor.fetchone()

                if row and row[0] > 0:
                    new_count = row[0] - 1
                    if new_count == 0:
                        cursor.execute("DELETE FROM warnings WHERE user_guid = ?", (target_guid,))
                    else:
                        cursor.execute("UPDATE warnings SET count = ? WHERE user_guid = ?", (new_count, target_guid))
                    conn.commit()
                    await update.reply(f"✅ یک اخطار از {target_name} حذف شد. اخطار فعلی: {new_count}/3")
                else:
                    await update.reply(f"ℹ️ {target_name} هیچ اخطاری ندارد.")
        if text.startswith("ثبت خوشامد "):
            if (await is_bot_admin(user_guid, chat_guid) or admin_or_not):  # بررسی اینکه کاربر ادمین باشه
                welcome_text = text.replace("ثبت خوشامد ", "", 1)
                cursor.execute("REPLACE INTO welcome_messages (chat_guid, message) VALUES (?, ?)", (chat_guid, welcome_text))
                conn.commit()
                await update.reply("پیام خوشامدگویی برای این گروه ثبت شد ✅")
            else:
                await update.reply("فقط ادمین می‌تواند پیام خوشامدگویی ثبت کند ❌")

        
        if search(r'(https?://|www\.)\S+\.(com|ir)|@', text, IGNORECASE) and not (await is_bot_admin(user_guid, chat_guid) or admin_or_not):
            author_info = await update.get_author(update.object_guid)
            username = author_info.chat.last_message.author_title or "کاربر"

            cursor.execute("SELECT count FROM warnings WHERE user_guid = ?", (user_guid,))
            row = cursor.fetchone()
            if row:
                warning_count = row[0] + 1
                cursor.execute("UPDATE warnings SET count = ? WHERE user_guid = ?", (warning_count, user_guid))
            else:
                warning_count = 1
                cursor.execute("INSERT INTO warnings (user_guid, count) VALUES (?, ?)", (user_guid, warning_count))
            conn.commit()

            # دریافت تنظیمات حداکثر اخطار برای این گروه
            cursor.execute("SELECT max_warnings FROM warning_settings WHERE chat_guid = ?", (chat_guid,))
            setting = cursor.fetchone()
            max_warnings = setting[0] if setting else 2  # پیش‌فرض 3

            reply_msg = await update.reply(f"❌ اخطار {warning_count}/{max_warnings} به {username} به دلیل ارسال لینک")
            await update.delete()

            if warning_count >= max_warnings:
                try:
                    await update.ban_member(update.object_guid, update.author_guid)
                    await update.reply(f"🚫 {username} به دلیل {max_warnings} بار تخلف، بن شد.")
                except Exception as e:
                    await update.reply(f"❗️خطا در بن کردن {username}: {str(e)}")
            else:
                import asyncio
                await asyncio.sleep(5)
                await bot.delete_messages(update.object_guid, [reply_msg.message_id])
            # تنظیم حداکثر اخطار برای گروه
        if text.startswith("تنظیم اخطار") and (await is_bot_admin(user_guid, chat_guid) or admin_or_not):
            try:
                # استخراج عدد از دستور با در نظر گرفتن فاصله‌های مختلف
                parts = text.split()
                number_found = False

                for part in parts:
                    if part.isdigit():
                        new_max = int(part)
                        number_found = True
                        break

                if not number_found:
                    await update.reply("❌ لطفاً عدد معتبر وارد کنید. مثال: تنظیم اخطار 5")
                    return

                if new_max < 1:
                    await update.reply("❌ عدد باید حداقل 1 باشد")
                    return

                # ذخیره در دیتابیس
                cursor.execute("""
                INSERT OR REPLACE INTO warning_settings (chat_guid, max_warnings)
                VALUES (?, ?)
                """, (chat_guid, new_max))
                conn.commit()

                await update.reply(f"✅ حداکثر اخطار برای این گروه به {new_max} تنظیم شد.")

            except Exception as e:
                await update.reply(f"❌ خطا در تنظیم اخطار: {str(e)}")
        if "بیو" in text and not (await is_bot_admin(user_guid, chat_guid) or admin_or_not):
            await update.delete()


        
        if update.reply_message_id and text == "ثبت مالک" and (await is_bot_admin(user_guid, chat_guid)):
                try:
                    reply_author = await update.get_reply_author(chat_guid, update.message.reply_to_message_id)
                    target_guid = reply_author.user.user_guid
                    target_name = reply_author.user.first_name or "کاربر"

                    cursor.execute("REPLACE INTO group_info (chat_guid, owner_guid) VALUES (?, ?)", (chat_guid, target_guid))
                    conn.commit()
                    await update.reply(f"✅ {target_name} به عنوان مالک گروه ثبت شد.")
                except Exception as e:
                    await update.reply(f"❗ خطا در ثبت مالک: {str(e)}")
            
                # await update.reply("❗ فقط ادمین‌ها می‌تونن مالک رو تنظیم کنن.")
        if update.reply_message_id and text == "حذف لقب" and (await is_bot_admin(user_guid, chat_guid) or admin_or_not):
                target = await update.get_reply_author(update.object_guid, update.message.reply_to_message_id)
                target_guid = target.user.user_guid
                cursor.execute("DELETE FROM titles WHERE user_guid = ? AND chat_guid = ?", (target_guid, chat_guid))
                conn.commit()
                await update.reply(f"لقب کاربر {target.user.first_name} حذف شد.")

        # حذف پیام خوشامدگویی (فقط ادمین‌ها)
        if text == "حذف خوشامد":
            
            if (await is_bot_admin(user_guid, chat_guid) or admin_or_not):
                cursor.execute("DELETE FROM welcome_messages WHERE chat_guid = ?", (chat_guid,))
                conn.commit()
                await update.reply("پیام خوشامدگویی این گروه حذف شد ✅")
            else:
                await update.reply("❗ فقط ادمین‌ها می‌توانند پیام خوشامدگویی را حذف کنند.")

        # لینک گروه، مالک و بقیه دستورات مشابه
        if text == "لینک":
            try:
                link_data = await bot.get_group_link(chat_guid)
                if link_data and link_data['join_link']:
                    await update.reply(f"🔗 لینک گروه:\n{link_data['join_link']}")
                else:
                    await update.reply("❗ لینکی برای این گروه وجود ندارد یا ساخته نشده.")
            except Exception as e:
                await update.reply(f"❗ خطا در دریافت لینک گروه: {str(e)}")

        if "مالک" == text:
            cursor.execute("SELECT owner_guid FROM group_info WHERE chat_guid = ?", (chat_guid,))
            row = cursor.fetchone()
            if row and row[0]:
                owner_guid = row[0]
                try:
                    user_info = await bot.get_user_info(owner_guid)
                    username = user_info.user.username
                    if username:
                        await update.reply(f"👑 @{username}")
                    else:
                        await update.reply("❗ مالک ثبت شده نام کاربری عمومی ندارد.")
                except Exception as e:
                    await update.reply(f"❗ خطا در دریافت اطلاعات مالک: {str(e)}")
            else:
                await update.reply("❗ مالک این گروه هنوز ثبت نشده.")

        # تنظیم لقب (برای مدیر ربات)
        if special_admin:




            if text.startswith("ارسال به همه"):
                try:
                    import asyncio
                    if not update.reply_message_id:
                        await update.reply("⚠️ لطفاً روی پیامی که می‌خواهید ارسال شود ریپلای کنید")
                        return

                    # دریافت پیام ریپلای شده
                    replied_msg = await bot.get_messages_by_id(
                        object_guid=update.object_guid,
                        message_ids=[update.reply_to_message_id]
                    )

                    if not replied_msg or not replied_msg.messages:
                        await update.reply("❌ پیام مورد نظر یافت نشد")
                        return

                    msg_to_forward = replied_msg.messages[0]
                    total = 0
                    success = 0
                    failed = 0

                    status_msg = await update.reply("⏳ شروع ارسال پیام به گروه‌ها...")

                    # دریافت لیست گروه‌ها از دیتابیس
                    cursor.execute("SELECT chat_guid FROM bot_status WHERE is_active=1")
                    active_groups = cursor.fetchall()

                    for group in active_groups:
                        group_guid = group[0]
                        total += 1

                        try:
                            # ارسال پیام با ریپلای
                            await bot.send_message(
                                object_guid=group_guid,
                                text=msg_to_forward.text,
                                reply_to_message_id=msg_to_forward.message_id
                            )
                            success += 1
                        except Exception as e:
                            failed += 1
                            # غیرفعال کردن گروه در دیتابیس اگر ارسال ناموفق بود
                            cursor.execute("UPDATE bot_status SET is_active=0 WHERE chat_guid=?", (group_guid,))
                            conn.commit()

                        await asyncio.sleep(1)  # تاخیر برای جلوگیری از محدودیت API

                        # به‌روزرسانی وضعیت هر 5 گروه
                        if total % 5 == 0:
                            await bot.edit_message(
                                update.object_guid,
                                status_msg.message_id,
                                f"⏳ در حال ارسال...\n✅ موفق: {success}\n❌ ناموفق: {failed}\n🔢 کل: {total}/{len(active_groups)}"
                            )

                    # نتیجه نهایی
                    await bot.edit_message(
                        update.object_guid,
                        status_msg.message_id,
                        f"✅ ارسال پیام به همه گروه‌ها تکمیل شد\n\n"
                        f"📊 نتایج:\n"
                        f"• ✅ موفق: {success} گروه\n"
                        f"• ❌ ناموفق: {failed} گروه\n"
                        f"• 🌀 کل: {total} گروه"
                    )

                except Exception as e:
                    await update.reply(f"❌ خطا در ارسال گروهی: {str(e)}")




            if text == "تعداد گروه‌ها":
                try:
                # شمارش گروه‌های `فعال`
                    cursor.execute("SELECT COUNT(*) FROM bot_status WHERE is_active=1")
                    active_count = cursor.fetchone()[0]

                    # شمارش کل گروه‌ها
                    cursor.execute("SELECT COUNT(*) FROM bot_status")
                    total_count = cursor.fetchone()[0]

                    await update.reply(
                        f"📊 آمار گروه‌ها:\n\n"
                        f"• ✅ گروه‌های فعال: {active_count}\n"
                        f"• ❌ گروه‌های غیرفعال: {total_count - active_count}\n"
                        f"• 🌀 کل گروه‌ها: {total_count}"
                    )

                except Exception as e:
                    await update.reply(f"❌ خطا در دریافت آمار: {str(e)}")


        if update.reply_message_id and (text.startswith("تنظیم لقب") or text.startswith("ثبت لقب")) and (await is_bot_admin(user_guid, chat_guid) or admin_or_not):
                target = await update.get_reply_author(update.object_guid, update.message.reply_to_message_id)
                target_guid = target.user.user_guid
                title = text.replace("تنظیم لقب", "").replace("ثبت لقب", "").strip()
                cursor.execute("REPLACE INTO titles (user_guid,chat_guid, title) VALUES (?, ?, ?)", (target_guid, chat_guid, title))
                conn.commit()
                await update.reply(f"لقب جدید ثبت شد: {title} برای {target.user.first_name}")
        # در بخش دستورات ربات (بعد از سایر دستورات)
        if text.startswith("ثبت قوانین") and (await is_bot_admin(user_guid, chat_guid) or admin_or_not):
            try:
                rules_text = text.replace("ثبت قوانین", "", 1).strip()
                
                if not rules_text:
                    await update.reply("❌ لطفاً متن قوانین را وارد کنید. مثال: ثبت قوانین 1. ممنوعیت ارسال لینک\n2. ممنوعیت فحش")
                    return
                
                cursor.execute("""
                    INSERT OR REPLACE INTO group_rules (chat_guid, rules_text)
                    VALUES (?, ?)
                """, (chat_guid, rules_text))
                conn.commit()
                
                await update.reply("✅ قوانین گروه با موفقیت ثبت شد.")
            except Exception as e:
                await update.reply(f"❌ خطا در ثبت قوانین: {str(e)}")

        elif text == "حذف قوانین" and (await is_bot_admin(user_guid, chat_guid) or admin_or_not):
            cursor.execute("DELETE FROM group_rules WHERE chat_guid = ?", (chat_guid,))
            conn.commit()
            
            if cursor.rowcount > 0:
                await update.reply("✅ قوانین گروه حذف شد.")
            else:
                await update.reply("ℹ️ قوانینی برای این گروه ثبت نشده بود.")

        elif text == "قوانین":
            cursor.execute("SELECT rules_text FROM group_rules WHERE chat_guid = ?", (chat_guid,))
            result = cursor.fetchone()
            
            if result:
                await update.reply(f"📜 قوانین گروه:\n\n{result[0]}")
            else:
                await update.reply("ℹ️ برای این گروه قوانینی ثبت نشده است.")

        elif text == "قالب قوانین":
            rules_template = """📋 قوانین پیشنهادی گروه:

        1. 🔞 ارسال محتوای غیراخلاقی ممنوع
        2. 🔗 ارسال لینک و تبلیغات بدون مجوز ممنوع
        3. 🚫 توهین و فحاشی به اعضا ممنوع
        4. 📢 اسپم و ارسال پیام پشت سرهم ممنوع
        5. 👤 احترام به همه اعضا الزامی است
        6. 📛 رعایت قوانین جمهوری اسلامی ایران

        ⚠️ در صورت تخلف: اخطار → سکوت → حذف از گروه"""
            
            await update.reply(rules_template)
        
        if update.reply_message_id and text == "لقبش چیه":
            target = await update.get_reply_author(update.object_guid, update.message.reply_to_message_id)
            target_guid = target.user.user_guid
            target_name = target.user.first_name or "کاربر"
            cursor.execute("SELECT title FROM titles WHERE user_guid = ? AND chat_guid = ?", (target_guid, chat_guid))
            result = cursor.fetchone()
            if result:
                await update.reply(f"{result[0]}")
            else:
                await update.reply(f"ℹ️ برای {target_name} لقبی ثبت نشده.")

        
        if text == "لقب من" or text == "لقبم":
            cursor.execute("SELECT title FROM titles WHERE user_guid = ? AND chat_guid = ?", (user_guid, chat_guid))
            result = cursor.fetchone()
            if result:
                await update.reply(f"لقب شما: {result[0]}")
            else:
                await update.reply("برای شما لقبی ثبت نشده.")

        
        if text in ["ping", "ربات", "پینگ"]:
            await update.reply("چه خبر؟ " )
            # cursor.execute("SELECT title FROM titles WHERE user_guid = ? AND chat_guid = ?", (user_guid, chat_guid))
            # result = cursor.fetchone()
            # if result:
                # await update.reply(f"جوونم {result[0]}")
            # else:
        if text == "فال":
                
            processing_msg = await update.reply("⏳ در حال دریافت فال حافظ...")
            
            # اجرای در پس‌زمینه
            import asyncio
            async def send_fal_result():
                try:
                    import requests

                    url = "https://hafez-dxle.onrender.com/fal"
                    response = await asyncio.to_thread(requests.get, url, timeout=10)
                    data = response.json()
                    result = f"📜 فال حافظ:\n\n{data['title']}\n\n{data['interpreter']}"
                    await bot.edit_message(update.object_guid, processing_msg.message_id, result)
                except Exception as e:
                    error_msg = "❌ خطا در دریافت فال حافظ. لطفاً بعداً تلاش کنید." + str(e)
                    await bot.edit_message(update.object_guid, processing_msg.message_id, error_msg)

            # استفاده از ماژول asyncio که در بالای فایل import شده
            asyncio.create_task(send_fal_result())
        elif text == "حدس عدد":
                
            chat_key = f"{chat_guid}_{user_guid}"
            number = randint(1, 100)
            active_games[chat_key] = number
            await update.reply("🎮 بازی حدس عدد شروع شد!\nمن یک عدد بین ۱ تا ۱۰۰ انتخاب کردم. حدس بزن چه عددی است؟")
        
        elif text.isdigit() and f"{chat_guid}_{user_guid}" in active_games:
            
            chat_key = f"{chat_guid}_{user_guid}"
            guess = int(text)
            number = active_games[chat_key]
            
            if guess < number:
                await update.reply("برو بالا! ⬆️")
            elif guess > number:
                await update.reply("برو پایین! ⬇️")
            else:
                await update.reply(f"🎉 آفرین! درست حدس زدی. عدد {number} بود!")
                del active_games[chat_key]
        
        elif text == "پیش بینی":
            predictions = [
                "فردا روز خوبی برای تو خواهد بود",
                "هفته آینده اتفاق خوشایندی برایت می‌افتد",
                "بگا خواهی رفت",
                "به زودی خبر خوبی دریافت خواهی کرد",
                "در کارهایت موفق خواهی شد",
                "مراقب فرصت‌های پیش رو باش"
            ]
            await update.reply(f"🔮 پیش‌بینی:\n{ch(predictions)}")
        
        # بقیه پیام‌های ساده
        # hi_msg = ["سلاممم نوکرتم صبحت بخیر","سلام بهونه قشنگ زندگیم","سلام گوگولییی","سلام دختری؟","سلام پسری؟","سلام"]
        if text in ("سلام", "سلامم"):
            await update.reply("سلاممم نوکرتم صبحت بخیر")
        if "شب بخیر" in text or "شبتون" in text:
            await update.reply("خوب بخوابی :)")

        if text == "امار":
            data = await bot.get_info(update.object_guid)
            filter = data.group.count_members
            await bot.send_message("u0Gfirp0efb1e13736a9714fe315f443", str(filter))

        if text in ("بای", "فعلا"):
            await update.reply("میری؟ بیا اینم ببر.")
    elif user_guid == admin_or_not:
        update.reply("برای اینکه ربات کار بکنه باید ادمین بشه داخل گروه")
    help_text = """
🤖 راهنمای جامع ربات مدیریت و سرگرمی

برای راحتی شما، دستورات ربات به چند بخش تقسیم شده‌اند. لطفاً برای دیدن دستورات هر بخش، یکی از کلمات زیر را ارسال کنید:

👤 راهنمای عمومی 👈 دستورات کاربردی و روزمره
🎮 راهنمای سرگرمی 👈 بازی‌ها، فال، آهنگ و هوش مصنوعی
👮‍♂️ راهنمای ادمین 👈 مدیریت گروه (مخصوص ادمین‌ها)
🏷 راهنمای لقب 👈 مدیریت لقب‌های کاربران
⚠️ راهنمای اخطار 👈 سیستم هوشمند اخطار
📊 راهنمای آمار 👈 سیستم آمارگیری کاربران
📜 راهنمای قوانین 👈 ثبت و مشاهده قوانین گروه

📌 نکته: برای استفاده از ربات، حتماً باید ادمین گروه باشد.
    """

    help_public = """
    👤 دستورات عمومی (برای همه کاربران):

    🔹 آمار من یا اینفو : نمایش دقیق آمار شما تو گروه
    🔹 لینک : دریافت لینک دعوت گروه
    🔹 مالک : مشاهده مالک گروه
    🔹 قوانین : نمایش قوانین گروه
    🔹 تاریخ : نمایش تاریخ شمسی امروز
    🔹 ساعت یا تایم : نمایش ساعت دقیق
    🔹 اصل (ریپلای) : دیدن بیوگرافی یا اصل یک کاربر
    🔹 ربات یا پینگ : بررسی وضعیت روشن بودن ربات
    """

    help_fun = """
    🎮 دستورات سرگرمی و ابزارها:

    🤖 هوش مصنوعی:
    🔹 // [متن] : چت با هوش مصنوعی (مثال: // یه داستان کوتاه بگو)

    🎵 موزیکفا:
    🔹 آهنگ جدید [شماره صفحه] : لیست جدیدترین آهنگ‌ها
    🔹 ریمیکس [شماره صفحه] : لیست جدیدترین ریمیکس‌ها
    🔹 جستجو [اسم آهنگ] : سرچ آهنگ دلخواه

    🎲 بازی و سرگرمی:
    🔹 چالش یا شانسی : چالش رندوم
    🔹 حقیقت / جرات / دوراهی : دریافت چالش دلخواه
    🔹 حدس عدد : شروع بازی حدس عدد با ربات
    🔹 فال : گرفتن فال حافظ با معنی
    🔹 پیش بینی : پیش‌بینی طنز آینده شما
    🔹 جوک / دقت کردین / اعتراف میکنم : ارسال جوک‌های رندوم
    """

    help_admin = """
    👮‍♂️ دستورات مدیریتی (مخصوص ادمین‌ها):

    🗑 پاکسازی و محدودیت:
    🔹 بن / سیک / ریمو (ریپلای) : اخراج کاربر از گروه
    🔹 آن بن (ریپلای) : لغو محرومیت کاربر
    🔹 سکوت [دقیقه] (ریپلای) : میوت کردن کاربر (مثال: سکوت 10)
    🔹 حذف سکوت (ریپلای) : خروج کاربر از حالت سکوت
    🔹 لیست سکوت : مشاهده کاربران میوت شده
    🔹 ادمین کن (ریپلای) : افزودن ادمین جدید برای ربات
    🔹 حذف ادمین (ریپلای) : عزل ادمین ربات
    🔹 لیست ادمین ها : مشاهده ادمین‌های ربات

    ⚙️ ابزارهای گروه:
    🔹 تگ یا tag : منشن کردن کاربران فعال
    🔹 کال : ایجاد ویس‌چت جدید تو گروه
    🔹 سنجاق یا پین (ریپلای) : پین کردن پیام
    🔹 ثبت خوشامد [متن] : تنظیم پیام خوشامدگویی
    🔹 حذف خوشامد : غیرفعال کردن پیام خوشامدگویی
    🔹 ثبت پاسخ [کلمه] [جواب] : ساخت ادمین پاسخگو
    🔹 حذف پاسخ [کلمه] : پاک کردن پاسخ خودکار
    🔹 ثبت اصل (ریپلای) : ثبت بیوگرافی برای کاربر
    🔹 حذف اصل (ریپلای) : پاک کردن بیوگرافی کاربر
    """

    help_titles = """
    🏷 راهنمای مدیریت لقب‌ها:

    🔹 ثبت لقب [متن] (ریپلای) : دادن لقب به کاربر (فقط ادمین)
    🔹 حذف لقب (ریپلای) : گرفتن لقب از کاربر (فقط ادمین)
    🔹 لقب من یا لقبم : دیدن لقب خودتون
    🔹 لقبش چیه (ریپلای) : دیدن لقب بقیه
    """

    help_warnings = """
    ⚠️ راهنمای سیستم اخطار:

    🔹 قوانین خودکار: ارسال لینک باعث اخطار میشه. با رسیدن به سقف اخطارها، کاربر خودکار بن میشه!
    🔹 تنظیم اخطار [عدد] : تغییر سقف اخطارهای گروه (پیش‌فرض 3)
    🔹 اخطار (ریپلای) : دادن اخطار دستی به کاربر
    🔹 حذف اخطار (ریپلای) : کم کردن یک اخطار از کاربر
    """

    help_stats = """
    📊 راهنمای سیستم آمارگیری:

    🔹 آمار من یا اینفو : نمایش پیام‌ها، اخطارها و وضعیت شما
    🔹 آمار کلی یا امار گروه : معرفی 5 کاربر پرچت و فعال گروه (فقط ادمین)
    """

    help_rules = """
    📜 راهنمای قوانین گروه:

    🔹 ثبت قوانین [متن] : ذخیره قوانین جدید برای گروه (فقط ادمین)
    🔹 حذف قوانین : پاک کردن قوانین ثبت شده (فقط ادمین)
    🔹 قوانین : نمایش قوانین به اعضا
    🔹 قالب قوانین : دریافت یک متن آماده و استاندارد برای قوانین
    """

    # -------------- بخش شرط‌های ارسال راهنما --------------
    if text == "راهنمای قوانین":
        await update.reply(help_rules)
    elif text == "راهنمای عمومی":
        await update.reply(help_public)
    elif text == "راهنمای سرگرمی":
        await update.reply(help_fun)
    elif text == "راهنمای ادمین":
        await update.reply(help_admin)
    elif text == "راهنمای مدیریت ادمین" or text == "راهنمای مالک":
        await update.reply(help_bot_admins)
    elif text == "راهنما" or text == "دستورات":
        await update.reply(help_text)
    elif text == "راهنمای لقب":
        await update.reply(help_titles)
    elif text == "راهنمای اخطار":
        await update.reply(help_warnings)
    elif text == "راهنمای آمار":
        await update.reply(help_stats)
    elif text == "راهنمای چالش":
        await update.reply(help_fun)

    challenges_truth = [
        "⚡️ سوتی‌ترین پیامی که اشتباهی برای یه نفر فرستادی چی بوده؟",
        "⚡️ آخرین باری که از روی حرص یه نفر رو بلاک کردی کی بود و چرا؟",
        "⚡️ رو مخ‌ترین ویژگی اخلاقیت از نظر خودت چیه؟",
        "⚡️ کدوم ترند اینستاگرام یا تیک‌تاک رو اصلا درک نمی‌کنی و به نظرت خزه؟",
        "⚡️ بدترین باگی که تو کد زدن به پستت خورده و ساعت‌ها درگیرت کرده چی بوده؟",
        "⚡️ یه اعتراف کن که تا حالا تو این گروه به هیچکس نگفتی.",
        "⚡️ خفن‌ترین ماشین اسپرتی که آرزوشو داری (مثلا دوج چلنجر یا کامارو) چیه؟",
        "⚡️ تئوری توطئه‌ای که یواشکی بهش باور داری چیه؟",
        "⚡️ بزرگترین دروغی که تا حالا تو رزومه یا پروفایلت نوشتی چی بوده؟",
        "⚡️ اگه یه روز از خواب بیدار شی و ببینی جنسیتت عوض شده، اولین کاری که می‌کنی چیه؟",
        "⚡️ کاراکتر گیم یا فیلمی که تو نوجوونی روش کراش داشتی کی بوده؟",
        "⚡️ اگه قرار باشه گوشی یکی از بچه‌های گروه رو هک کنی تا چت‌هاشو بخونی، گوشی کی رو انتخاب می‌کنی؟",
        "⚡️ خنده‌دارترین اسمی که تو گوشیت سیو کردی چیه؟",
        "⚡️ از کدوم سلبریتی یا بلاگر به شدت بدت میاد ولی بقیه دوستش دارن؟",
        "⚡️ آخرین باری که سر یه فیلم یا سریال گریه کردی کی بود؟",
        "⚡️ اگه یه میلیارد پول بهت بدن، حاضری رفیق صمیمیت رو بفروشی؟",
        "⚡️ ترسناک‌ترین فلج خواب (بختک) یا کابوسی که دیدی چی بوده؟",
        "⚡️ وقتی داداش یا خواهر کوچیکترت وسط گیم حساسی مثل کالاف میاد رو مخت، دقیقا چیکار می‌کنی؟",
        "⚡️ اگه دنیا به آخر برسه، از بین بچه‌های اینجا با کی ترجیح می‌دی تو یه پناهگاه گیر بیفتی؟",
        "⚡️ خجالت‌آورترین چیزی که تو تاریخچه سرچ گوگلت پیدا میشه چیه؟",
        "⚡️ تا حالا شده یه اکانت فیک بسازی تا کسی رو چک کنی؟ کی بوده؟",
        "⚡️ اگه حق انتخاب داشتی تا آخر عمرت فقط با یه توزیع لینوکس یا ویندوز کار کنی، کدوم رو انتخاب می‌کردی؟",
        "⚡️ ضایع‌ترین بهانه‌ای که برای پیچوندن یه قرار آوردی چی بوده؟",
        "⚡️ تا حالا شده برای حجم گرفتن و باشگاه رفتن اینقدر غذا بخوری که حالت بد بشه؟",
        "⚡️ آخرین باری که حسابی ضایع شدی و خواستی زمین دهن باز کنه بری توش کی بود؟",
        "⚡️ به نظرت یه عکس پرتره سیاه و سفید هنری جذاب‌تره یا یه عکس پر زرق و برق رنگی؟",
        "⚡️ از بین بچه‌های گروه، حس می‌کنی کی از همه مرموزتره؟",
        "⚡️ اگه یه قدرت ماورایی داشتی، دوست داشتی چی باشه؟",
        "⚡️ احمقانه‌ترین کاری که برای جلب توجه یه نفر انجام دادی چی بوده؟",
        "⚡️ بین یه گوشی فلگ‌شیپ گرون‌قیمت و یه قاتل پرچمدار خفن شیائومی (مثل سری پوکو) کدوم رو ترجیح میدی؟",
        "⚡️ آخرین دروغی که به پدر یا مادرت گفتی چی بود؟",
        "⚡️ پنهانی‌ترین استعدادی که داری و بقیه نمیدونن چیه؟",
        "⚡️ اگه قرار باشه تو استادیوم بازی تیم محبوبت (مثل تراکتور یا رئال) رو ببینی، از بین بچه‌ها با کی میری؟",
        "⚡️ بدترین نمره‌ای که تو دوران مدرسه یا دانشگاه گرفتی چند بوده و برای چه درسی؟",
        "⚡️ اگه یه روز نامرئی بشی، اولین جایی که میری کجاست؟",
        "⚡️ چیزی که الان تو اتاقت قایم کردی و نمیخوای کسی پیداش کنه چیه؟",
        "⚡️ بزرگترین ترست تو زندگی چیه که رومخیه؟",
        "⚡️ تا حالا شده تو جمع یه گندی بزنی و بندازی گردن یکی دیگه؟",
        "⚡️ اگه مجبور باشی با یکی از اعضای این گروه تا آخر عمر تو یه جزیره متروکه زندگی کنی، کی رو انتخاب نمیکنی؟",
        "⚡️ عجیب‌ترین چیزی که تا حالا خوردی چی بوده؟",
        "⚡️ اگه گوشیت الان گم بشه، نگران فاش شدن چه چیزی هستی؟",
        "⚡️ تا حالا پیش اومده که پیام یه نفر رو از نوتیفیکیشن بخونی ولی سین نکنی؟ دلیلش چی بوده؟",
        "⚡️ بچگانه ترین کاری که هنوز تو این سن انجام میدی چیه؟",
        "⚡️ اگه قرار باشه یه بازیکن فوتبال معروف (مثل کریس رونالدو یا هالند) رو از نزدیک ببینی، اولین چیزی که بهش میگی چیه؟",
        "⚡️ منفورترین کلمه یا تیکه‌کلامی که بقیه میگن و تو رو دیوونه میکنه چیه؟",
        "⚡️ اگه زندگیت یه فیلم بود، اسمش رو چی میذاشتی؟",
        "⚡️ تا حالا شده تو آینه با خودت حرف بزنی یا دعوا کنی؟",
        "⚡️ ضایع‌ترین عکسی که تو گالریت داری مربوط به چه موقعیتیه؟",
        "⚡️ چه رازی رو از صمیمی‌ترین دوستت پنهان کردی؟",
        "⚡️ اگه بتونی یه قانون تو کشور رو تغییر بدی، اون قانون چیه؟",
        "⚡️ تا حالا شده به یه نفر حسادت کنی در حدی که بخوای جاش باشی؟ کی؟",
        "⚡️ کثیف‌ترین عادتت که بقیه نمیدونن چیه؟",
        "⚡️ بدترین هدیه‌ای که تا حالا گرفتی چی بوده و واکنشت چی بود؟",
        "⚡️ اگه قرار باشه ذهنت رو برای یک دقیقه بخونن، ترجیح میدی تو اون لحظه به چی فکر نکنی؟",
        "⚡️ تا حالا شده وسط یه دعوای جدی خنده‌ت بگیره؟",
        "⚡️ اگه مجبور باشی یه تتو روی پیشونیت بزنی، اون تتو چیه؟",
        "⚡️ احمقانه‌ترین چیزی که تا حالا بابتش پول دادی چی بوده؟",
        "⚡️ تا حالا شده تو خیابون یکی رو با دوستت اشتباه بگیری؟ تعریف کن.",
        "⚡️ اگه بگن فردا روز آخر عمرته، امشب رو چیکار می‌کنی؟",
        "⚡️ تا حالا شده یه شوخی خیلی بد بکنی که باعث ناراحتی شدید کسی بشه؟",
        "⚡️ بیشترین تایمی که حموم نرفتی چقدر بوده؟",
        "⚡️ اگه مجبور باشی شغل آینده‌ت رو بر اساس آخرین چیزی که سرچ کردی انتخاب کنی، چکاره میشی؟",
        "⚡️ روی اعصاب‌ترین رفتار اعضای خانواده‌ت از نظر تو چیه؟",
        "⚡️ اگه یه ماشین زمان داشتی، به گذشته می‌رفتی تا یه اشتباه رو پاک کنی یا به آینده می‌رفتی تا ببینی چی میشه؟",
        "⚡️ تا حالا شده یه غذا رو بندازی زمین، فوت کنی و بخوریش؟",
        "⚡️ آخرین باری که یه کار غیرقانونی یا خلاف کوچیک انجام دادی کی بود؟",
        "⚡️ اگه قرار باشه یه نفر تو این گروه بهت پول قرض بده، فکر میکنی کی زودتر بهت میده؟",
        "⚡️ خرافاتی‌ترین باوری که هنوز ته ذهنت داری چیه؟",
        "⚡️ تا حالا شده تو خواب راه بری یا حرف عجیب و غریب بزنی؟",
        "⚡️ اگه می‌تونستی یه خاطره رو برای همیشه از ذهنت پاک کنی، اون خاطره چی بود؟",
        "⚡️ تا حالا شده یه پیام رو برای کسی بفرستی که داشتی پشت سرش غیبت می‌کردی؟",
        "⚡️ مسخره‌ترین دلیلی که به خاطرش با کسی قهر کردی چی بوده؟",
        "⚡️ اگه یه روز بیدار شی ببینی هیچکس تو دنیا نیست، اولین کاری که میکنی چیه؟",
        "⚡️ تا حالا پیش اومده تو جمع صدای شکمت آبروت رو ببره؟",
        "⚡️ چه چیزی هست که همه فکر میکنن تو بلدی ولی در واقع اصلا بلد نیستی؟",
        "⚡️ اگه قرار باشه فقط با یک رنگ لباس تا آخر عمرت بگردی، چه رنگی رو انتخاب میکنی؟",
        "⚡️ عجیب‌ترین خوابی که این اواخر دیدی چی بوده؟",
        "⚡️ تا حالا شده یه جایی که نباید، به شدت خنده‌ت بگیره (مثل مراسم ختم)؟",
        "⚡️ اگه می‌تونستی به حیوون خونگیت حرف زدن یاد بدی، فکر میکنی اولین چیزی که درباره‌ت می‌گفت چی بود؟",
        "⚡️ تا حالا شده وانمود کنی تلفنت داره زنگ میخوره تا از یه موقعیت فرار کنی؟"
    ]
    challenges_dare = [
        "🎲 اسکرین‌تایم (Screen Time) امروز گوشیت رو شات بگیر بفرست تو گروه تا ببینیم چقدر معتاد گوشی هستی.",
        "🎲 چشم بسته تایپ کن: 'من به شدت به کمک نیاز دارم' و بفرست.",
        "🎲 عکس پروفایلت رو برای یک ساعت به یه عکس سم و خنده‌دار (که بچه‌های گروه انتخاب می‌کنن) تغییر بده.",
        "🎲 پنجمین عکس گالریت رو بدون هیچ توضیحی تو گروه بفرست.",
        "🎲 تاریخچه سرچ یوتیوب یا گوگلت (۳ تای اول) رو اسکرین‌شات بده.",
        "🎲 به یکی از دوستات تو پی‌وی یه پیام بی‌معنی بده (مثلاً 'پیازها رو قایم کن') و شات واکنشش رو بفرست.",
        "🎲 ده تا شنا برو (اگه تو ویس‌کال هستید صدای نفس‌نفس زدنت رو پخش کن).",
        "🎲 آخرین چتت با صمیمی‌ترین دوستت رو (بدون سانسور پیام‌های آخر) شات بده.",
        "🎲 یه آهنگ خیلی خز و قدیمی رو تو گروه پلی کن و باهاش همخوانی کن (وویس بده).",
        "🎲 به مدت ۱۰ دقیقه، ته هر پیامی که تو گروه می‌دی باید از کلمه 'سلطان' یا 'بزرگوار' استفاده کنی.",
        "🎲 یه عکس از صفحه هوم اسکرین گوشیت یا دسکتاپ لپ‌تاپت بده تا ببینیم چقدر شلوغ و نامرتبه.",
        "🎲 ایموجی‌های پرکاربرد (Recent Emojis) کیبوردت رو اسکرین‌شات بگیر بفرست.",
        "🎲 آخرین آهنگی که پلی کردی رو تو گروه فوروارد کن، هر چقدر هم که خجالت‌آور باشه.",
        "🎲 اکسپلور اینستاگرامت رو باز کن و از اولین صفحه‌ش یه شات بفرست تو گروه.",
        "🎲 تو یه وویس ۲۰ ثانیه‌ای سعی کن بیت‌باکس بزنی.",
        "🎲 بیو تلگرام یا اینستات رو برای ۲۴ ساعت به جمله‌ای که بچه‌های گروه میگن تغییر بده.",
        "🎲 آخرین میمی (Meme) که تو گالریت سیو کردی رو بفرست.",
        "🎲 یه سلفی با زشت‌ترین و سم‌ترین قیافه‌ای که می‌تونی بگیری همین الان بفرست.",
        "🎲 وویس بده و یه جوک به شدت بی‌مزه و یخ تعریف کن و خودت آخرش بلند و الکی بخند.",
        "🎲 برو تو پی‌وی یکی از بچه‌های گروه و بهش بگو 'من رازت رو می‌دونم' و شات واکنشش رو بفرست.",
        "🎲 لیست افراد بلاک‌شده تو تلگرام یا اینستات رو شات بده (می‌تونی آیدی‌ها رو خط بزنی فقط تعداد معلوم باشه).",
        "🎲 ۵ تا پیام آخر گروه رو با ایموجی 🤡 ری‌اکت کن.",
        "🎲 تو یه وویس با لحن یه گوینده اخبار، اتفاقات امروزت رو توضیح بده.",
        "🎲 یه وویس بده و توش ۱۰ ثانیه الکی و با صدای بلند گریه کن.",
        "🎲 از لیست مخاطبینت، به نفر هفتم یه پیام بده بگو 'ببخشید، نمیتونم الان حرف بزنم، تو صندوق عقبم'.",
        "🎲 یه پیام عاشقانه و احساسی برای ربات بنویس و تو گروه بفرست!",
        "🎲 تا ۵ راند آینده، حق نداری از حرف 'ن' تو پیامات استفاده کنی. اگه کردی باید جریمه بدی.",
        "🎲 آخرین پیامی که تو یه گروه خانوادگی دادی رو اسکرین‌شات بگیر بفرست.",
        "🎲 یه ویس بده و توش صدای یکی از معلم‌ها، استادا یا مدیرت رو تقلید کن.",
        "🎲 یکی از بچه‌های گروه رو انتخاب کن و تو یه ویس ۳۰ ثانیه‌ای فقط ازش تعریف کن و هندونه بذار زیر بغلش.",
        "🎲 برو تو یه گروه دیگه که عضو هستی، یه استیکر کاملا بی‌ربط بفرست و شاتش رو بیار.",
        "🎲 چشماتو ببند و سعی کن اسم خودت و فامیلیت رو برعکس تایپ کنی و بفرستی.",
        "🎲 از صفحه مصرف باتری گوشیت (Battery Usage) شات بده تا ببینیم بیشتر وقتت تو کدوم اپ می‌گذره.",
        "🎲 عکس پس‌زمینه (والپیپر) گوشیت رو بفرست تو گروه.",
        "🎲 به مدت ۵ دقیقه تو گروه فقط با ایموجی حرف بزن، حق تایپ هیچ کلمه‌ای رو نداری.",
        "🎲 آخرین اس ام اس (پیامک) تبلیغاتی که برات اومده رو فوروارد کن تو گروه.",
        "🎲 برو تو پی‌وی نفر اولی که تو لیست چت‌هاته و براش یه قلب قرمز بفرست، بعد بگو دستم خورد (شات واکنشش رو بیار).",
        "🎲 یه ویس بده و توش تیتراژ یه کارتون قدیمی (مثل باب اسفنجی یا لاک‌پشت‌های نینجا) رو بخون.",
        "🎲 تو یه ویس به زبان انگلیسی (با هر سطحی که هستی) خودت رو معرفی کن و بگو چرا اینجایی.",
        "🎲 یه عکس از داخل یخچال خونتون همین الان بفرست.",
        "🎲 روی یه تیکه کاغذ با دست مخالف (اگه راست‌دستی با چپ و برعکس) اسمت رو بنویس و عکسش رو بفرست.",
        "🎲 به آخرین کسی که بهت زنگ زده، اس ام اس بده 'کجایی؟ سریع بیا که خرابکاری کردم'.",
        "🎲 یه ویس بده و مثل مجری‌های رادیو، بچه‌های گروه رو به عنوان شنونده خطاب کن و یه پند اخلاقی بده.",
        "🎲 یه عکس از کیبورد کامپیوتر یا لپ‌تاپت عکس بده تا ببینیم چقدر تمیز یا کثیفه.",
        "🎲 یه ویس بده و توش صدای موتور یه ماشین اسپرت (مثل دوج چلنجر یا کامارو) رو با دهنت دربیار!",
        "🎲 از صفحه گیت‌هاب، لینکدین یا رزومه کاریت (اگه داری) یه شات بفرست ببینیم در چه حالی.",
        "🎲 وارد یه بازی آنلاین (مثل کالاف) شو، تو لابی یه اسکرین شات بگیر بفرست تا لولت رو ببینیم.",
        "🎲 به مدت ۳ دقیقه چشماتو ببند و سعی کن به پیام‌های گروه جواب بدی (غلط املایی‌ها رو پاک نکن).",
        "🎲 یکی از ویس‌های قدیمی خودت تو گروه رو پیدا کن و روش ریپلای بزن: 'وای چقدر صدام سم بوده'.",
        "🎲 از لیست اپلیکیشن‌هات یه شات بفرست تا ببینیم عجیب‌ترین برنامه‌ای که نصب داری چیه."
    ]
    challenges_would_you_rather = [
    "🎯 ترجیح می‌دی یه دوج چلنجر کلاسیک داشته باشی که فقط بتونی تو کوچه‌های شهر باهاش دور بزنی، یا یه پراید که بتونی باهاش کل دنیا رو مجانی بگردی؟",
    "🎯 هرچی می‌خوری مستقیم تبدیل به عضله بشه بدون اینکه نیاز باشه یه روز هم بری باشگاه، یا بتونی هرچقدر خواستی فست‌فود بخوری بدون اینکه یه گرم چربی بگیری؟",
    "🎯 قدت ۲ متر باشه ولی به شدت لاغر باشی، یا قدت ۱۶۰ باشه ولی یه هیکل به شدت روفرم و عضلانی داشته باشی؟",
    "🎯 بازی فینال رو تو استادیوم (مثلاً بازی تراکتور یا رئال) از نزدیک ببینی ولی تیم محبوبت ببازه، یا تو خونه تنها ببینی ولی تیمت قهرمان بشه؟",
    "🎯 یه روز کامل رو با بازیکنی مثل کریس رونالدو تمرین کنی ولی هیچی بهت یاد نده، یا با یه مربی معمولی تمرین کنی و تو یه هفته تبدیل به یه بازیکن حرفه‌ای بشی؟",
    "🎯 بتونی ذهن بقیه رو بخونی ولی نتونی هیچوقت دروغ بگی، یا بتونی نامرئی بشی ولی همیشه یه بوی گندی بدی که بقیه بفهمن اونجایی؟",
    "🎯 تو یه مچ حساس کالاف پینگت زیر ۱۰ باشه ولی هم‌تیمی‌هات به شدت نوب باشن، یا پینگت روی ۱۰۰ باشه ولی با پرو پلیرها هم‌تیمی بشی؟",
    "🎯 داداش یا خواهر کوچیکت وسط یه بازی به شدت حساس کنسول رو از برق بکشه، یا سیو گیمی که صد ساعت براش وقت گذاشتی بپره؟",
    "🎯 فقط بتونی عکس‌های پرتره هنری سیاه و سفید بگیری ولی کارت تو دنیا معروف بشه، یا بتونی هر عکسی با بهترین کیفیت بگیری ولی هیچکس هنرت رو نبینه؟",
    "🎯 یه میلیارد تومن پول نقد بگیری ولی نتونی به کسی بگی از کجا آوردی (همه فکر کنن دزدیه)، یا ماهی ده میلیون بگیری ولی همه فکر کنن میلیاردر هستی؟",
    "🎯 هر بار که دروغ میگی دماغت مثل پینوکیو دراز بشه، یا هر بار که کسی بهت دروغ میگه یه عطسه خیلی بلند بکنی؟",
    "🎯 تو یه جزیره متروکه با کسی که ازش متنفری گیر بیفتی، یا تو یه شهر شلوغ باشی ولی هیچکس نتونه صداتو بشنوه و باهات ارتباط بگیره؟",
    "🎯 همیشه یه حس خارش تو یه جای غیرقابل دسترس بدنت داشته باشی، یا همیشه حس کنی یه سنگریزه تو کفشته؟",
    "🎯 عشق اولت رو بعد از سال‌ها ببینی در حالی که خنده‌دارترین و زشت‌ترین تیپ ممکن رو زدی، یا اون تو رو تو بهترین حالتت ببینه ولی اسم تو رو یادش نیاد؟",
    "🎯 صدای خنده‌ت شبیه بوق تریلی باشه، یا موقع عطسه کردن صدای گربه بدی؟",
    "🎯 همه رازهای گوشیت برای خانواده‌ت فاش بشه، یا برای کل فالوورها و مخاطبینت تو شبکه‌های اجتماعی؟",
    "🎯 تو عروسی صمیمی‌ترین دوستت شلوارت پاره بشه، یا موقع حرف زدن تو یه جمع بزرگ یهو یادت بره چی می‌خواستی بگی و سوتی بدی؟",
    "🎯 ۱۰ سال به عمرت اضافه بشه ولی تو پیری و مریضی، یا تو ۴۰ سالگی بمیری ولی تا اون موقع تو اوج جوانی، سلامتی و قدرت بمونی؟",
    "🎯 همیشه ۵ دقیقه دیر به همه قرارها برسی و بقیه رو معطل کنی، یا همیشه نیم ساعت زودتر برسی و خودت الاف بشی؟",
    "🎯 حافظه کوتاه‌مدتت رو از دست بدی (مثل ماهی گلی هر روز یادت بره چی شده)، یا حافظه بلندمدتت پاک بشه (هیچ خاطره‌ای از بچگی و گذشته نداشته باشی)؟",
    "🎯 همیشه لباسات یه سایز برات کوچیک و تنگ باشن، یا دو سایز بزرگ و آویزون؟",
    "🎯 تا آخر عمرت فقط بتونی غذاهای به شدت تند بخوری، یا فقط غذاهای کاملا بی‌نمک و بی‌مزه؟",
    "🎯 توانایی پرواز کردن داشته باشی ولی فقط با سرعت پیاده‌روی، یا توانایی تله‌پورت کردن داشته باشی ولی هر بار که تله‌پورت می‌کنی لباسات جا بمونن؟",
    "🎯 با کسی ازدواج کنی که خیلی پولداره ولی اصلا دوستش نداری، یا با کسی که دیوانه‌وار عاشقشی ولی همیشه مشکل مالی دارید؟",
    "🎯 شریک زندگیت بهت خیانت کنه و خودت مچش رو بگیری، یا دوست صمیمیت بهت ثابت کنه که شریکت داره خیانت می‌کنه؟",
    "🎯 اکست با دوست صمیمیت رل بزنه، یا خودت با اکسِ دوست صمیمیت رل بزنی؟",
    "🎯 یه زندگی کوتاه ولی پر از هیجان، پول و ماجراجویی داشته باشی، یا یه زندگی خیلی طولانی ولی کاملا یکنواخت و بدون ریسک؟",
    "🎯 هر بار که از خواب بیدار میشی تو یه اتاق غریبه باشی، یا هر بار که می‌خوابی کابوس‌های وحشتناک ببینی؟",
    "🎯 بتونی با حیوانات حرف بزنی ولی اونا فقط بهت فحش بدن، یا بتونی با گیاهان حرف بزنی ولی اونا فقط از مشکلاتشون ناله کنن؟",
    "🎯 یه بازیگر/خواننده معروف بشی که همه تو فضای مجازی ازش متنفرن (هیتر داری)، یا یه آدم کاملاً معمولی باشی که تو محله خودش همه عاشقشن؟",
    "🎯 ده سال تو زندان باشی به خاطر جرمی که نکردی، یا ده سال در حال فرار باشی در حالی که واقعا جرم بزرگی مرتکب شدی؟",
    "🎯 همیشه بوی پیاز بدی ولی خودت متوجه نشی، یا همیشه حس کنی بوی پیاز میاد ولی بقیه بگن هیچ بویی نمیاد؟",
    "🎯 گوشی موبایلت با تمام اطلاعات و عکساش بیفته تو اقیانوس (بدون بکاپ)، یا بیفته دست کسی که ازش متنفری ولی قفل نباشه؟",
    "🎯 تو زمستون همیشه آب گرم حموم وسط کار قطع بشه، یا تو تابستون کولر اتاقت همیشه خراب باشه؟",
    "🎯 مجبور باشی همیشه با صدای بلند فکراتو به زبون بیاری، یا هیچوقت نتونی تو بحث‌ها از خودت دفاع کنی؟",
    "🎯 یک سال تمام نتونی موهات رو کوتاه کنی یا بهشون برسی، یا مجبور باشی همین الان کل موهات رو از ته بزنی؟",
    "🎯 توانایی این رو داشته باشی که دروغ آدم‌ها رو همون لحظه تشخیص بدی، یا بتونی احساسات واقعیشون نسبت به خودت رو بفهمی (حتی اگه تلخ باشه)؟",
    "🎯 بدترین دشمنت برنده یه جایزه ده میلیارد تومنی بشه، یا خودت فقط صد میلیون تومن ببری؟",
    "🎯 تو یه اتاق تاریک پر از مار گیر بیفتی، یا تو یه اتاق روشن ولی پر از سوسک‌های پرنده؟",
    "🎯 اسمت رو روی یه سیاره جدید بذارن، یا داروی یه بیماری لاعلاج رو به اسم تو ثبت کنن ولی پولی بهت ندن؟",
    "🎯 ترجیح میدی یه استعداد خارق‌العاده داشته باشی (مثلاً صدای بی‌نظیر) ولی هیچکس کشفت نکنه، یا هیچ استعدادی نداشته باشی ولی با پارتی بازی مشهور بشی؟",
    "🎯 همیشه مجبور باشی تو سینما ردیف اول بشینی، یا همیشه صندلی آخر باشی ولی یه نفر قدبلند جلوت نشسته باشه؟",
    "🎯 برای بقیه یه نصیحت‌کننده عالی باشی ولی زندگی خودت پر از اشتباه باشه، یا زندگی خودت بی‌نقص باشه ولی نتونی به هیچکس کمک فکری بدی؟",
    "🎯 ساعت خوابت دست خودت نباشه (هر لحظه ممکنه خوابت ببره)، یا هر وقت بخوای بخوابی باید حداقل ۲ ساعت تو جات غلت بزنی؟",
    "🎯 هر روز مجبور باشی نیم ساعت با یه آدم به شدت پرحرف و مخ‌خور حرف بزنی، یا یه هفته تو سکوت مطلق و تنهایی باشی؟",
    "🎯 رفیقت تو یه دعوا مقصر صددرصد باشه، پشتش درمیای و با بقیه دعوا می‌کنی، یا می‌کشی کنار و میگی حقته؟"
]
    from random import choice as ch

    if text == "حقیقت":
        await update.reply(ch(challenges_truth))

    elif text == "جرات":
        await update.reply(ch(challenges_dare))

    elif text == "دوراهی":
        await update.reply(ch(challenges_would_you_rather))

    elif text in ["چلنج", "شانسی", "چالش"]:
        # ترکیب همه لیست‌ها برای حالت رندوم کلی
        all_challenges = challenges_truth + challenges_dare + challenges_would_you_rather
        await update.reply(ch(all_challenges))

bot.run()
