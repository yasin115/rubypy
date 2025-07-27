from rubpy import Client, filters
from rubpy.types import Update
import re
# import sqlite3

# conn = sqlite3.connect('data.db')
# cursor = conn.cursor()

bot = Client(name='rubpy')

@bot.on_message_updates(filters.text)
async def updates(update: Update):
    text = update.message.text
    name = await update.get_author(update.object_guid)
    
    # wellcome
    if update.message.text == "یک عضو از طریق لینک به گروه افزوده شد." and update.message.type != "Text":
        await update.reply("به گروه خوش اومدی")
    if update.message.text == "یک عضو گروه را ترک کرد." and update.message.type != "Text":
        await update.reply("سیکتیر کن عزیزم" )
    
    
    # check admin
    if await update.is_admin(update.object_guid,update.user_guid):
        
        # pin message
        if 'پین' == text or 'pin' == text:
            await update.pin(update.object_guid,update.message.reply_to_message_id)
            await update.reply("done")
        if update.reply_message_id != None:
            # ban user
            if 'بن' == text or "سیک" == text or "ریمو" == text:
                author_reply = await update.get_reply_author(update.object_guid,update.message.reply_to_message_id)
                await update.ban_member(update.object_guid,author_reply.user.user_guid)
                await update.reply(str("done"))
    else:
        
        # join group
        #anti link
        if re.search(r'(https?://|www\.)\S+\.(com|ir)|بیو', text, re.IGNORECASE):
            await update.reply(' اخطار‍ ' 
                                        + str(name.chat.last_message.author_title)
                                        )
            await update.delete()
   

bot.run()