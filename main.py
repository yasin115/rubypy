from random import randint
from rubpy import Client, filters
from rubpy.types import Update
import re


# import sqlite3

# conn = sqlite3.connect('data.db')
# cursor = conn.cursor()

bot = Client(name='rubpy')

@bot.on_message_updates(filters.text)
async def updates(update: Update ):
    text = update.message.text
    name = await update.get_author(update.object_guid)
    
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
    else:
        
        # join group
        #anti link
        if re.search(r'(https?://|www\.)\S+\.(com|ir)|بیو', text, re.IGNORECASE):
            await update.reply(' اخطار‍ ' 
                                        + str(name.chat.last_message.author_title)
                                        )
            await update.delete()
   
    ping_msg = ["pong","ربات فعال است ...","جوون"]
    #super admin
    if update.user_guid == "u0Gfirp0efb1e13736a9714fe315f443":
        if text == "ping" or text == "ربات" or text == "پینگ":
            a = randint(0,2)
            await update.reply(ping_msg[a])
        if text == "امار":
            data = await bot.get_info(update.object_guid)
            filter = data.group.count_members
            await bot.send_message("u0Gfirp0efb1e13736a9714fe315f443",str(filter))

        if update.message.text == "ارسال به همه":
            await update.send_message(update.chat_id,"سلام دنیا!")
    
    #help 
    if text == "راهنما":
        await update.reply("""
                     دستور های فعلی ربات :
                     
                     ربات / پینگ => فعال بودن ربات
                     بن / سیک / ریمو => حذف کاربر
                     سنجاق => سنجاق پیام ریپلای شده
                    
                    ربات رو باید ادمین کنید تا کار کنه در غیر اینصورت کار نخواهد کرد
                    خوشامدگویی خودکار داره و لینک هارو پاک میکنه و اخطار میده
                     """)
bot.run()