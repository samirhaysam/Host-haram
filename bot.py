import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import os
import subprocess
import time
import logging
import json
import random
import string
import sys
import signal
from datetime import datetime

print("🚀 بدء تحميل البوت (النسخة الكاملة المحدثة)...")

# ========== إعدادات البوت ==========
BOT_CONFIG = {
    "token": os.getenv("BOT_TOKEN", "8294494311:AAFizYlueq-vNPh_20W_agpXijONPmX7sDQ"),
    "admin_users": [int(os.getenv("ADMIN_ID", 1056328647))],
    "settings": {
        "max_file_size": 50 * 1024 * 1024,  # 50MB
    },
    "paths": {
        "upload_folder": "uploads",
        "pending_folder": "pending",
        "logs_folder": "logs",
        "data_file": "bot_data.json"
    }
}

TOKEN = BOT_CONFIG["token"]
ADMIN_USERS = BOT_CONFIG["admin_users"]
SETTINGS = BOT_CONFIG["settings"]
PATHS = BOT_CONFIG["paths"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, PATHS["upload_folder"])
LOGS_FOLDER = os.path.join(BASE_DIR, PATHS["logs_folder"])
PENDING_FOLDER = os.path.join(BASE_DIR, PATHS["pending_folder"])
DATA_FILE = os.path.join(BASE_DIR, PATHS["data_file"])

for folder in [UPLOAD_FOLDER, LOGS_FOLDER, PENDING_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(BASE_DIR, "bot.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ========== إدارة البيانات ==========
def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"خطأ في تحميل البيانات: {e}")
    return {
        "active_bots": {},
        "users": {},
        "pending_files": {},
        "approved_files": {},
        "rejected_files": {},
        "admin_users": ADMIN_USERS
    }

def save_data():
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(bot_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"خطأ في حفظ البيانات: {e}")

bot_data = load_data()
active_bots = bot_data.get("active_bots", {})
users_data = bot_data.get("users", {})
pending_files = bot_data.get("pending_files", {})
approved_files = bot_data.get("approved_files", {})
rejected_files = bot_data.get("rejected_files", {})
admin_users = bot_data.get("admin_users", [])

print(f"👥 المشرفين: {admin_users}")

# ========== التحقق من التوكن ==========
if not TOKEN or TOKEN == "YOUR_BOT_TOKEN_HERE":
    print("❌ خطأ: التوكن غير صالح!")
    sys.exit(1)

try:
    bot = telebot.TeleBot(TOKEN, threaded=False)
    bot_info = bot.get_me()
    print(f"✅ البوت جاهز: @{bot_info.username}")
except Exception as e:
    print(f"❌ فشل في إنشاء البوت: {e}")
    sys.exit(1)

# ========== وظائف مساعدة ==========
def is_admin(user_id):
    return user_id in admin_users

def generate_file_id():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

def check_process_running(pid):
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False

def run_bot_script(file_path, user_id):
    try:
        log_file = os.path.join(LOGS_FOLDER, f"{os.path.basename(file_path)}_{int(time.time())}.log")
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'

        with open(log_file, 'w') as log:
            process = subprocess.Popen(
                ['python3', file_path],
                stdout=log,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid,
                cwd=os.path.dirname(file_path),
                env=env
            )
        return process.pid
    except Exception as e:
        logger.error(f"فشل تشغيل الملف: {e}")
        return str(e)

def stop_bot_process(pid):
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(1)
        if check_process_running(pid):
            os.kill(pid, signal.SIGKILL)
        return True
    except Exception as e:
        logger.error(f"فشل إيقاف العملية {pid}: {e}")
        return False

# ========== الكيبوردات ==========
def main_keyboard(user_id):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        KeyboardButton("📤 رفع ملف"),
        KeyboardButton("📁 ملفاتي"),
        KeyboardButton("ℹ️ المساعدة"),
        KeyboardButton("📺 قناتي")
    ]
    if is_admin(user_id):
        buttons.append(KeyboardButton("👑 لوحة التحكم"))
    keyboard.add(*buttons)
    return keyboard

def admin_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("⏳ الملفات المنتظرة"),
        KeyboardButton("🔵 البوتات النشطة"),
        KeyboardButton("🏠 الرئيسية")
    )
    return keyboard

def create_approval_keyboard(file_id):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("✅ قبول", callback_data=f"approve_{file_id}"),
        InlineKeyboardButton("❌ رفض", callback_data=f"reject_{file_id}")
    )
    return keyboard

def create_bot_control_keyboard(pid):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("🛑 إيقاف", callback_data=f"stop_{pid}"),
        InlineKeyboardButton("🗑️ حذف", callback_data=f"delete_{pid}")
    )
    return keyboard

# ========== معالجة الأوامر ==========
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
        f"مرحباً {message.from_user.first_name}! 🤖\nأرسل ملف بايثون (.py) لرفعه.",
        reply_markup=main_keyboard(message.from_user.id)
    )

@bot.message_handler(func=lambda m: m.text == "📺 قناتي")
def my_channel(m):
    bot.send_message(m.chat.id, "يمكنك زيارة قناتي: https://t.me/Haram_2002")

