from random import randint
from rubpy import Client, filters
from rubpy.types import Update
import re

import sqlite3

conn = sqlite3.connect('data.db')
cursor = conn.cursor()

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

# جدول اخطار کاربران
cursor.execute("""
CREATE TABLE IF NOT EXISTS warnings (
    user_guid TEXT PRIMARY KEY,
    count INTEGER
)
""")

conn.commit()

bot = Client(name='rubpy')

@bot.on_message_updates(filters.text)
async def updates(update: Update ):
    text = update.message.text
    name = await update.get_author(update.object_guid)
    # ثبت یا افزایش شمارش پیام برای کاربر
    user_guid = update.author_guid

    user_name = name.chat.last_message.author_title or "کاربر"

    chat_guid = update.object_guid  # شناسه گروه


    cursor.execute("SELECT message_count FROM stats WHERE user_guid = ? AND chat_guid = ?", (user_guid, chat_guid))
    row = cursor.fetchone()

    if row:
        new_count = row[0] + 1
        cursor.execute("UPDATE stats SET message_count = ?, name = ? WHERE user_guid = ? AND chat_guid = ?", (new_count, user_name, user_guid, chat_guid))
    else:
        cursor.execute("INSERT INTO stats (user_guid, chat_guid, name, message_count) VALUES (?, ?, ?, ?)", (user_guid, chat_guid, user_name, 1))

    conn.commit()


    import random
    cursor.execute("SELECT title FROM titles WHERE user_guid = ?", (update.author_object_guid,))
    result = cursor.fetchone() or [None]
    truth_challenges = [
    "🧠 حقیقت: تا حالا به کسی که دوستش داشتی دروغ گفتی؟",
    "💔 حقیقت: آخرین باری که دلت شکست کی بود؟",
    "😳 حقیقت: خجالت‌آورترین کاری که کردی چی بوده؟",
    "🙄 حقیقت: تا حالا وانمود کردی کسی رو دوست داری؟",
    "🕵️‍♂️ حقیقت: آخرین بار کی رو یواشکی چک کردی؟",
    "📱 حقیقت: آخرین پیام خجالت‌آور تو گوشیت چیه؟",
    "🤐 حقیقت: رازی داری که هیچ‌کس ندونه؟",
    "😬 حقیقت: کسی هست که وانمود می‌کنی خوشت نمیاد ولی درواقع خوشت میاد؟",
    "😅 حقیقت: آخرین دروغ بزرگی که گفتی چی بود؟",
    "🤔 حقیقت: از کدوم دوست یا فامیل مخفیانه متنفری؟",
    "👀 حقیقت: آخرین باری که گریه کردی کی بود؟",
    "💤 حقیقت: تا حالا وسط حرف کسی خواب رفتی؟",
    "🧏‍♀️ حقیقت: تا حالا شده فقط وانمود کنی داری گوش می‌دی؟",
    "📸 حقیقت: آخرین عکسی که گرفتی رو الان نشون می‌دی؟",
    "📚 حقیقت: تا حالا تقلب کردی و لو نرفتی؟",
    "💬 حقیقت: بدترین حرفی که به کسی زدی چی بوده؟",
    "🧃 حقیقت: چیزی رو خوردی که بعدش پشیمون شدی؟",
    "🎧 حقیقت: آهنگی که گوش می‌دی ولی نمی‌خوای کسی بدونه چیه؟",
    "😈 حقیقت: شیطون‌ترین کاری که کردی چی بوده؟",
    "🎭 حقیقت: تا حالا وانمود کردی کسی نیستی؟"
]

    dare_challenges = [
    "📞 جرئت: به یکی زنگ بزن و بگو دوستت دارم و قطع کن!",
    "🖼️ جرئت: یه عکس خجالت‌آور از گالریت رو تو گروه بفرست.",
    "👣 جرئت: پروفایلتو به مدت ۵ دقیقه بذار عکس کفشت!",
    "🎤 جرئت: صدای خنده مصنوعی ضبط کن و بفرست.",
    "😂 جرئت: یه جوک خیلی بی‌مزه تعریف کن!",
    "💃 جرئت: یه ویدیو ۵ ثانیه‌ای برقص و بفرست.",
    "🎨 جرئت: با چشم بسته یه چیز بکش و نشون بده.",
    "🙃 جرئت: یه پیام به اشتباه به کسی بفرست و بعد توضیح نده!",
    "🕺 جرئت: جلوی آینه ادا دربیار و بفرست.",
    "🛑 جرئت: یه پیام بده به معلم یا مدیر قدیمی‌ات!",
    "🤳 جرئت: بدون فیلتر یه عکس سلفی الان بگیر.",
    "📢 جرئت: یه فریاد ضبطی بفرست.",
    "🎲 جرئت: گوشی رو بده به نفر کناری تا یه پیام به انتخاب خودش بفرسته.",
    "🧊 جرئت: یه تیکه یخ بذار روی صورتت و عکس بگیر.",
    "📺 جرئت: یه صحنه سریال رو بازی کن و ضبط کن.",
    "🙄 جرئت: ده بار پشت سر هم بگو «من عاشق خودمم» و ضبط کن.",
    "📴 جرئت: گوشیتو به مدت ۵ دقیقه بذار روی حالت پرواز.",
    "🧦 جرئت: یه عکس از جورابات بفرست.",
    "💌 جرئت: یه نامه عاشقانه برای یه شخصیت کارتونی بنویس.",
    "🎁 جرئت: بگو کدوم یکی از اعضای گروهو می‌خوای کادو بگیری."
]

    all_challenges = truth_challenges + dare_challenges

