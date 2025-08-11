from rubpy import Client, filters
from rubpy.types import Update
import re
import aiohttp
from deep_translator import GoogleTranslator
import random
import sqlite3
import jdatetime  # برای تاریخ شمسی
import datetime

conn = sqlite3.connect('data.db',check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS welcome_messages (
    chat_guid TEXT PRIMARY KEY,
    message TEXT
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


conn.commit()




async def get_challenge():
    # انتخاب تصادفی بین truth و dare
    challenge_type = random.choice(['truth', 'dare'])
    url = f"https://api.truthordarebot.xyz/api/{challenge_type}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                text_en = data.get('question', '')
                # ترجمه به فارسی
                text_fa = GoogleTranslator(source='auto', target='fa').translate(text_en)
                prefix = "🧠 حقیقت" if challenge_type == 'truth' else "🎯 جرئت"
                return f"{prefix}: {text_fa}"
            else:
                return "❌ خطا در دریافت چالش"
bot = Client(name='rubpy')







active_voice_chats = {}

@bot.on_message_updates(filters.text)
async def updates(update: Update ):
    text = update.message.text.strip()
    name = await update.get_author(update.object_guid)
    user_guid = update.author_guid
    user_name = name.chat.last_message.author_title or "کاربر"
    chat_guid = update.object_guid  # شناسه گروه
    admin_or_not = await bot.user_is_admin(update.object_guid, update.author_object_guid)

    # --- مهم: مقداردهی پیش‌فرض تا UnboundLocalError پیش نیاد ---
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


    now_ts = int(datetime.datetime.now().timestamp())
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
    
    
    
    # تابع برای تشخیص ویس چت فعال
    
    if text == "کال" and admin_or_not:
        try:
            # بررسی وجود ویس چت فعال
            if chat_guid in active_voice_chats:
                await update.reply("⚠️ از قبل یک ویس چت فعال دارید!")
                return
                
            result = await bot.create_group_voice_chat(group_guid=chat_guid)
            
            # ذخیره اطلاعات ویس چت
            active_voice_chats[chat_guid] = {
                'voice_chat_id': result.voice_chat_id,
                'title': 'ویس چت گروه'
            }
            
            await update.reply("🎤 ویس چت با موفقیت ایجاد شد!\nبرای پیوستن از دکمه ویس چت در گروه استفاده کنید.")
        except Exception as e:
            await update.reply(f"❌ خطا در ایجاد ویس چت: {str(e)}")



    if text == "تایم":
        now = datetime.datetime.now()
        current_time = now.strftime("%H:%M:%S")
        await update.reply(f"⏰ ساعت فعلی: {current_time}")

    if text == "تاریخ":
        today_jalali = jdatetime.date.today()
        date_str = today_jalali.strftime("%Y/%m/%d")
        await update.reply(f"📅 تاریخ امروز (شمسی): {date_str}")
   

    # سکوت عادی یا زمان‌دار
    if update.reply_message_id and text.startswith("سکوت"):
        admin_check = await bot.user_is_admin(chat_guid, user_guid)
        if admin_check:
            target = await update.get_reply_author(chat_guid, update.message.reply_to_message_id)
            target_guid = target.user.user_guid
            target_name = target.user.first_name or "کاربر"

            parts = text.split()
            until_ts = None
            if len(parts) == 2 and parts[1].isdigit():  # مثال: سکوت 5
                minutes = int(parts[1])
                until_ts = int((datetime.datetime.now() + datetime.timedelta(minutes=minutes)).timestamp())

            cursor.execute("INSERT OR REPLACE INTO mutes (user_guid, chat_guid, until) VALUES (?, ?, ?)",
                        (target_guid, chat_guid, until_ts))
            conn.commit()

            if until_ts:
                await update.reply(f"🔇 {target_name} به مدت {minutes} دقیقه ساکت شد.")
            else:
                await update.reply(f"🔇 {target_name} در این گروه ساکت شد (دائمی).")
        else:
            await update.reply("❗ فقط ادمین‌ها می‌توانند سکوت بدهند.")

    # حذف سکوت
    if update.reply_message_id and text == "حذف سکوت":
        admin_check = await bot.user_is_admin(chat_guid, user_guid)
        if admin_check:
            target = await update.get_reply_author(chat_guid, update.message.reply_to_message_id)
            target_guid = target.user.user_guid
            target_name = target.user.first_name or "کاربر"

            cursor.execute("DELETE FROM mutes WHERE user_guid = ? AND chat_guid = ?", (target_guid, chat_guid))
            conn.commit()
            await update.reply(f"🔊 سکوت {target_name} برداشته شد.")
        else:
            await update.reply("❗ فقط ادمین‌ها می‌توانند سکوت کاربر را بردارند.")

    if text.startswith("ثبت پاسخ "):
        if await bot.user_is_admin(chat_guid, user_guid):
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
        if await bot.user_is_admin(chat_guid, user_guid):
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

# ثبت اخطار دستی (فقط ادمین‌ها)
    if update.reply_message_id and text == "اخطار":
        admin_check = await bot.user_is_admin(chat_guid, user_guid)
        if admin_check:
            target = await update.get_reply_author(update.object_guid, update.message.reply_to_message_id)
            target_guid = target.user.user_guid
            target_name = target.user.first_name or "کاربر"

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

            # اگر تعداد اخطار ۳ یا بیشتر شد، بن کن
            if warning_count >= 3:
                try:
                    await update.ban_member(update.object_guid, target_guid)
                    await update.reply(f"🚫 {target_name} به دلیل ۳ بار اخطار، بن شد.")
                except Exception as e:
                    await update.reply(f"❗️خطا در بن کردن {target_name}: {str(e)}")
        else:
            await update.reply("❗ فقط ادمین‌ها می‌توانند اخطار ثبت کنند.")



    # آمار من
    if text == "آمار من":
        cursor.execute("SELECT message_count FROM stats WHERE user_guid = ? AND chat_guid = ?", (user_guid, chat_guid))
        msg_row = cursor.fetchone()

        cursor.execute("SELECT title FROM titles WHERE user_guid = ? AND chat_guid = ?", (user_guid, chat_guid))
        title_row = cursor.fetchone()

        msg_count = msg_row[0] if msg_row else 0
        title = title_row[0] if title_row else "ثبت نشده"

        await update.reply(f"📊 آمار شما:\nپیام‌ها: {msg_count}\nلقب: {title}")

    # welcome messages (همون‌طور که بود)
    if update.message.text == "یک عضو از طریق لینک به گروه افزوده شد." and update.message.type == "Event":
        cursor.execute("SELECT message FROM welcome_messages WHERE chat_guid = ?", (chat_guid,))
        result = cursor.fetchone()

        if result:
            await update.reply(result[0])
        else:
            await update.reply("به گروه خوش اومدی 🌹")

    if update.message.text == "یک عضو گروه را ترک کرد." and update.message.type != "Text":
        await update.reply("درم ببند.")

    # check admin


    if admin_or_not:
        # ... (دستورات ادمین مثل آمار کلی، پین، بن) بدون تغییر منطقی
        if text == "آمار کلی":
            cursor.execute("SELECT user_guid, name, message_count FROM stats WHERE chat_guid = ? ORDER BY message_count DESC LIMIT 3", (chat_guid,))
            top_users = cursor.fetchall()
            if top_users:
                msg = "🏆 آمار ۳ نفر اول در این گروه:\n"
                for i, (u_guid, name_, count) in enumerate(top_users, start=1):
                    msg += f"{i}. {name_} → {count} پیام\n"
                await update.reply(msg)
            else:
                await update.reply("هیچ آماری ثبت نشده.")
        if 'پین' == text or 'pin' == text or text == "سنجاق":
            await update.pin(update.object_guid, update.message.reply_to_message_id)
            await update.reply("سنجاق شد")
        if update.reply_message_id is not None:
            if text in ('بن', 'سیک', 'ریمو'):
                author_reply = await update.get_reply_author(update.object_guid, update.message.reply_to_message_id)
                await update.ban_member(update.object_guid, author_reply.user.user_guid)
                first_name = name.chat.last_message.author_title or "کاربر"
                await update.reply(f'{first_name} بن شد.')

    # حذف اخطار (ریپلای)
        if update.reply_message_id and text == "حذف اخطار":
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
        if admin_or_not:  # بررسی اینکه کاربر ادمین باشه
            welcome_text = text.replace("ثبت خوشامد ", "", 1)
            cursor.execute("REPLACE INTO welcome_messages (chat_guid, message) VALUES (?, ?)", (chat_guid, welcome_text))
            conn.commit()
            await update.reply("پیام خوشامدگویی برای این گروه ثبت شد ✅")
        else:
            await update.reply("فقط ادمین می‌تواند پیام خوشامدگویی ثبت کند ❌")

    # anti-link (فقط وقتی کاربر ادمین نیست)
    if re.search(r'(https?://|www\.)\S+\.(com|ir)|@', text, re.IGNORECASE) and not admin_or_not:
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

        reply_msg = await update.reply(f"❌ اخطار {warning_count}/3 به {username} به دلیل ارسال لینک")
        await update.delete()

        if warning_count >= 3:
            try:
                await update.ban_member(update.object_guid, update.author_guid)
                await update.reply(f"🚫 {username} به دلیل ۳ بار تخلف، بن شد.")
            except Exception as e:
                await update.reply(f"❗️خطا در بن کردن {username}: {str(e)}")
        else:
            import asyncio
            await asyncio.sleep(5)
            await bot.delete_messages(update.object_guid, [reply_msg.message_id])
    if "بیو" in text:
        await update.delete()
    # ثبت مالک (با ریپلای) - مثل سابق
    if update.reply_message_id and text == "ثبت مالک":
        admin_check = await bot.user_is_admin(chat_guid, user_guid)
        if admin_check:
            try:
                reply_author = await update.get_reply_author(chat_guid, update.message.reply_to_message_id)
                target_guid = reply_author.user.user_guid
                target_name = reply_author.user.first_name or "کاربر"

                cursor.execute("REPLACE INTO group_info (chat_guid, owner_guid) VALUES (?, ?)", (chat_guid, target_guid))
                conn.commit()
                await update.reply(f"✅ {target_name} به عنوان مالک گروه ثبت شد.")
            except Exception as e:
                await update.reply(f"❗ خطا در ثبت مالک: {str(e)}")
        else:
            await update.reply("❗ فقط ادمین‌ها می‌تونن مالک رو تنظیم کنن.")
    # حذف لقب (فقط مدیر ربات)
    if update.author_object_guid == "u0HXkpO07ea05449373fa9cfa8b81b65":
        if update.reply_message_id and text == "حذف لقب":
            target = await update.get_reply_author(update.object_guid, update.message.reply_to_message_id)
            target_guid = target.user.user_guid
            cursor.execute("DELETE FROM titles WHERE user_guid = ? AND chat_guid = ?", (target_guid, chat_guid))
            conn.commit()
            await update.reply(f"لقب کاربر {target.user.first_name} حذف شد.")

    # حذف پیام خوشامدگویی (فقط ادمین‌ها)
    if text == "حذف خوشامد":
        admin_check = await bot.user_is_admin(chat_guid, user_guid)
        if admin_check:
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
    if update.author_object_guid == "u0HXkpO07ea05449373fa9cfa8b81b65":
        if update.reply_message_id and text.startswith("تنظیم لقب"):
            target = await update.get_reply_author(update.object_guid, update.message.reply_to_message_id)
            target_guid = target.user.user_guid
            title = text.replace("تنظیم لقب", "").strip()
            cursor.execute("REPLACE INTO titles (user_guid,chat_guid, title) VALUES (?, ?, ?)", (target_guid, chat_guid, title))
            conn.commit()
            await update.reply(f"لقب جدید ثبت شد: {title} برای {target.user.first_name}")

    # بررسی لقب با ریپلای
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

    # لقبت من (حالا کوئری درست انجام میشه)
    if text == "لقب من":
        cursor.execute("SELECT title FROM titles WHERE user_guid = ? AND chat_guid = ?", (user_guid, chat_guid))
        result = cursor.fetchone()
        if result:
            await update.reply(f"لقب شما: {result[0]}")
        else:
            await update.reply("برای شما لقبی ثبت نشده.")

    # ping — دقت: result فقط داخل این بلوک مقداردهی و استفاده میشه
    ping_msg = ["مامان منو ندیدین","چقدر صدام میکنی یارو","نفس","خواهش کن جوابتو بدم","بگو کار دارم"]
    if text in ["ping", "ربات", "پینگ"]:
        cursor.execute("SELECT title FROM titles WHERE user_guid = ? AND chat_guid = ?", (user_guid, chat_guid))
        result = cursor.fetchone()
        if result:
            await update.reply(f"جوونم {result[0]}")
        else:
            await update.reply(random.choice(ping_msg))

    # بقیه پیام‌های ساده
    hi_msg = ["سلام زیبا","های","بخواب بچه","سلام دختری؟","دیر اومدی داریم میبندیم"]
    if text in ("سلام", "سلامم"):
        await update.reply(hi_msg[random.randint(0,4)])
    if text == "شب بخیر":
        await update.reply("خوب بخوابی :)")

    if text == "امار":
        data = await bot.get_info(update.object_guid)
        filter = data.group.count_members
        await bot.send_message("u0Gfirp0efb1e13736a9714fe315f443", str(filter))

    if text in ("بای", "فعلا"):
        await update.reply("میری؟ بیا اینم با خودت ببر.")

    help_general = """
    📚 راهنمای کلی ربات مدیریت گروه Rubpy 📚

    سلام! برای استفاده از ربات می‌تونی از این دستورات استفاده کنی:

    1. مدیریت لقب‌ها  
    برای اطلاعات بیشتر بنویس: راهنمای لقب

    2. مدیریت پیام‌ها و خوشامدگویی  
    برای اطلاعات بیشتر بنویس: راهنمای خوشامد

    3. اخطار و بن کردن کاربران  
    برای اطلاعات بیشتر بنویس: راهنمای اخطار

    4. آمار و اطلاعات  
    برای اطلاعات بیشتر بنویس: راهنمای آمار

    5. لینک و مدیریت گروه  
    برای اطلاعات بیشتر بنویس: راهنمای لینک

    6. چالش و سرگرمی  
    برای اطلاعات بیشتر بنویس: راهنمای چالش

    اگر سوالی داشتی یا مشکلی بود با سازنده ربات @yasin_309 تماس بگیر.
    """

    help_titles = """
    👑 مدیریت لقب‌ها

    - ثبت لقب فقط توسط سازنده ربات انجام می‌شود.  
    - برای ثبت لقب با سازنده هماهنگ باشید.  
    - مشاهده لقب خودتان: لقب من  
    - مشاهده لقب دیگران (ریپلای روی پیامشان): لقبش چیه  
    """

    help_welcome = """
    🚀 مدیریت پیام‌ها و خوشامدگویی

    - ثبت پیام خوشامدگویی (فقط ادمین‌ها):  
    ثبت خوشامد [متن پیام]  
    - حذف پیام خوشامدگویی (فقط ادمین‌ها):  
    حذف خوشامد  
    """

    help_warning = """
    ⚠️ اخطار و بن کردن کاربران

    - دادن اخطار دستی (فقط ادمین‌ها، ریپلای روی پیام کاربر و نوشتن):  
    اخطار  
    - حذف اخطار (ریپلای روی پیام کاربر و نوشتن):  
    حذف اخطار  
    - بعد از ۳ اخطار کاربر به صورت خودکار بن می‌شود.  
    - بن کردن دستی (ادمین‌ها، ریپلای و نوشتن یکی از این‌ها):  
    بن  
    سیک  
    ریمو  
    """

    help_stats = """
    📊 آمار و اطلاعات

    - مشاهده آمار شخصی:  
    آمار من  
    - مشاهده آمار کلی گروه (فقط ادمین‌ها):  
    آمار کلی  
    - مشاهده مالک گروه:  
    مالک  
    - ثبت مالک گروه (فقط ادمین‌ها، ریپلای و نوشتن):  
    ثبت مالک  
    """

    help_links = """
    🔗 لینک و مدیریت گروه

    - دریافت لینک گروه:  
    لینک  
    - ارسال لینک توسط کاربران عادی اخطار دارد و بعد از ۳ بار بن خواهند شد.
    """

    help_challenge = """
    🎲 چالش و سرگرمی

    - دریافت چالش جدید (حقیقت یا جرئت):  
    چالش  
    یا  
    چالش جدید  
    """

    if text == "راهنما":
        await update.reply(help_general)
    elif text == "راهنمای لقب":
        await update.reply(help_titles)
    elif text == "راهنمای خوشامد":
        await update.reply(help_welcome)
    elif text == "راهنمای اخطار":
        await update.reply(help_warning)
    elif text == "راهنمای آمار":
        await update.reply(help_stats)
    elif text == "راهنمای لینک":
        await update.reply(help_links)
    elif text == "راهنمای چالش":
        await update.reply(help_challenge)


    if text in ["چالش", "چالش جدید"]:
        challenge = await get_challenge()
        await update.reply(challenge)




bot.run()