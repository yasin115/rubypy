from rubpy import Client, filters
from rubpy.types import Update
import re

bot = Client(name='rubpy')

@bot.on_message_updates(filters.text)
async def updates(update: Update):
    text = update.message.text

    # --- ضد لینک ---
    if re.search(r'(https?://|www\.)\S+\.(com|ir)|بیو', text, re.IGNORECASE):
        await update.reply('اخطار')
        await update.delete()
        

    # --- دستور بن فقط توسط ادمین ---
        # await update.reply(bot.get_group_admin_members(update.object_guid))
    if re.search(r'اسم جدید', text, re.IGNORECASE):
    
        await bot.edit_group_info(update.object_guid,text[8:])


bot.run()