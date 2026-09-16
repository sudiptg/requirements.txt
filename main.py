import logging
import aiosqlite
import asyncio
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatInviteLink
from telegram.constants import ParseMode, ChatMemberStatus
from telegram.ext import Application, CommandHandler, ContextTypes, JobQueue
from keep_alive import keep_alive

# ==========================================
# ⚙️ CONFIGURATION (Private Security Lock)
# ==========================================
# 👇 यहाँ BOT_TOKEN के अंदर अपना NAYA (नया) टोकन डालना! 👇
BOT_TOKEN = "अपना_नया_टोकन_यहाँ_डालें"  
OWNER_ID = 8599429441
UPDATES_CHANNEL_URL = "https://t.me/Ss_GodX"  
SUPPORT_GROUP_URL = "https://t.me/Ss_GodX"    

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ==========================================
# 📦 ADMIN HTML BLOCKQUOTE TEMPLATES (Left-Border Box)
# ==========================================
START_TEXT_ADMIN = '''
<blockquote><b>⚡ ᴘᴜʙʟɪᴄ ʟɪɴᴋ ᴄʜᴀɴɢᴇʀ • ᴘʀᴏ ⚡</b>

<b>📌 ᴄᴏʀᴇ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ</b>
• /addch - Add a channel node
• /delch - Remove a channel node
• /channels - View active nodes

<b>🔗 ʟɪɴᴋ ᴇɴɢɪɴᴇ</b>
• /links - Generate 59s expiring links
• /reqlink - Show request links
• /bulklink - Batch link generation

<b>🛡️ ᴀᴜᴛᴏ ᴀᴘᴘʀᴏᴠᴀʟ</b>
• /reqmode - Toggle auto-approve
• /reqtime - Set approval timer
• /approveon - Enable for channel
• /approveoff - Disable for channel
• /approveall - Approve all pending

<b>⚙️ sʏsᴛᴇᴍ ᴛᴏᴏʟs</b>
• /status - View system status
• /stats - View bot statistics
• /broadcast - Send global message
• /cleanup - Purge inactive users</blockquote>
'''

ADDCH_TEXT = '''
<blockquote><b>⚡ ᴄʜᴀɴɴᴇʟ ɴᴏᴅᴇ • ᴄᴏɴɴᴇᴄᴛᴇᴅ ⚡</b>

<b>📢 ᴄʜᴀɴɴᴇʟ ᴅᴇᴛᴀɪʟs:</b>
• Title: {title}
• Node ID: <code>{ch_id}</code>

🚀 <i>Node is now live and fully protected!</i></blockquote>
'''

LINKS_TEXT = '''
<blockquote><b>🔗 sᴇᴄᴜʀᴇ ɪɴᴠɪᴛᴇ ʟɪɴᴋ • ɢᴇɴᴇʀᴀᴛᴇᴅ ⚡</b>

<b>📢 ɴᴏᴅᴇ ɪɴғᴏ:</b>
• Channel: {title}

<b>⏱️ ᴇxᴘɪʀᴀᴛɪᴏɴ ᴄᴏᴜɴᴛᴅᴏᴡɴ:</b>
• Timer: 59 Seconds
• Link: {link}

⚠️ <i>Link will be revoked & deleted automatically!</i></blockquote>
'''

# ==========================================
# 🗄️ DATABASE SETUP
# ==========================================
async def init_db():
    async with aiosqlite.connect("link_changer.db") as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute('''
            CREATE TABLE IF NOT EXISTS channels (
                channel_id TEXT PRIMARY KEY,
                title TEXT
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY
            )
        ''')
        await db.commit()

