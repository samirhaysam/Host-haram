import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import os
import subprocess
import time
import logging
import threading
import signal
import json
import random
import string
import sys
from datetime import datetime

print("🚀 بدء تحميل البوت...")

# ========== إعدادات البوت ==========
BOT_CONFIG = {
    "token": os.getenv("BOT_TOKEN", "8445840908:AAGarKrlQXhLug7IM8O320Dofg6jZiIeLso"),  # 🔹 ضع توكن البوت هنا أو عبر متغيرات البيئة
    "admin_users": [int(os.getenv("ADMIN_ID", 1056328647))],  # 🔹 ضع آيديك هنا أو عبر متغيرات البيئة
    "settings": {
        "auto_approve": False,
        "max_files_per_user": 5,
        "max_file_size": 50 * 1024 * 1024,
        "allowed_extensions": [".py"],
        "cleanup_interval": 86400,
        "log_retention_days": 7
    },
    "paths": {
        "upload_folder": "uploads",
        "pending_folder": "pending",
        "logs_folder": "logs",
        "data_file": "bot_data.json"
    }
}

# تطبيق الإعدادات
TOKEN = BOT_CONFIG["token"]
ADMIN_USERS = BOT_CONFIG["admin_users"]
SETTINGS = BOT_CONFIG["settings"]
PATHS = BOT_CONFIG["paths"]

# المجلدات الأساسية
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, PATHS["upload_folder"])
LOGS_FOLDER = os.path.join(BASE_DIR, PATHS["logs_folder"])
PENDING_FOLDER = os.path.join(BASE_DIR, PATHS["pending_folder"])
DATA_FILE = os.path.join(BASE_DIR, PATHS["data_file"])