@bot.message_handler(func=lambda m: m.text == "ℹ️ المساعدة")
def help_msg(m):
    bot.send_message(m.chat.id, "أرسل ملف .py لرفعه. سيتم مراجعته من قبل المشرف.")

@bot.message_handler(func=lambda m: m.text == "📁 ملفاتي")
def my_files(m):
    user_id = m.from_user.id
    all_files = {**pending_files, **approved_files, **rejected_files}
    user_files = [(fid, info) for fid, info in all_files.items() if info.get('user_id') == user_id]

    if not user_files:
        bot.send_message(m.chat.id, "لا يوجد لديك ملفات.")
        return

    for fid, info in user_files:
        status = "✅ معتمد" if fid in approved_files else ("❌ مرفوض" if fid in rejected_files else "⏳ بانتظار")
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🗑️ حذف", callback_data=f"delete_{fid}"))
        bot.send_message(
            m.chat.id,
            f"📁 {info['file_name']}\n({status})",
            reply_markup=keyboard
        )

@bot.message_handler(func=lambda m: m.text == "👑 لوحة التحكم")
def admin_panel(m):
    if is_admin(m.from_user.id):
        bot.send_message(m.chat.id, "لوحة التحكم:", reply_markup=admin_keyboard())
    else:
        bot.send_message(m.chat.id, "غير مصرح لك!")

@bot.message_handler(func=lambda m: m.text == "⏳ الملفات المنتظرة")
def pending_list(m):
    if not is_admin(m.from_user.id):
        bot.send_message(m.chat.id, "غير مصرح لك!")
        return
    if not pending_files:
        bot.send_message(m.chat.id, "لا يوجد ملفات بانتظار المراجعة.")
        return
    for fid, info in pending_files.items():
        bot.send_message(
            m.chat.id,
            f"📄 {info['file_name']}\n👤 {info['user_name']}",
            reply_markup=create_approval_keyboard(fid)
        )

@bot.message_handler(func=lambda m: m.text == "🔵 البوتات النشطة")
def list_active_bots(m):
    if not is_admin(m.from_user.id):
        bot.send_message(m.chat.id, "غير مصرح لك!")
        return
    if not active_bots:
        bot.send_message(m.chat.id, "لا يوجد بوتات نشطة.")
        return
    for pid, info in active_bots.items():
        bot.send_message(
            m.chat.id,
            f"🤖 **{info['file_name']}**\n🆔 PID: `{pid}`\n👤 {info['user_name']}",
            parse_mode='Markdown',
            reply_markup=create_bot_control_keyboard(pid)
        )

@bot.message_handler(func=lambda m: m.text == "🏠 الرئيسية")
def back_home(m):
    bot.send_message(m.chat.id, "الرئيسية:", reply_markup=main_keyboard(m.from_user.id))

@bot.message_handler(func=lambda m: m.text == "📤 رفع ملف")
def upload_file(m):
    bot.send_message(m.chat.id, "أرسل ملف بايثون (.py) الآن.")