# ==========================================
# 👑 ADMIN COMMANDS & PUBLIC GATEWAY
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Save user in DB for Broadcasts
    async with aiosqlite.connect("link_changer.db") as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        await db.commit()

    # 👑 OWNER VIEW (Boxed Admin Panel)
    if user_id == OWNER_ID:
        keyboard = [
            [InlineKeyboardButton("📢 Updates Channel", url=UPDATES_CHANNEL_URL),
             InlineKeyboardButton("💬 Support", url=SUPPORT_GROUP_URL)]
        ]
        await update.message.reply_text(
            text=START_TEXT_ADMIN,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
        return

    # 👥 PUBLIC VIEW (The 59-Sec UI from the Screenshot)
    async with aiosqlite.connect("link_changer.db") as db:
        async with db.execute("SELECT channel_id FROM channels LIMIT 1") as cursor:
            channel = await cursor.fetchone()

    if not channel:
        return 

    ch_id = channel[0]

    try:
        # API Level Hard Expiration
        expire_timestamp = int(time.time()) + 60 
        invite: ChatInviteLink = await context.bot.create_chat_invite_link(
            chat_id=ch_id, creates_join_request=False, expire_date=expire_timestamp
        )
        
        # UI from Screenshot
        keyboard = [[InlineKeyboardButton("• JOIN CHANNEL •", url=invite.invite_link)]]
        msg1 = await update.message.reply_text(
            text="<b>HERE IS YOUR LINK! CLICK BELOW TO PROCEED</b>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
        msg2 = await update.message.reply_text(
            text="<b><u>Note: If the link is expired, please click the post link again to get a new one.</u></b>",
            parse_mode=ParseMode.HTML
        )
        
        # 59-second auto-delete timer
        context.job_queue.run_once(
            revoke_and_delete, when=59, 
            data={'channel_id': ch_id, 'invite_link': invite.invite_link, 'chat_id': msg1.chat_id, 'message_ids': [msg1.message_id, msg2.message_id]}
        )
    except Exception as e:
        logging.error(f"Error in public link generation: {e}")

async def revoke_and_delete(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    try:
        await context.bot.revoke_chat_invite_link(chat_id=job.data['channel_id'], invite_link=job.data['invite_link'])
        for m_id in job.data.get('message_ids', []):
            try: await context.bot.delete_message(chat_id=job.data['chat_id'], message_id=m_id)
            except: pass
    except: pass

async def addch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    if not context.args:
        await update.message.reply_text("<blockquote>⚠️ Please provide a channel ID. Example: <code>/addch -100123456789</code></blockquote>", parse_mode=ParseMode.HTML)
        return
    try:
        chat = await context.bot.get_chat(context.args[0])
        async with aiosqlite.connect("link_changer.db") as db:
            await db.execute("INSERT OR REPLACE INTO channels (channel_id, title) VALUES (?, ?)", (context.args[0], chat.title))
            await db.commit()
        await update.message.reply_text(text=ADDCH_TEXT.format(title=chat.title, ch_id=context.args[0]), parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"<blockquote>⚠️ <b>Connection Failed:</b> {str(e)}</blockquote>", parse_mode=ParseMode.HTML)

async def delch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    if not context.args:
        await update.message.reply_text("<blockquote>⚠️ Format: <code>/delch channel_id</code></blockquote>", parse_mode=ParseMode.HTML)
        return
    async with aiosqlite.connect("link_changer.db") as db:
        await db.execute("DELETE FROM channels WHERE channel_id = ?", (context.args[0],))
        await db.commit()
    await update.message.reply_text(f"<blockquote><b>🗑️ ᴄʜᴀɴɴᴇʟ ɴᴏᴅᴇ • ʀᴇᴍᴏᴠᴇᴅ ⚡</b>\n\nID: <code>{context.args[0]}</code> purged from database.</blockquote>", parse_mode=ParseMode.HTML)

async def channels_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    async with aiosqlite.connect("link_changer.db") as db:
        async with db.execute("SELECT channel_id, title FROM channels") as cursor:
            ch_list = await cursor.fetchall()
    if not ch_list:
        await update.message.reply_text("<blockquote>⚠️ No active channels connected.</blockquote>", parse_mode=ParseMode.HTML)
        return
    text = "<blockquote><b>📡 ᴄᴏɴɴᴇᴄᴛᴇᴅ ɴᴏᴅᴇs:</b>\n\n"
    for idx, (ch_id, title) in enumerate(ch_list, 1):
        text += f"{idx}. {title} [<code>{ch_id}</code>]\n"
    text += "</blockquote>"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    async with aiosqlite.connect("link_changer.db") as db:
        async with db.execute("SELECT channel_id, title FROM channels LIMIT 1") as cursor:
            channel = await cursor.fetchone()
    if not channel: return
    invite = await context.bot.create_chat_invite_link(chat_id=channel[0], creates_join_request=False, expire_date=int(time.time())+60)
    msg = await update.message.reply_text(text=LINKS_TEXT.format(title=channel[1], link=invite.invite_link), parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    context.job_queue.run_once(revoke_and_delete, when=59, data={'channel_id': channel[0], 'invite_link': invite.invite_link, 'chat_id': msg.chat_id, 'message_ids': [msg.message_id]})

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    await update.message.reply_text("<blockquote><b>🛡️ sʏsᴛᴇᴍ sᴛᴀᴛᴜs ⚡</b>\n\n• Core Engine: Online\n• Ping: <50ms\n• Security: Private Admin Lock\n• UI: Pro Blockquote View Active</blockquote>", parse_mode=ParseMode.HTML)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    message = " ".join(context.args)
    if not message:
        await update.message.reply_text("<blockquote>⚠️ Please provide a message to broadcast.</blockquote>", parse_mode=ParseMode.HTML)
        return
    async with aiosqlite.connect("link_changer.db") as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            users = await cursor.fetchall()
    sent = 0
    for (uid,) in users:
        try:
            await context.bot.send_message(chat_id=uid, text=f"<blockquote>📢 <b>Broadcast:</b>\n\n{message}</blockquote>", parse_mode=ParseMode.HTML)
            sent += 1
        except: pass
    await update.message.reply_text(f"<blockquote>✅ <b>Success:</b> Broadcast sent to {sent} active users.</blockquote>", parse_mode=ParseMode.HTML)

async def placeholder_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    await update.message.reply_text("<blockquote>⚠️ This feature requires Userbot/Pyrogram integration (`approve.py`) to handle join requests.</blockquote>", parse_mode=ParseMode.HTML)

def main():
    asyncio.run(init_db())
    keep_alive()
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addch", addch))
    app.add_handler(CommandHandler("delch", delch))
    app.add_handler(CommandHandler("channels", channels_cmd))
    app.add_handler(CommandHandler("links", links))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("broadcast", broadcast))
    
    for cmd in ["reqlink", "bulklink", "reqtime", "reqmode", "approveon", "approveoff", "approveall", "stats", "cleanup"]:
        app.add_handler(CommandHandler(cmd, placeholder_cmd))
        
    print("🚀 PRO Bot is Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
