
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
    user_guid TEXT PRIMARY KEY,
    title TEXT
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
     



    # wellcome
    if update.message.text == "یک عضو از طریق لینک به گروه افزوده شد." and update.message.type != "Text":
        await update.reply("به گروه خوش اومدی.")
    if update.message.text == "یک عضو گروه را ترک کرد." and update.message.type != "Text":
        await update.reply("درم ببند." )


    # check admin
    if await update.is_admin(update.object_guid,update.user_guid):

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
 

        # join group
        #anti link

    if update.author_object_guid == "u0HXkpO07ea05449373fa9cfa8b81b65":
        if update.reply_message_id and text.startswith("لقب"):
            target = await update.get_reply_author(update.object_guid, update.message.reply_to_message_id)
            target_guid = target.user.user_guid
            title = text.replace("لقب", "").strip()

            # ثبت یا آپدیت در دیتابیس
            cursor.execute("REPLACE INTO titles (user_guid, title) VALUES (?, ?)", (target_guid, title))
            conn.commit()

            await update.reply(f"لقب جدید ثبت شد: {title} برای {target.user.first_name}")

    if text == "لقب من":
        if result:
            await update.reply(f"لقب شما: {result[0]}")
        else:
            await update.reply("برای شما لقبی ثبت نشده.")

    ping_msg = ["مامان منو ندیدین","چقدر صدام میکنی یارو","نفس","بابای منو ندیدین","بگو کار دارم"]
    #super admin
    if True:
        if text == "ping" or text == "ربات" or text == "پینگ":
            if result[0]:
                await update.reply(f"جوونم {result[0]}")
            else:
                a = randint(0,4)
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
    if re.search(r'(https?://|www\.)\S+\.(com|ir)|بیو|@', text, re.IGNORECASE):
        user_guid = update.user_guid
        author_info = await update.get_author(update.author_object_guid)
        username = author_info.chat.last_message.author_title or "کاربر"
        

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

        # حذف پیام و اعلام اخطار
        await update.reply(f"❌ اخطار {warning_count}/3 به {username} به دلیل ارسال لینک")
        await update.delete()

        # اگر بیشتر از ۳ بار شد → بن
        if warning_count >= 3:
            await update.ban_member(update.object_guid, update.user_guid)
            await update.reply(f"🚫 {username} به دلیل ۳ بار تخلف، بن شد.")

bot.run()