# إنشاء المجلدات
for folder in [UPLOAD_FOLDER, LOGS_FOLDER, PENDING_FOLDER]:
    os.makedirs(folder, exist_ok=True)
    print(f"✅ إنشاء مجلد: {folder}")

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(BASE_DIR, "bot.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ========== إدارة البيانات ==========
def load_data():
    """تحميل البيانات المحفوظة"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"خطأ في تحميل البيانات: {e}")

    return {
        "active_bots": {},
        "users": {},
        "files": {},
        "pending_files": {},
        "approved_files": {},
        "rejected_files": {},
        "admin_users": ADMIN_USERS,
        "settings": SETTINGS
    }

def save_data():
    """حفظ البيانات"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(bot_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"خطأ في حفظ البيانات: {e}")

# تحميل البيانات
bot_data = load_data()
active_bots = bot_data.get("active_bots", {})
users_data = bot_data.get("users", {})
files_data = bot_data.get("files", {})
pending_files = bot_data.get("pending_files", {})
approved_files = bot_data.get("approved_files", {})
rejected_files = bot_data.get("rejected_files", {})
admin_users = bot_data.get("admin_users", [])
settings = bot_data.get("settings", {})

print(f"👥 المشرفين: {admin_users}")

# ========== إعداد البوت مع معالجة أخطاء محسنة ==========
if TOKEN == "YOUR_BOT_TOKEN_HERE":
    print("❌ خطأ: لم تقم بتغيير التوكن!")
    sys.exit(1)

try:
    # إعداد البوت مع خيارات متقدمة
    bot = telebot.TeleBot(TOKEN, threaded=True, num_threads=5)

    # اختبار الاتصال
    bot_info = bot.get_me()
    print(f"✅ تم إنشاء كائن البوت بنجاح: @{bot_info.username}")

except Exception as e:
    print(f"❌ فشل في إنشاء البوت: {e}")
    sys.exit(1)

# ========== الكيبوردات ==========
def main_keyboard(user_id):
    """لوحة المفاتيح الرئيسية"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

    buttons = [
        KeyboardButton("📨 الرسالة"),
        KeyboardButton("📺 قناتي"),
        KeyboardButton("📤 رفع ملف"),
        KeyboardButton("📁 ملفاتي"),
        KeyboardButton("ℹ️ المساعدة"),
        KeyboardButton("📊 الحالة")
    ]

    # للمشرفين فقط
    if is_admin(user_id):
        buttons.append(KeyboardButton("👑 لوحة التحكم"))

    keyboard.add(*buttons)
    return keyboard

def admin_keyboard():
    """لوحة المفاتيح الخاصة بالمشرفين"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

    buttons = [
        KeyboardButton("⏳ الملفات المنتظرة"),
        KeyboardButton("🔵 البوتات النشطة"),
        KeyboardButton("👥 المستخدمين"),
        KeyboardButton("⚙️ الإعدادات"),
        KeyboardButton("📊 الإحصائيات"),
        KeyboardButton("🏠 الرئيسية")
    ]

    keyboard.add(*buttons)
    return keyboard

def back_to_main_keyboard(user_id):
    """زر العودة للرئيسية"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("🏠 الرئيسية"))
    return keyboard

# ========== إنلاين كيبورد للموافقة السريعة ==========
def create_approval_keyboard(file_id):
    """إنشاء أزرار الموافقة السريعة"""
    keyboard = InlineKeyboardMarkup()

    buttons = [
        InlineKeyboardButton("✅ قبول الملف", callback_data=f"approve_{file_id}"),
        InlineKeyboardButton("❌ رفض الملف", callback_data=f"reject_{file_id}"),
        InlineKeyboardButton("👀 معاينة السجلات", callback_data=f"logs_{file_id}"),
        InlineKeyboardButton("🗑️ حذف الملف", callback_data=f"delete_{file_id}")
    ]

    keyboard.add(buttons[0], buttons[1])
    keyboard.add(buttons[2], buttons[3])

    return keyboard

def create_management_keyboard(pid):
    """إنشاء أزرار إدارة البوت"""
    keyboard = InlineKeyboardMarkup()

    buttons = [
        InlineKeyboardButton("🛑 إيقاف البوت", callback_data=f"stop_{pid}"),
        InlineKeyboardButton("🔄 إعادة التشغيل", callback_data=f"restart_{pid}"),
        InlineKeyboardButton("📋 السجلات", callback_data=f"viewlogs_{pid}"),
        InlineKeyboardButton("🗑️ حذف البوت", callback_data=f"delete_{pid}")
    ]

    keyboard.add(buttons[0], buttons[1])
    keyboard.add(buttons[2], buttons[3])

    return keyboard

# ========== وظائف المساعدة ==========
def is_admin(user_id):
    """التحقق إذا كان المستخدم مشرف"""
    return user_id in admin_users

def generate_file_id():
    """إنشاء معرف فريد للملف"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

def run_bot_script(file_path, user_id):
    """تشغيل ملف البوت في عملية منفصلة مع تحسينات للسحابة"""
    try:
        print(f"🔧 محاولة تشغيل الملف: {file_path}")

        # إنشاء ملف log للملف
        log_file = os.path.join(LOGS_FOLDER, f"{os.path.basename(file_path)}_{int(time.time())}.log")

        # التأكد من أن الملف قابل للتنفيذ
        os.chmod(file_path, 0o755)

        # استخدام python مع تحسينات للسحابة
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'  # التأكد من أن الإخراج غير مخزن مؤقت

        with open(log_file, 'w') as log:
            process = subprocess.Popen(
                ['python3', file_path],
                stdout=log,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                preexec_fn=os.setsid,
                cwd=os.path.dirname(file_path),
                env=env
            )

        pid = process.pid
        print(f"✅ تم تشغيل البوت بـ PID: {pid}")
        print(f"📁 مسار العمل: {os.path.dirname(file_path)}")

        # الانتظار والتحقق من العملية
        time.sleep(3)
        if check_process_running(pid):
            print(f"✅ العملية {pid} تعمل بنجاح")
            return pid
        else:
            # قراءة الأخطاء من ملف السجل
            with open(log_file, 'r') as f:
                error_log = f.read()
            return f"فشل التشغيل - العملية توقفت. الخطأ: {error_log[:200]}..."

    except Exception as e:
        error_msg = f"خطأ في التشغيل: {str(e)}"
        logger.error(error_msg)
        return error_msg

def check_process_running(pid):
    """التحقق إذا كانت العملية لا تزال تعمل مع تحسينات للسحابة"""
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # إذا لم نكن قادرين على التحقق من العملية، نفترض أنها تعمل
    except Exception as e:
        logger.error(f"خطأ في التحقق من العملية: {e}")
        return False

def get_file_logs(file_name, lines=10):
    """الحصول على آخر سطور من ملف log"""
    try:
        log_files = [f for f in os.listdir(LOGS_FOLDER) if file_name in f and f.endswith('.log')]

        if not log_files:
            return "❌ لا توجد سجلات للملف"

        latest_log = max(log_files, key=lambda f: os.path.getctime(os.path.join(LOGS_FOLDER, f)))
        log_path = os.path.join(LOGS_FOLDER, latest_log)

        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.readlines()

        if not content:
            return "📭 ملف السجلات فارغ"

        return "".join(content[-lines:])

    except Exception as e:
        return f"❌ خطأ في قراءة السجلات: {str(e)}"

def cleanup_old_processes():
    """تنظيف العمليات المتوقفة"""
    try:
        current_active = {}
        for pid, info in active_bots.items():
            if check_process_running(pid):
                current_active[pid] = info

        active_bots.clear()
        active_bots.update(current_active)
        save_data()
    except Exception as e:
        logger.error(f"خطأ في تنظيف العمليات: {e}")

def notify_user(user_id, message):
    """إرسال إشعار للمستخدم"""
    try:
        bot.send_message(user_id, message, parse_mode='Markdown', reply_markup=main_keyboard(user_id))
    except Exception as e:
        logger.error(f"فشل في إرسال إشعار للمستخدم {user_id}: {e}")

def check_requirements():
    """التحقق من الاعتمادات الأساسية"""
    try:
        # التحقق من وجود Python
        subprocess.run(['python3', '--version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("✅ Python موجود")

        # التحقق من وجود pip
        subprocess.run(['pip3', '--version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("✅ pip موجود")

    except subprocess.CalledProcessError as e:
        print(f"❌ خطأ في التحقق من الاعتمادات: {e}")

# ========== معالجة الكول باك (الأزرار التفاعلية) ==========
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    """معالجة الأزرار التفاعلية"""
    try:
        if call.data.startswith('approve_'):
            file_id = call.data.split('_')[1]
            approve_file_callback(call.message, file_id, call.from_user.id, call.message.message_id)

        elif call.data.startswith('reject_'):
            file_id = call.data.split('_')[1]
            reject_file_callback(call.message, file_id, call.from_user.id, call.message.message_id)

        elif call.data.startswith('logs_'):
            file_id = call.data.split('_')[1]
            show_file_logs_callback(call.message, file_id, call.from_user.id)

        elif call.data.startswith('stop_'):
            pid = int(call.data.split('_')[1])
            stop_bot_callback(call.message, pid, call.from_user.id, call.message.message_id)

        elif call.data.startswith('restart_'):
            pid = int(call.data.split('_')[1])
            restart_bot_callback(call.message, pid, call.from_user.id, call.message.message_id)

        elif call.data.startswith('viewlogs_'):
            pid = int(call.data.split('_')[1])
            view_bot_logs_callback(call.message, pid, call.from_user.id)

        elif call.data.startswith('delete_'):
            identifier = call.data.split('_')[1]
            if identifier.isdigit():  # Check if it's a PID or file_id
                pid = int(identifier)
                delete_bot_callback(call.message, pid, call.from_user.id, call.message.message_id)
            else:
                file_id = identifier
                delete_file_callback(call.message, file_id, call.from_user.id, call.message.message_id)

    except Exception as e:
        try:
            bot.answer_callback_query(call.id, f"❌ خطأ: {str(e)}")
        except:
            pass

def approve_file_callback(message, file_id, user_id, message_id):
    """قبول الملف عبر الزر التفاعلي"""
    if not is_admin(user_id):
        try:
            bot.answer_callback_query(message.id, "❌ غير مصرح لك!")
        except:
            pass
        return

    try:
        if file_id not in pending_files:
            try:
                bot.answer_callback_query(message.id, "❌ الملف غير موجود!")
            except:
                pass
            return

        file_info = pending_files[file_id]

        # نقل الملف
        old_path = file_info['file_path']
        new_path = os.path.join(UPLOAD_FOLDER, file_info['file_name'])
        os.rename(old_path, new_path)

        # تشغيل البوت
        pid = run_bot_script(new_path, file_info['user_id'])

        if pid and isinstance(pid, int):
            file_info['file_path'] = new_path
            file_info['pid'] = pid
            file_info['approve_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            file_info['approved_by'] = "نظام"
            file_info['status'] = 'approved'

            approved_files[file_id] = file_info
            del pending_files[file_id]

            active_bots[pid] = {
                'file_name': file_info['file_name'],
                'file_path': new_path,
                'user_id': file_info['user_id'],
                'user_name': file_info['user_name'],
                'start_time': time.time(),
                'file_id': file_id
            }

            save_data()

            # تحديث الرسالة الأصلية
            try:
                bot.edit_message_text(
                    f"✅ **تم قبول الملف بنجاح!**\n\n"
                    f"📁 **الملف:** `{file_info['file_name']}`\n"
                    f"🆔 **الحالة:** تم التشغيل\n"
                    f"👤 **بواسطة:** {file_info['user_name']}\n"
                    f"⏰ **الوقت:** {datetime.now().strftime('%H:%M:%S')}",
                    chat_id=message.chat.id,
                    message_id=message_id,
                    parse_mode='Markdown'
                )
            except:
                pass

            # إعلام المستخدم
            user_msg = f"""
🎉 **تم قبول ملفك!**

📁 **الملف:** `{file_info['file_name']}`
✅ **الحالة:** تم التشغيل بنجاح
🆔 **PID:** `{pid}`

💡 **يمكنك متابعة الملف من قائمة 'ملفاتي'**
            """
            notify_user(file_info['user_id'], user_msg)

            try:
                bot.answer_callback_query(message.id, "✅ تم قبول الملف!")
            except:
                pass

        else:
            try:
                bot.answer_callback_query(message.id, f"❌ فشل التشغيل: {pid}")
            except:
                pass

    except Exception as e:
        try:
            bot.answer_callback_query(message.id, f"❌ خطأ: {str(e)}")
        except:
            pass

def reject_file_callback(message, file_id, user_id, message_id):
    """رفض الملف عبر الزر التفاعلي"""
    if not is_admin(user_id):
        try:
            bot.answer_callback_query(message.id, "❌ غير مصرح لك!")
        except:
            pass
        return

    try:
        if file_id not in pending_files:
            try:
                bot.answer_callback_query(message.id, "❌ الملف غير موجود!")
            except:
                pass
            return

        file_info = pending_files[file_id]

        file_info['reject_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        file_info['rejected_by'] = "نظام"
        file_info['status'] = 'rejected'

        rejected_files[file_id] = file_info
        del pending_files[file_id]

        try:
            os.remove(file_info['file_path'])
        except:
            pass

        save_data()

        # تحديث الرسالة الأصلية
        try:
            bot.edit_message_text(
                f"❌ **تم رفض الملف**\n\n"
                f"📁 **الملف:** `{file_info['file_name']}`\n"
                f"👤 **المستخدم:** {file_info['user_name']}\n"
                f"⏰ **الوقت:** {datetime.now().strftime('%H:%M:%S')}",
                chat_id=message.chat.id,
                message_id=message_id,
                parse_mode='Markdown'
            )
        except:
            pass

        # إعلام المستخدم
        user_msg = f"""
😔 **تم رفض ملفك**

📁 **الملف:** `{file_info['file_name']}`
❌ **الحالة:** مرفوض

💡 **يمكنك رفع ملف آخر من قائمة 'رفع ملف'`
        """
        notify_user(file_info['user_id'], user_msg)

        try:
            bot.answer_callback_query(message.id, "❌ تم رفض الملف!")
        except:
            pass

    except Exception as e:
        try:
            bot.answer_callback_query(message.id, f"❌ خطأ: {str(e)}")
        except:
            pass

def stop_bot_callback(message, pid, user_id, message_id):
    """إيقاف البوت عبر الزر التفاعلي"""
    if not is_admin(user_id):
        try:
            bot.answer_callback_query(message.id, "❌ غير مصرح لك!")
        except:
            pass
        return

    try:
        if pid not in active_bots:
            try:
                bot.answer_callback_query(message.id, "❌ البوت غير موجود!")
            except:
                pass
            return

        bot_info = active_bots[pid]
        os.kill(pid, signal.SIGTERM)
        del active_bots[pid]
        save_data()

        # تحديث الرسالة الأصلية
        try:
            bot.edit_message_text(
                f"🛑 **تم إيقاف البوت**\n\n"
                f"📁 **الملف:** `{bot_info['file_name']}`\n"
                f"🆔 **PID:** `{pid}`\n"
                f"⏰ **الوقت:** {datetime.now().strftime('%H:%M:%S')}",
                chat_id=message.chat.id,
                message_id=message_id,
                parse_mode='Markdown'
            )
        except:
            pass

        # إعلام المستخدم
        user_msg = f"""
🛑 **تم إيقاف بوتك**

📁 **الملف:** `{bot_info['file_name']}`
🆔 **PID:** `{pid}`

💡 **يمكنك رفع ملف آخر من قائمة 'رفع ملف'`
        """
        notify_user(bot_info['user_id'], user_msg)

        try:
            bot.answer_callback_query(message.id, "✅ تم إيقاف البوت!")
        except:
            pass

    except Exception as e:
        try:
            bot.answer_callback_query(message.id, f"❌ خطأ: {str(e)}")
        except:
            pass

def restart_bot_callback(message, pid, user_id, message_id):
    """إعادة تشغيل البوت عبر الزر التفاعلي"""
    if not is_admin(user_id):
        try:
            bot.answer_callback_query(message.id, "❌ غير مصرح لك!")
        except:
            pass
        return

    try:
        if pid not in active_bots:
            try:
                bot.answer_callback_query(message.id, "❌ البوت غير موجود!")
            except:
                pass
            return

        bot_info = active_bots[pid]
        os.kill(pid, signal.SIGTERM)
        time.sleep(2)  # انتظار لإيقاف العملية

        # إعادة تشغيل البوت
        new_pid = run_bot_script(bot_info['file_path'], bot_info['user_id'])

        if new_pid and isinstance(new_pid, int):
            bot_info['pid'] = new_pid
            active_bots[new_pid] = bot_info
            del active_bots[pid]
            save_data()

            # تحديث الرسالة الأصلية
            try:
                bot.edit_message_text(
                    f"🔄 **تم إعادة تشغيل البوت**\n\n"
                    f"📁 **الملف:** `{bot_info['file_name']}`\n"
                    f"🆔 **PID الجديد:** `{new_pid}`\n"
                    f"⏰ **الوقت:** {datetime.now().strftime('%H:%M:%S')}",
                    chat_id=message.chat.id,
                    message_id=message.message_id,
                    parse_mode='Markdown'
                )
            except:
                pass

            # إعلام المستخدم
            user_msg = f"""
🔄 **تم إعادة تشغيل بوتك**

📁 **الملف:** `{bot_info['file_name']}`
🆔 **PID الجديد:** `{new_pid}`

💡 **يمكنك متابعة الملف من قائمة 'ملفاتي'`
            """
            notify_user(bot_info['user_id'], user_msg)

            try:
                bot.answer_callback_query(message.id, "✅ تم إعادة تشغيل البوت!")
            except:
                pass
        else:
            try:
                bot.answer_callback_query(message.id, f"❌ فشل إعادة التشغيل: {new_pid}")
            except:
                pass

    except Exception as e:
        try:
            bot.answer_callback_query(message.id, f"❌ خطأ: {str(e)}")
        except:
            pass

def delete_bot_callback(message, pid, user_id, message_id):
    """حذف البوت عبر الزر التفاعلي"""
    if not is_admin(user_id):
        try:
            bot.answer_callback_query(message.id, "❌ غير مصرح لك!")
        except:
            pass
        return

    try:
        if pid not in active_bots:
            try:
                bot.answer_callback_query(message.id, "❌ البوت غير موجود!")
            except:
                pass
            return

        bot_info = active_bots[pid]
        os.kill(pid, signal.SIGTERM)
        try:
            os.remove(bot_info['file_path'])
        except:
            pass
        del active_bots[pid]
        save_data()

        # تحديث الرسالة الأصلية
        try:
            bot.edit_message_text(
                f"🗑️ **تم حذف البوت**\n\n"
                f"📁 **الملف:** `{bot_info['file_name']}`\n"
                f"🆔 **PID:** `{pid}`\n"
                f"⏰ **الوقت:** {datetime.now().strftime('%H:%M:%S')}",
                chat_id=message.chat.id,
                message_id=message_id,
                parse_mode='Markdown'
            )
        except:
            pass

        # إعلام المستخدم
        user_msg = f"""
🗑️ **تم حذف بوتك**

📁 **الملف:** `{bot_info['file_name']}`
🆔 **PID:** `{pid}`

💡 **يمكنك رفع ملف آخر من قائمة 'رفع ملف'`
        """
        notify_user(bot_info['user_id'], user_msg)

        try:
            bot.answer_callback_query(message.id, "✅ تم حذف البوت!")
        except:
            pass

    except Exception as e:
        try:
            bot.answer_callback_query(message.id, f"❌ خطأ: {str(e)}")
        except:
            pass

def delete_file_callback(message, file_id, user_id, message_id):
    """حذف الملف عبر الزر التفاعلي"""
    if not is_admin(user_id):
        try:
            bot.answer_callback_query(message.id, "❌ غير مصرح لك!")
        except:
            pass
        return

    try:
        file_info = None
        file_status = None
        if file_id in pending_files:
            file_info = pending_files[file_id]
            file_status = 'pending'
        elif file_id in approved_files:
            file_info = approved_files[file_id]
            file_status = 'approved'
        elif file_id in rejected_files:
            file_info = rejected_files[file_id]
            file_status = 'rejected'

        if not file_info:
            try:
                bot.answer_callback_query(message.id, "❌ الملف غير موجود!")
            except:
                pass
            return

        try:
            os.remove(file_info['file_path'])
        except:
            pass

        if file_status == 'pending':
            del pending_files[file_id]
        elif file_status == 'approved':
            del approved_files[file_id]
        elif file_status == 'rejected':
            del rejected_files[file_id]

        save_data()

        # تحديث الرسالة الأصلية
        try:
            bot.edit_message_text(
                f"🗑️ **تم حذف الملف**\n\n"
                f"📁 **الملف:** `{file_info['file_name']}`\n"
                f"⏰ **الوقت:** {datetime.now().strftime('%H:%M:%S')}",
                chat_id=message.chat.id,
                message_id=message_id,
                parse_mode='Markdown'
            )
        except:
            pass

        try:
            bot.answer_callback_query(message.id, "✅ تم حذف الملف!")
        except:
            pass

    except Exception as e:
        try:
            bot.answer_callback_query(message.id, f"❌ خطأ: {str(e)}")
        except:
            pass

# ========== معالجة الأزرار والرسائل ==========
@bot.message_handler(commands=['start'])
def send_welcome(message):
    """بدء البوت وعرض القائمة الرئيسية"""
    try:
        welcome_text = f"""
🎊 **مرحباً {message.from_user.first_name}!**  

🤖 **بوت استضافة ملفات بايثون الاحترافي**

📋 **اختر من القائمة الرئيسية:**
        """

        bot.send_message(
            message.chat.id,
            welcome_text,
            parse_mode='Markdown',
            reply_markup=main_keyboard(message.from_user.id)
        )
    except Exception as e:
        print(f"❌ خطأ في إرسال الترحيب: {e}")

@bot.message_handler(func=lambda message: message.text == "🏠 الرئيسية")
def main_menu(message):
    """العودة للقائمة الرئيسية"""
    try:
        welcome_text = f"""
🏠 **القائمة الرئيسية**

🎊 مرحباً {message.from_user.first_name}!
🤖 بوت استضافة ملفات بايثون
        """

        bot.send_message(
            message.chat.id,
            welcome_text,
            parse_mode='Markdown',
            reply_markup=main_keyboard(message.from_user.id)
        )
    except Exception as e:
        print(f"❌ خطأ في القائمة الرئيسية: {e}")

@bot.message_handler(func=lambda message: message.text == "📤 رفع ملف")
def upload_file(message):
    """طلب رفع ملف"""
    try:
        text = """
📤 **رفع ملف بايثون**

📎 **الخطوات:**
1. أرسل ملف Python (.py) الآن
2. انتظر مراجعة المشرف
3. سيصلك إشعار عند القبول

⚡ **المتطلبات:**
• الملف يجب أن يكون بصيغة .py
• يدعم مكتبات Python الأساسية
• حجم الملف لا يتعدى 50MB

🚀 **أرسل الملف الآن...**
        """

        bot.send_message(
            message.chat.id,
            text,
            parse_mode='Markdown',
            reply_markup=back_to_main_keyboard(message.from_user.id)
        )
    except Exception as e:
        print(f"❌ خطأ في رفع الملف: {e}")

@bot.message_handler(func=lambda message: message.text == "📨 الرسالة")
def send_message(message):
    """إرسال رسالة إلى المستخدم"""
    try:
        bot.send_message(message.chat.id, "يرجى كتابة الرسالة التي تريد إرسالها.")
        bot.register_next_step_handler(message, send_message_to_admin)
    except Exception as e:
        print(f"❌ خطأ في إرسال الرسالة: {e}")

def send_message_to_admin(message):
    """إرسال رسالة إلى الادمن"""
    try:
        admin_id = int(os.getenv("ADMIN_ID", 1056328647))  # Samir's Telegram ID
        bot.send_message(admin_id, f"رسالة من المستخدم {message.from_user.first_name}:\n\n{message.text}")
        bot.send_message(message.chat.id, "تم إرسال رسالتك إلى المشرف.", reply_markup=main_keyboard(message.from_user.id))
    except Exception as e:
        print(f"❌ خطأ في إرسال الرسالة إلى المشرف: {e}")

@bot.message_handler(func=lambda message: message.text == "📺 قناتي")
def my_channel(message):
    """عرض قناة المستخدم"""
    try:
        channel_url = "https://t.me/Haram_2002"
        bot.send_message(message.chat.id, f"يمكنك زيارة قناتي من خلال الرابط التالي: {channel_url}", reply_markup=main_keyboard(message.from_user.id))
    except Exception as e:
        print(f"❌ خطأ في عرض القناة: {e}")

@bot.message_handler(func=lambda message: message.text == "📁 ملفاتي")
def my_files(message):
    """عرض ملفات المستخدم"""
    try:
        user_id = str(message.from_user.id)
        if user_id in users_data:
            files = []
            for file_id, file_info in approved_files.items():
                if file_info['user_id'] == message.from_user.id:
                    files.append((file_info['file_name'], file_id, 'approved'))
            for file_id, file_info in rejected_files.items():
                if file_info['user_id'] == message.from_user.id:
                    files.append((file_info['file_name'], file_id, 'rejected'))
            for file_id, file_info in pending_files.items():
                if file_info['user_id'] == message.from_user.id:
                    files.append((file_info['file_name'], file_id, 'pending'))

            if files:
                keyboard = InlineKeyboardMarkup()
                for file_name, file_id, status in files:
                    keyboard.add(InlineKeyboardButton(f"{file_name} (حالة: {status})", callback_data=f"delete_{file_id}"))
                bot.send_message(message.chat.id, "📁 ملفاتك:", reply_markup=keyboard)
            else:
                bot.send_message(message.chat.id, "لا يوجد لديك أي ملفات.", reply_markup=main_keyboard(message.from_user.id))
        else:
            bot.send_message(message.chat.id, "لا يوجد لديك أي ملفات.", reply_markup=main_keyboard(message.from_user.id))
    except Exception as e:
        print(f"❌ خطأ في عرض الملفات: {e}")

@bot.message_handler(func=lambda message: message.text == "ℹ️ المساعدة")
def help_message(message):
    """إرسال معلومات المساعدة"""
    try:
        help_text = """
📖 **مساعدة**

🤖 بوت استضافة ملفات بايثون

📋 **الأوامر المتاحة:**
/start - بدء البوت
📤 رفع ملف - رفع ملف بايثون
📁 ملفاتي - عرض ملفاتي
ℹ️ المساعدة - عرض هذه الرسالة
📊 الحالة - عرض حالة البوت
        """
        bot.send_message(message.chat.id, help_text, parse_mode='Markdown', reply_markup=main_keyboard(message.from_user.id))
    except Exception as e:
        print(f"❌ خطأ في إرسال المساعدة: {e}")

@bot.message_handler(func=lambda message: message.text == "📊 الحالة")
def bot_status(message):
    """عرض حالة البوت"""
    try:
        status_text = f"""
📊 **حالة البوت**

🤖 **البوتات النشطة:** {len(active_bots)}
⏳ **الملفات المنتظرة:** {len(pending_files)}
✅ **الملفات المعتمدة:** {len(approved_files)}
❌ **الملفات المرفوضة:** {len(rejected_files)}
        """
        bot.send_message(message.chat.id, status_text, parse_mode='Markdown', reply_markup=main_keyboard(message.from_user.id))
    except Exception as e:
        print(f"❌ خطأ في عرض الحالة: {e}")

@bot.message_handler(func=lambda message: message.text == "👑 لوحة التحكم")
def admin_panel(message):
    """عرض لوحة التحكم"""
    try:
        if is_admin(message.from_user.id):
            bot.send_message(message.chat.id, "👑 **لوحة التحكم**", reply_markup=admin_keyboard())
        else:
            bot.send_message(message.chat.id, "❌ غير مصرح لك بالوصول إلى لوحة التحكم.", reply_markup=main_keyboard(message.from_user.id))
    except Exception as e:
        print(f"❌ خطأ في عرض لوحة التحكم: {e}")

@bot.message_handler(func=lambda message: message.text == "⏳ الملفات المنتظرة")
def pending_files_list(message):
    """عرض قائمة الملفات المنتظرة"""
    try:
        if not is_admin(message.from_user.id):
            bot.send_message(message.chat.id, "❌ غير مصرح لك بالوصول إلى هذه الميزة.", reply_markup=main_keyboard(message.from_user.id))
            return

        if not pending_files:
            bot.send_message(message.chat.id, "لا يوجد ملفات منتظرة.", reply_markup=admin_keyboard())
            return

        for file_id, file_info in pending_files.items():
            keyboard = create_approval_keyboard(file_id)
            bot.send_message(
                message.chat.id,
                f"📄 **الملف:** `{file_info['file_name']}`\n"
                f"👤 **المستخدم:** {file_info['user_name']}\n"
                f"🆔 **معرف الملف:** `{file_id}`",
                parse_mode='Markdown',
                reply_markup=keyboard
            )

    except Exception as e:
        print(f"❌ خطأ في عرض الملفات المنتظرة: {e}")

@bot.message_handler(func=lambda message: message.text == "🔵 البوتات النشطة")
def active_bots_list(message):
    """عرض قائمة البوتات النشطة"""
    try:
        if not is_admin(message.from_user.id):
            bot.send_message(message.chat.id, "❌ غير مصرح لك بالوصول إلى هذه الميزة.", reply_markup=main_keyboard(message.from_user.id))
            return

        if not active_bots:
            bot.send_message(message.chat.id, "لا يوجد بوتات نشطة.", reply_markup=admin_keyboard())
            return

        for pid, info in active_bots.items():
            keyboard = create_management_keyboard(pid)
            bot.send_message(
                message.chat.id,
                f"🤖 **الملف:** `{info['file_name']}`\n"
                f"🆔 **PID:** `{pid}`\n"
                f"👤 **المستخدم:** {info['user_name']}",
                parse_mode='Markdown',
                reply_markup=keyboard
            )

    except Exception as e:
        print(f"❌ خطأ في عرض البوتات النشطة: {e}")

@bot.message_handler(func=lambda message: message.text == "👥 المستخدمين")
def users_list(message):
    """عرض قائمة المستخدمين"""
    try:
        if not is_admin(message.from_user.id):
            bot.send_message(message.chat.id, "❌ غير مصرح لك بالوصول إلى هذه الميزة.", reply_markup=main_keyboard(message.from_user.id))
            return

        if not users_data:
            bot.send_message(message.chat.id, "لا يوجد مستخدمين مسجلين.", reply_markup=admin_keyboard())
            return

        users_list = "\n".join([f"👤 {user['first_name']} (ID: {user_id})" for user_id, user in users_data.items()])
        bot.send_message(message.chat.id, f"👥 **المستخدمين:**\n{users_list}", reply_markup=admin_keyboard())
    except Exception as e:
        print(f"❌ خطأ في عرض المستخدمين: {e}")

@bot.message_handler(func=lambda message: message.text == "⚙️ الإعدادات")
def settings_menu(message):
    """عرض قائمة الإعدادات"""
    try:
        if not is_admin(message.from_user.id):
            bot.send_message(message.chat.id, "❌ غير مصرح لك بالوصول إلى هذه الميزة.", reply_markup=main_keyboard(message.from_user.id))
            return

        settings_text = """
⚙️ **الإعدادات**

🔧 **إعدادات البوت:**
- التحديث التلقائي: مفعّل
- الحد الأقصى للملفات لكل مستخدم: 5
- الحجم الأقصى للملف: 50MB
        """
        bot.send_message(message.chat.id, settings_text, parse_mode='Markdown', reply_markup=admin_keyboard())
    except Exception as e:
        print(f"❌ خطأ في عرض الإعدادات: {e}")

@bot.message_handler(func=lambda message: message.text == "📊 الإحصائيات")
def statistics(message):
    """عرض الإحصائيات"""
    try:
        if not is_admin(message.from_user.id):
            bot.send_message(message.chat.id, "❌ غير مصرح لك بالوصول إلى هذه الميزة.", reply_markup=main_keyboard(message.from_user.id))
            return

        stats_text = f"""
📊 **الإحصائيات**

👥 **عدد المستخدمين:** {len(users_data)}
📄 **عدد الملفات المرفوعة:** {sum(user['files_uploaded'] for user in users_data.values())}
🤖 **البوتات النشطة:** {len(active_bots)}
⏳ **الملفات المنتظرة:** {len(pending_files)}
✅ **الملفات المعتمدة:** {len(approved_files)}
❌ **الملفات المرفوضة:** {len(rejected_files)}
        """
        bot.send_message(message.chat.id, stats_text, parse_mode='Markdown', reply_markup=admin_keyboard())
    except Exception as e:
        print(f"❌ خطأ في عرض الإحصائيات: {e}")

# ========== معالجة الملفات المرسلة ==========
@bot.message_handler(content_types=['document'])
def handle_document(message):
    """معالجة الملفات المرسلة"""
    try:
        if not (message.document.mime_type == 'text/x-python' or
                (message.document.file_name and message.document.file_name.endswith('.py'))):
            bot.reply_to(message, "❌ يرجى إرسال ملف بايثون صالح (.py) فقط.")
            return

        msg = bot.reply_to(message, "📥 جارٍ تنزيل الملف...")

        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        file_name = message.document.file_name
        file_id = generate_file_id()
        file_path = os.path.join(PENDING_FOLDER, f"{file_id}_{file_name}")

        with open(file_path, 'wb') as f:
            f.write(downloaded_file)

        os.chmod(file_path, 0o755)

        pending_files[file_id] = {
            'file_name': file_name,
            'file_path': file_path,
            'user_id': message.from_user.id,
            'user_name': message.from_user.first_name,
            'username': message.from_user.username,
            'upload_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'file_size': len(downloaded_file),
            'status': 'pending'
        }

        user_id_str = str(message.from_user.id)
        if user_id_str not in users_data:
            users_data[user_id_str] = {
                'first_name': message.from_user.first_name,
                'username': message.from_user.username,
                'files_uploaded': 0,
                'join_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        users_data[user_id_str]['files_uploaded'] += 1

        save_data()

        # إعلام المشرفين مع أزرار الموافقة السريعة
        for admin_id in admin_users:
            try:
                admin_msg = f"""
📨 **ملف جديد بانتظار المراجعة**

📁 **الملف:** `{file_name}`
👤 **المستخدم:** {message.from_user.first_name}
🆔 **معرف الملف:** `{file_id}`
📦 **الحجم:** {len(downloaded_file)} بايت
⏰ **الوقت:** {datetime.now().strftime("%H:%M:%S")}
                """
                keyboard = create_approval_keyboard(file_id)
                bot.send_message(
                    admin_id,
                    admin_msg,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            except Exception as e:
                print(f"❌ فشل في إعلام المشرف {admin_id}: {e}")

        success_text = f"""
✅ **تم استلام الملف بنجاح!**

📁 **الملف:** `{file_name}`
🆔 **معرف الملف:** `{file_id}`

📋 **حالة الملف:** ⏳ بانتظار المراجعة
🔔 **سيصلك إشعار عند المراجعة**
        """

        bot.edit_message_text(
            success_text,
            chat_id=message.chat.id,
            message_id=msg.message_id,
            parse_mode='Markdown'
        )

    except Exception as e:
        logger.error(f"خطأ في معالجة الملف: {e}")
        try:
            bot.reply_to(message, f"❌ خطأ في معالج الملف: {str(e)}")
        except:
            pass

# ========== التشغيل الرئيسي مع إعادة الاتصال التلقائي ==========
def start_bot():
    """بدء تشغيل البوت مع التحقق من الاعتمادات"""
    print("\n" + "="*50)
    print("🚀 بدء تشغيل بوت الاستضافة...")
    print(f"📁 المجلد الأساسي: {BASE_DIR}")
    print(f"🔑 المشرفين: {admin_users}")
    print(f"🤖 البوتات النشطة: {len(active_bots)}")
    print(f"⏳ الملفات المنتظرة: {len(pending_files)}")
    print("="*50)

    # تنظيف العمليات القديمة
    cleanup_old_processes()

    # بدء مراقبة البوتات
    def monitor_bots():
        while True:
            try:
                cleanup_old_processes()
                time.sleep(30)
            except Exception as e:
                print(f"❌ خطأ في المراقبة: {e}")
                time.sleep(60)

    monitor_thread = threading.Thread(target=monitor_bots, daemon=True)
    monitor_thread.start()

    # التشغيل الرئيسي للبوت مع إعادة الاتصال التلقائي
    while True:
        try:
            print("🔄 تشغيل البوت...")
            bot.polling(none_stop=True, interval=2, timeout=30)
        except Exception as e:
            print(f"❌ خطأ في تشغيل البوت: {e}")
            print("🔁 إعادة المحاولة بعد 15 ثانية...")
            time.sleep(15)

if __name__ == "__main__":
    start_bot()
