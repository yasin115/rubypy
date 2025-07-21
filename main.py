from rubpy import Client, filters
from rubpy.types import Update
import re

bot = Client(name='rubpy')

@bot.on_message_updates(filters.text)
async def updates(update: Update):
    admins = await bot.get_group_admin_members(update.object_guid)
    text = update.message.text
    name = await update.get_author(update.object_guid)

    # check admin access
    for admin in admins.in_chat_members:
        if admin.member_guid == update.message.author_object_guid:
                
            #change group name
            if re.search(r'اسم جدید', text, re.IGNORECASE):
                await bot.edit_group_info(update.object_guid,text[8:])
                
            break
        # check normal user            
        else:
        
            # anti link
            if re.search(r'(https?://|www\.)\S+\.(com|ir)|بیو', text, re.IGNORECASE):
                await update.reply('اخطار ‍' + str(name['chat']['last_message']["author_title"]))
                await update.delete()


bot.run()