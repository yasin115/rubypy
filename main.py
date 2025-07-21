from rubpy import Client, filters
from rubpy.types import Update
import re
# import sqlite3

# conn = sqlite3.connect('data.db')
# cursor = conn.cursor()

bot = Client(name='rubpy')

@bot.on_message_updates(filters.text)
async def updates(update: Update):
    admins = await bot.get_group_admin_members(update.object_guid)
    text = update.message.text
    name = await update.get_author(update.object_guid)
    author_reply = await update.get_reply_author(update.object_guid,str(update.message.reply_to_message_id))

    # check admin access
    for admin in admins.in_chat_members:
        if admin.member_guid == update.message.author_object_guid:
                
            # pin message
            if 'پین' == text or 'pin' == text:
                await update.pin(update.object_guid,update.message.reply_to_message_id)
                await update.reply("done")
            
            # ban user    
            if 'بن' == text or "سیک" == text or "ریمو" == text:
                await update.ban_member(update.object_guid,author_reply.user.user_guid)
                await update.reply(str("done"))
            
            # if text == "حذف پیام ها":
            #     update.reply(update.get_messages(update.object_guid))
                # update.delete_messages(update.object_guid,1000)
            break
        # check normal user            
        else:
        
            # anti link
            if re.search(r'(https?://|www\.)\S+\.(com|ir)|بیو', text, re.IGNORECASE):
                await update.reply('اخطار‍' 
                                #    + str(name.chat.last_message.type)
                                   )
                await update.delete()


bot.run()