# تابع هندلر برای استفاده در بات rubpy
    if "چالش حقیقت"  == text:
        challenge = random.choice(truth_challenges)
        await update.reply(challenge)
    elif "چالش جرئت"  ==  text or text == "چالش جرعت":
        challenge = random.choice(dare_challenges)
        await update.reply(challenge)
    elif "چالش"  == text:
        challenge = random.choice(all_challenges)
        await update.reply(challenge)



    if text == "آمار من":
        # گرفتن تعداد پیام‌ها فقط در این گروه
        cursor.execute("SELECT message_count FROM stats WHERE user_guid = ? AND chat_guid = ?", (user_guid, chat_guid))
        msg_row = cursor.fetchone()

        # گرفتن لقب در همین گروه
        cursor.execute("SELECT title FROM titles WHERE user_guid = ? AND chat_guid = ?", (user_guid, chat_guid))
        title_row = cursor.fetchone()

        msg_count = msg_row[0] if msg_row else 0
        title = title_row[0] if title_row else "ثبت نشده"

        await update.reply(f"📊 آمار شما:\nپیام‌ها: {msg_count}\nلقب: {title}")

    # wellcome
    if update.message.text == "یک عضو از طریق لینک به گروه افزوده شد." and update.message.type != "Text":
        await update.reply("به گروه خوش اومدی.")
    if update.message.text == "یک عضو گروه را ترک کرد." and update.message.type != "Text":
        await update.reply("درم ببند." )


    # check admin
    admin_or_not = await bot.user_is_admin(update.object_guid,update.author_object_guid)

    if admin_or_not:
        if text == "آمار کلی" and admin_or_not:
            cursor.execute("""
            SELECT user_guid, name, message_count 
            FROM stats 
            WHERE chat_guid = ? 
            ORDER BY message_count DESC 
            LIMIT 7
        """, (chat_guid,))
            top_users = cursor.fetchall()

            if top_users:
                msg = "🏆 آمار ۷ نفر اول در این گروه:\n"
                for i, (u_guid, name, count) in enumerate(top_users, start=1):
                    display_name = "شما" if u_guid == user_guid else name
                    msg += f"{i}. {display_name} → {count} پیام\n"
                await update.reply(msg)
            else:
                await update.reply("هیچ آماری ثبت نشده.")
        # pin message
        if 'پین' == text or 'pin' == text or text == "سنجاق":
            await update.pin(update.object_guid,update.message.reply_to_message_id)
            await update.reply("سنجاق شد")
        if update.reply_message_id != None:
            # ban user
            if 'بن' == text or "سیک" == text or "ریمو" == text :
                author_reply = await update.get_reply_author(update.object_guid,update.message.reply_to_message_id)
                await update.ban_member(update.object_guid,author_reply.user.user_guid)
                first_name = name.chat.last_message.author_title or "کاربر"

                text = f'{first_name} بن شد.'
                await update.reply(text)

                # await update.reply(f"{name.chat.last_message.author_title} بن شد.")

    if update.reply_message_id and text == "حذف اخطار":
            target = await update.get_reply_author(update.object_guid, update.message.reply_to_message_id)
            target_guid = target.user.user_guid
            target_name = target.user.first_name or "کاربر"

            # بررسی وجود اخطار
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

        # join group
        #anti link
    else:
     if re.search(r'(https?://|www\.)\S+\.(com|ir)|بیو|@', text, re.IGNORECASE) and not admin_or_not:
        user_guid = update.author_guid
        author_info = await update.get_author(update.object_guid)
        username = author_info.chat.last_message.author_title or "کاربر"
        print(username)

        # دریافت تعداد اخطار فعلی
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
        await update.delete()  # حذف پیام لینک‌دار کاربر