@bot.message_handler(content_types=['document'])
def handle_document(message):
    doc = message.document
    if not (doc.file_name and doc.file_name.endswith('.py')):
        bot.reply_to(message, "❌ يرجى إرسال ملف بايثون فقط (.py)")
        return

    if doc.file_size > SETTINGS["max_file_size"]:
        bot.reply_to(message, "❌ حجم الملف كبير جدًا (الحد الأقصى: 50MB)")
        return

    file_id = generate_file_id()
    file_path = os.path.join(PENDING_FOLDER, f"{file_id}_{doc.file_name}")

    file_info = bot.get_file(doc.file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    with open(file_path, 'wb') as f:
        f.write(downloaded_file)

    pending_files[file_id] = {
        'file_name': doc.file_name,
        'file_path': file_path,
        'user_id': message.from_user.id,
        'user_name': message.from_user.first_name,
        'upload_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'status': 'pending'
    }

    user_id_str = str(message.from_user.id)
    if user_id_str not in users_
        users_data[user_id_str] = {'first_name': message.from_user.first_name, 'files_uploaded': 0}
    users_data[user_id_str]['files_uploaded'] += 1

    save_data()

    for admin in admin_users:
        try:
            bot.send_message(
                admin,
                f"ملف جديد بانتظار المراجعة:\n📁 `{doc.file_name}`\n👤 {message.from_user.first_name}",
                parse_mode='Markdown',
                reply_markup=create_approval_keyboard(file_id)
            )
        except Exception as e:
            logger.warning(f"فشل إرسال إشعار للمشرف {admin}: {e}")

    bot.reply_to(message, f"✅ تم استلام الملف!\nمعرف الملف: `{file_id}`\n⏳ بانتظار الموافقة.", parse_mode='Markdown')

# ========== معالجة الأزرار ==========
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if call.data.startswith('approve_'):
        file_id = call.data.split('_')[1]
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "غير مصرح لك!")
            return
        if file_id not in pending_files:
            bot.answer_callback_query(call.id, "الملف غير موجود!")
            return

        info = pending_files[file_id]
        new_path = os.path.join(UPLOAD_FOLDER, info['file_name'])
        os.rename(info['file_path'], new_path)

        pid = run_bot_script(new_path, info['user_id'])
        if isinstance(pid, int):
            info['file_path'] = new_path
            info['pid'] = pid
            info['status'] = 'approved'
            approved_files[file_id] = info
            active_bots[pid] = {**info, 'file_id': file_id}
            del pending_files[file_id]
            save_data()
            bot.edit_message_text("✅ تم قبول الملف وتشغيله!", call.message.chat.id, call.message.message_id)
            bot.send_message(info['user_id'], f"🎉 تم قبول ملفك: `{info['file_name']}`", parse_mode='Markdown')
        else:
            bot.answer_callback_query(call.id, f"فشل التشغيل: {pid}")

    elif call.data.startswith('reject_'):
        file_id = call.data.split('_')[1]
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "غير مصرح لك!")
            return
        if file_id not in pending_files:
            bot.answer_callback_query(call.id, "الملف غير موجود!")
            return

        info = pending_files[file_id]
        del pending_files[file_id]
        rejected_files[file_id] = info
        save_data()
        try:
            os.remove(info['file_path'])
        except:
            pass
        bot.edit_message_text("❌ تم رفض الملف.", call.message.chat.id, call.message.message_id)
        bot.send_message(info['user_id'], f"😔 تم رفض ملفك: `{info['file_name']}`", parse_mode='Markdown')

    elif call.data.startswith('stop_'):
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "غير مصرح لك!")
            return
        pid = int(call.data.split('_')[1])
        if pid not in active_bots:
            bot.answer_callback_query(call.id, "البوت غير نشط!")
            return

        if stop_bot_process(pid):
            bot_info = active_bots[pid]
            del active_bots[pid]
            save_data()
            bot.edit_message_text(
                f"🛑 تم إيقاف البوت:\n📁 `{bot_info['file_name']}`",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown'
            )
            try:
                bot.send_message(bot_info['user_id'], f"🛑 تم إيقاف بوتك: `{bot_info['file_name']}`")
            except:
                pass
        else:
            bot.answer_callback_query(call.id, "فشل الإيقاف!")

    elif call.data.startswith('delete_'):
        if not is_admin(call.from_user.id):
            # السماح للمستخدم بحذف ملفاته الخاصة فقط
            pass  # سيتم التحقق من الملكية لاحقًا

        identifier = call.data.split('_')[1]
        if identifier.isdigit():
            # حذف بوت نشط (pid)
            pid = int(identifier)
            if pid in active_bots:
                bot_info = active_bots[pid]
                if not is_admin(call.from_user.id) and bot_info['user_id'] != call.from_user.id:
                    bot.answer_callback_query(call.id, "غير مصرح لك!")
                    return
                stop_bot_process(pid)
                try:
                    os.remove(bot_info['file_path'])
                except:
                    pass
                del active_bots[pid]
                for fid, info in list(approved_files.items()):
                    if info.get('pid') == pid:
                        del approved_files[fid]
                        break
                save_data()
                bot.edit_message_text(
                    f"🗑️ تم حذف البوت:\n📁 `{bot_info['file_name']}`",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='Markdown'
                )
                if bot_info['user_id'] != call.from_user.id:
                    try:
                        bot.send_message(bot_info['user_id'], f"🗑️ تم حذف بوتك: `{bot_info['file_name']}`")
                    except:
                        pass
            else:
                bot.answer_callback_query(call.id, "البوت غير موجود!")
        else:
            # حذف ملف (file_id)
            file_id = identifier
            file_info = None
            src = None
            if file_id in pending_files:
                file_info = pending_files[file_id]
                src = 'pending'
            elif file_id in approved_files:
                file_info = approved_files[file_id]
                src = 'approved'
            elif file_id in rejected_files:
                file_info = rejected_files[file_id]
                src = 'rejected'

            if file_info:
                if not is_admin(call.from_user.id) and file_info['user_id'] != call.from_user.id:
                    bot.answer_callback_query(call.id, "غير مصرح لك بحذف هذا الملف!")
                    return
                try:
                    os.remove(file_info['file_path'])
                except:
                    pass
                if src == 'pending':
                    del pending_files[file_id]
                elif src == 'approved':
                    del approved_files[file_id]
                elif src == 'rejected':
                    del rejected_files[file_id]
                save_data()
                bot.edit_message_text(
                    f"🗑️ تم حذف الملف:\n📁 `{file_info['file_name']}`",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='Markdown'
                )
            else:
                bot.answer_callback_query(call.id, "الملف غير موجود!")

# ========== التشغيل ==========
if __name__ == "__main__":
    print("🔄 تشغيل البوت...")
    try:
        bot.polling(none_stop=False, interval=2, timeout=20)
    except KeyboardInterrupt:
        print("\n🛑 تم الإيقاف يدويًا.")
    except Exception as e:
        print(f"❌ خطأ: {e}")