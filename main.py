
import logging
import aiosqlite
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatInviteLink
from telegram.constants import ParseMode, ChatMemberStatus
from telegram.ext import Application, CommandHandler, ContextTypes, JobQueue
from keep_alive import keep_alive

# ==========================================
# ⚙️ CONFIGURATION (यहाँ अपना टोकन डाल)
# ==========================================
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
UPDATES_CHANNEL_URL = "https://t.me/Ss_GodX"  
SUPPORT_GROUP_URL = "https://t.me/Ss_GodX"    

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ==========================================
# 📦 HTML BLOCKQUOTE TEMPLATES 
# ==========================================
START_TEXT = """
<blockquote><b>⚡ ᴘᴜʙʟɪᴄ ʟɪɴᴋ ᴄʜᴀɴɢᴇʀ • ᴏғғɪᴄɪᴀʟ ⚡</b>

<b>🛡️ ᴡʜᴀᴛ ɪs ᴛʜɪs ʙᴏᴛ?</b>
• High-speed channel security & routing engine.
• Generates single-use 59-second auto-expiring links.
• Protects channels from unauthorized link sharing.
• 24/7 automated join-request management.

<b>⚙️ ᴀᴅᴍɪɴ ᴄᴏᴍᴍᴀɴᴅs:</b>
• /addch : Connect a channel node
• /links : Generate 59s auto-expire links
• /reqlink : Generate permanent request links
• /channels : View connected nodes

⚡ <i>Tap below to join our channel or get support!</i></blockquote>
"""

ADDCH_TEXT = """
<blockquote><b>⚡ ᴄʜᴀɴɴᴇʟ ɴᴏᴅᴇ • ᴄᴏɴɴᴇᴄᴛᴇᴅ ⚡</b>

<b>📢 ᴄʜᴀɴɴᴇʟ ᴅᴇᴛᴀɪʟs:</b>
• Title: {title}
• Node ID: <code>{ch_id}</code>

🚀 <i>Node is now live and protected!</i></blockquote>
"""

LINKS_TEXT = """
<blockquote><b>🔗 sᴇᴄᴜʀᴇ ɪɴᴠɪᴛᴇ ʟɪɴᴋ • ɢᴇɴᴇʀᴀᴛᴇᴅ ⚡</b>

<b>📢 ɴᴏᴅᴇ ɪɴғᴏ:</b>
• Channel: {title}

<b>⏱️ ᴇxᴘɪʀᴀᴛɪᴏɴ ᴄᴏᴜɴᴛᴅᴏᴡɴ:</b>
• Timer: 59 Seconds
• Link: {link}

⚠️ <i>Link will be revoked & deleted automatically!</i></blockquote>
"""

async def init_db():
    async with aiosqlite.connect("link_changer.db") as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                channel_id TEXT PRIMARY KEY,
                title TEXT
            )
        """)
        await db.commit()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("📢 Updates Channel", url=UPDATES_CHANNEL_URL),
            InlineKeyboardButton("💬 Support", url=SUPPORT_GROUP_URL)
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        text=START_TEXT, reply_markup=reply_markup, parse_mode=ParseMode.HTML, disable_web_page_preview=True
    )

async def addch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        await update.message.reply_text("<blockquote>⚠️ Provide channel ID: <code>/addch -100123456789</code></blockquote>", parse_mode=ParseMode.HTML)
        return
    channel_id = context.args[0]
    try:
        chat = await context.bot.get_chat(channel_id)
        bot_member = await chat.get_member(context.bot.id)
        if bot_member.status != ChatMemberStatus.ADMINISTRATOR or not bot_member.can_invite_users:
            await update.message.reply_text("<blockquote>⚠️ <b>Error:</b> Bot must be an admin with 'Invite Users' permission!</blockquote>", parse_mode=ParseMode.HTML)
            return
        async with aiosqlite.connect("link_changer.db") as db:
            await db.execute("INSERT OR REPLACE INTO channels (channel_id, title) VALUES (?, ?)", (channel_id, chat.title))
            await db.commit()
        await update.message.reply_text(text=ADDCH_TEXT.format(title=chat.title, ch_id=channel_id), parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"<blockquote>⚠️ <b>Connection Failed:</b> {str(e)}</blockquote>", parse_mode=ParseMode.HTML)

async def revoke_and_delete(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    try:
        await context.bot.revoke_chat_invite_link(chat_id=job.data['channel_id'], invite_link=job.data['invite_link'])
        await context.bot.delete_message(chat_id=job.data['chat_id'], message_id=job.data['message_id'])
    except Exception as e:
        logging.error(f"Error revoking link: {e}")

async def links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with aiosqlite.connect("link_changer.db") as db:
        async with db.execute("SELECT channel_id, title FROM channels") as cursor:
            channels = await cursor.fetchall()
    if not channels:
        await update.message.reply_text("<blockquote>⚠️ No channels found. Please use /addch first.</blockquote>", parse_mode=ParseMode.HTML)
        return
    for ch_id, title in channels:
        try:
            invite: ChatInviteLink = await context.bot.create_chat_invite_link(chat_id=ch_id, creates_join_request=False)
            msg = await update.message.reply_text(text=LINKS_TEXT.format(title=title, link=invite.invite_link), parse_mode=ParseMode.HTML, disable_web_page_preview=True)
            context.job_queue.run_once(
                revoke_and_delete, when=59, data={'channel_id': ch_id, 'invite_link': invite.invite_link, 'chat_id': msg.chat_id, 'message_id': msg.message_id}
            )
        except Exception as e:
            await update.message.reply_text(f"<blockquote>⚠️ Failed: {e}</blockquote>", parse_mode=ParseMode.HTML)

def main():
    asyncio.run(init_db())
    keep_alive()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addch", addch))
    app.add_handler(CommandHandler("links", links))
    print("🚀 Private Link Changer Bot is Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