# اگر بیشتر از یا مساوی ۳ اخطار شد → بن
        if warning_count >= 3:
            try:
                await update.ban_member(update.object_guid, update.author_guid)
                await update.reply(f"🚫 {username} به دلیل ۳ بار تخلف، بن شد.")
            except Exception as e:
                await update.reply(f"❗️خطا در بن کردن {username}: {str(e)}")
        else:
    # حذف پیام اخطار بعد از چند ثانیه
            import asyncio
            await asyncio.sleep(5)
            await bot.delete_messages(update.object_guid, [reply_msg.message_id])

        # اگر بیشتر از یا مساوی ۳ اخطار شد → بن
        if warning_count >= 3:
            try:
                await update.ban_member(update.object_guid, update.author_guid)
                await update.reply(f"🚫 {username} به دلیل ۳ بار تخلف، بن شد.")
            except Exception as e:
                await update.reply(f"❗️خطا در بن کردن {username}: {str(e)}")

    # کاهش یک اخطار توسط ادمین با ریپلای

    # فقط مدیران بتونن مالک رو تنظیم کنن

    if "لینک گروه" in text or text == "لینک":
        try:
             link_data = await bot.get_group_link(chat_guid)
             if link_data and link_data['join_link']:
                await update.reply(f"🔗 لینک گروه:\n{link_data['join_link']}")
             else:
                await update.reply("❗ لینکی برای این گروه وجود ندارد یا ساخته نشده.")
        except Exception as e:
            await update.reply(f"❗ خطا در دریافت لینک گروه: {str(e)}")
    if "مالک" in text:
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
    if update.author_object_guid == "u0HXkpO07ea05449373fa9cfa8b81b65":
        if update.reply_message_id and text == "ثبت مالک":
            admin_check = await bot.user_is_admin(chat_guid, user_guid)
        if admin_check:
            try:
            # گرفتن آیدی کسی که روش ریپلای شده
                reply_author = await update.get_reply_author(chat_guid, update.message.reply_to_message_id)
                target_guid = reply_author.user.user_guid
                target_name = reply_author.user.first_name or "کاربر"

            # ذخیره در دیتابیس
                cursor.execute("REPLACE INTO group_info (chat_guid, owner_guid) VALUES (?, ?)", (chat_guid, target_guid))
                conn.commit()

                await update.reply(f"✅ {target_name} به عنوان مالک گروه ثبت شد.")
            except Exception as e:
                await update.reply(f"❗ خطا در ثبت مالک: {str(e)}")
        else:
            await update.reply("❗ فقط ادمین‌ها می‌تونن مالک رو تنظیم کنن.")
        if update.reply_message_id and text.startswith("تنظیم لقب"):
            target = await update.get_reply_author(update.object_guid, update.message.reply_to_message_id)
            target_guid = target.user.user_guid
            title = text.replace("تنظیم لقب", "").strip()

            # ثبت یا آپدیت در دیتابیس
            cursor.execute("REPLACE INTO titles (user_guid,chat_guid, title) VALUES (?, ?, ?)", (target_guid, chat_guid,title))
            conn.commit()

            await update.reply(f"لقب جدید ثبت شد: {title} برای {target.user.first_name}")
    # بررسی لقب با ریپلای
    if update.reply_message_id and text == "لقبش چیه":
        target = await update.get_reply_author(update.object_guid, update.message.reply_to_message_id)
        target_guid = target.user.user_guid
        target_name = target.user.first_name or "کاربر"

        # دریافت لقب از دیتابیس
        cursor.execute("SELECT title FROM titles WHERE user_guid = ?", (target_guid,))
        result = cursor.fetchone()

        if result:
            await update.reply(f" {result[0]}")
        else:
            await update.reply(f"ℹ️ برای {target_name} لقبی ثبت نشده.")

    if text == "لقب من":
        if result:
            await update.reply(f"لقب شما: {result[0]}")
        else:
            await update.reply("برای شما لقبی ثبت نشده.")

    ping_msg = ["مامان منو ندیدین","چقدر صدام میکنی یارو","نفس","خواهش کن جوابتو بدم",f"جون دلم {result[0]}","بگو کار دارم"]
    #super admin
    if True:
        if text == "ping" or text == "ربات" or text == "پینگ":
            if result[0]:
                await update.reply(f"جوونم {result[0]}")
            else:
                a = randint(0,5)
                await update.reply(ping_msg[a])
                #await update.reply(str(update))
        hi_msg =["سلام زیبا","های","بخواب بچه","سلام دختری؟","دیر اومدی داریم میبندیم"]
        if text == "سلام" or text == "سلامم":
            # await update.reply(str(update))
            await update.reply(hi_msg[random.randint(0,4)])
       # if update.author_object_guid == "u0HXkpO07ea05449373fa9cfa8b81b65":
           # await update.reply("i worship you")    
        if text == "شب بخیر":
            await update.reply("خوب بخوابی :)")
        if text == "امار":
         #   await update.reply(str(update))
            data = await bot.get_info(update.object_guid)
            filter = data.group.count_members
            await bot.send_message("u0Gfirp0efb1e13736a9714fe315f443",str(filter))

    if text == "بای" or text == "فعلا":
        await update.reply("میری؟ بیا اینم با خودت ببر.")
    #help 
    if text == "راهنما":
        await update.reply("""
        دستور های فعلی ربات :
                     
ربات / پینگ => فعال بودن ربات

بن / سیک / ریمو => حذف کاربر

سنجاق => سنجاق پیام ریپلای شده

چالش سه نوع داره => چالش حقیقت ، چالش جرعت ، چالش (ترکیبی از هردو)
                    
 ربات رو باید ادمین کنید تا کار کنه در غیر اینصورت کار نخواهد کرد
                     """)

bot.run()
