import telebot
from telebot import types
import json
import schedule
import time
import threading
from config import TOKEN, ADMIN_ID, DEFAULT_NOTIFICATION_TIME, MAX_JOBS_PER_DIGEST
from database import Database

bot = telebot.TeleBot(TOKEN)
db = Database()

# Sahələr siyahısı
FIELDS = {
    'IT': '💻 İnformasiya Texnologiyaları',
    'Design': '🎨 Dizayn',
    'Marketing': '📢 Marketinq',
    'Sales': '💼 Satış',
    'Finance': '💰 Maliyyə',
    'HR': '👥 İnsan Resursları',
    'Education': '📚 Təhsil',
    'Healthcare': '🏥 Səhiyyə',
    'Engineering': '⚙️ Mühendislik',
    'Other': '🔧 Digər'
}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    # İstifadəçini verilənlər bazasına əlavə et
    db.add_user(user_id, username, first_name)
    
    welcome_text = f"""👋 Salam {first_name}! 

🎯 **Vakansiya Radar** botuna xoş gəlmisiniz!

Bu bot vasitəsilə:
✅ İstədiyiniz sahələrdə yeni vakansiyalar haqqında bildiriş ala bilərsiniz
✅ Müntəzəm iş elanları paylaşımı
✅ Sahə üzrə filtrlənmiş vakansiyalar

🚀 Başlamaq üçün aşağıdakı komandalardan istifadə edin:
/activevacancy - Maraqlandığınız sahələri seçin
/myjobs - Seçdiyiniz sahələrdə son vakansiyalar
/settime - Bildiriş vaxtını təyin edin
/feedback - Təklif və iradlarınızı göndərin

Hazır başlayaq? 🎉"""
    
    bot.send_message(message.chat.id, welcome_text)

@bot.message_handler(commands=['activevacancy'])
def select_fields(message):
    user_id = message.from_user.id
    current_fields = db.get_user_fields(user_id)
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    for field_key, field_name in FIELDS.items():
        if field_key in current_fields:
            button_text = f"✅ {field_name}"
        else:
            button_text = field_name
        
        markup.add(types.InlineKeyboardButton(
            text=button_text,
            callback_data=f"field_{field_key}"
        ))
    
    markup.add(
        types.InlineKeyboardButton("💾 Seçimləri Yadda Saxla", callback_data="save_fields"),
        types.InlineKeyboardButton("🗑 Hamısını Təmizlə", callback_data="clear_fields")
    )
    
    bot.send_message(
        message.chat.id,
        "📋 **Maraqlandığınız sahələri seçin:**\n\n"
        "Bir neçə sahə seçə bilərsiniz. Seçdiyiniz sahələrdə yeni vakansiyalar olduqda sizə bildiriş göndəriləcək.",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('field_'))
def handle_field_selection(call):
    user_id = call.from_user.id
    field = call.data.replace('field_', '')
    
    current_fields = db.get_user_fields(user_id)
    
    if field in current_fields:
        current_fields.remove(field)
    else:
        current_fields.append(field)
    
    db.update_user_fields(user_id, current_fields)
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    for field_key, field_name in FIELDS.items():
        if field_key in current_fields:
            button_text = f"✅ {field_name}"
        else:
            button_text = field_name
        
        markup.add(types.InlineKeyboardButton(
            text=button_text,
            callback_data=f"field_{field_key}"
        ))
    
    markup.add(
        types.InlineKeyboardButton("💾 Seçimləri Yadda Saxla", callback_data="save_fields"),
        types.InlineKeyboardButton("🗑 Hamısını Təmizlə", callback_data="clear_fields")
    )
    
    bot.edit_message_reply_markup(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == 'save_fields')
def save_fields(call):
    user_id = call.from_user.id
    selected_fields = db.get_user_fields(user_id)
    
    if not selected_fields:
        bot.answer_callback_query(call.id, "❌ Heç bir sahə seçmədiniz!", show_alert=True)
        return
    
    field_names = [FIELDS[field] for field in selected_fields]
    
    success_text = f"""✅ **Seçimləriniz uğurla yadda saxlanıldı!**

📋 **Seçdiyiniz sahələr:**
{chr(10).join(f"• {name}" for name in field_names)}

🔔 Bu sahələrdə yeni vakansiyalar olduqda sizə bildiriş göndəriləcək.

/myjobs - Son vakansiyaları görmək üçün
/settime - Bildiriş vaxtını dəyişmək üçün"""
    
    bot.edit_message_text(
        text=success_text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )

@bot.callback_query_handler(func=lambda call: call.data == 'clear_fields')
def clear_fields(call):
    user_id = call.from_user.id
    db.update_user_fields(user_id, [])
    
    bot.answer_callback_query(call.id, "🗑 Bütün seçimlər təmizləndi!", show_alert=True)
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    for field_key, field_name in FIELDS.items():
        markup.add(types.InlineKeyboardButton(
            text=field_name,
            callback_data=f"field_{field_key}"
        ))
    
    markup.add(
        types.InlineKeyboardButton("💾 Seçimləri Yadda Saxla", callback_data="save_fields"),
        types.InlineKeyboardButton("🗑 Hamısını Təmizlə", callback_data="clear_fields")
    )
    
    bot.edit_message_reply_markup(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )

@bot.message_handler(commands=['myjobs'])
def show_my_jobs(message):
    user_id = message.from_user.id
    selected_fields = db.get_user_fields(user_id)
    
    if not selected_fields:
        bot.send_message(
            message.chat.id,
            "❌ Hələ heç bir sahə seçmədiniz!\n\n"
            "/activevacancy komandasını istifadə edərək maraqlandığınız sahələri seçin."
        )
        return
    
    all_jobs = []
    for field in selected_fields:
        jobs = db.get_recent_jobs(field, 5)
        all_jobs.extend(jobs)
    
    if not all_jobs:
        field_names = [FIELDS[field] for field in selected_fields]
        bot.send_message(
            message.chat.id,
            f"📋 **Seçdiyiniz sahələrdə hal-hazırda aktiv vakansiya yoxdur:**\n"
            f"{chr(10).join(f'• {name}' for name in field_names)}\n\n"
            "🔄 Yeni vakansiyalar əlavə olunduqda sizə bildiriş göndəriləcək!"
        )
        return
    
    jobs_text = "💼 **Son vakansiyalar:**\n\n"
    
    for job in all_jobs[:10]:
        jobs_text += f"🏢 **{job[1]}** - {job[2]}\n"
        jobs_text += f"📍 Sahə: {FIELDS.get(job[3], job[3])}\n"
        jobs_text += f"📝 {job[4][:100]}...\n"
        if job[5]:
            jobs_text += f"💰 Maaş: {job[5]}\n"
        if job[6]:
            jobs_text += f"🌍 Yer: {job[6]}\n"
        if job[7]:
            jobs_text += f"📞 Əlaqə: {job[7]}\n"
        jobs_text += "─" * 30 + "\n\n"
    
    bot.send_message(message.chat.id, jobs_text)

@bot.message_handler(commands=['feedback'])
def feedback_command(message):
    bot.send_message(
        message.chat.id,
        "📝 **Təklif və iradlarınızı göndərin**\n\n"
        "Botla bağlı təkliflərinizi, problemləri və ya yeni fikirlərinizi yazın. "
        "Mesajınız birbaşa adminə çatacaq."
    )
    
    bot.register_next_step_handler(message, process_feedback)

def process_feedback(message):
    user_id = message.from_user.id
    feedback_text = message.text
    
    if db.add_feedback(user_id, feedback_text):
        bot.send_message(
            message.chat.id,
            "✅ **Təşəkkür edirik!**\n\n"
            "Təklifiniz uğurla göndərildi və tezliklə nəzərdən keçiriləcək."
        )
        
        try:
            username = message.from_user.username or "Naməlum"
            first_name = message.from_user.first_name or "Naməlum"
            
            admin_text = f"📝 **Yeni Feedback**\n\n"
            admin_text += f"👤 İstifadəçi: {first_name} (@{username})\n"
            admin_text += f"🆔 ID: {user_id}\n\n"
            admin_text += f"💬 Mesaj:\n{feedback_text}"
            
            bot.send_message(ADMIN_ID, admin_text)
        except Exception as e:
            print(f"Adminə feedback göndərmə xətası: {e}")
    else:
        bot.send_message(
            message.chat.id,
            "❌ Feedback göndərilərkən xəta baş verdi. Zəhmət olmasa yenidən cəhd edin."
        )

@bot.message_handler(commands=['settime'])
def choose_notify_time(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Hər saat", "Gündə 3 dəfə", "Hər axşam", "Heç biri")
    markup.add("Xüsusi saat seç")
    msg = bot.send_message(message.chat.id, "🕒 Bildiriş almaq istədiyiniz vaxtı seçin:", reply_markup=markup)
    bot.register_next_step_handler(msg, save_notify_time)

def save_notify_time(message):
    time_option = message.text
    user_id = message.from_user.id
    
    if time_option == "Xüsusi saat seç":
        markup = types.InlineKeyboardMarkup(row_width=3)
        times = ['08:00', '09:00', '10:00', '11:00', '12:00', '13:00',
                 '14:00', '15:00', '16:00', '17:00', '18:00', '19:00']
        for time in times:
            markup.add(types.InlineKeyboardButton(
                text=f"🕐 {time}",
                callback_data=f"time_{time}"
            ))
        bot.send_message(
            message.chat.id,
            "⏰ **Xüsusi bildiriş vaxtını seçin:**",
            reply_markup=markup
        )
        return
    
    # Bildiriş vaxtını saxla
    db.set_notification_time(user_id, time_option)
    bot.send_message(message.chat.id, f"✅ Bildiriş vaxtı olaraq '{time_option}' seçildi.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('time_'))
def handle_time_selection(call):
    user_id = call.from_user.id
    selected_time = call.data.replace('time_', '')
    
    if db.set_notification_time(user_id, selected_time):
        bot.edit_message_text(
            text=f"✅ **Bildiriş vaxtı təyin edildi!**\n\n"
                 f"⏰ Hər gün saat **{selected_time}**-da yeni vakansiyalar haqqında bildiriş alacaqsınız.\n\n"
                 f"Vaxtı dəyişmək üçün yenidən /settime yazın.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
    else:
        bot.answer_callback_query(call.id, "❌ Xəta baş verdi!", show_alert=True)

# ADMIN FUNKSIYALARI
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ Bu komanda yalnız admin üçündür!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Vakansiya Əlavə Et", callback_data="admin_add_job"),
        types.InlineKeyboardButton("📊 Statistika", callback_data="admin_stats")
    )
    markup.add(
        types.InlineKeyboardButton("📝 Feedback-lər", callback_data="admin_feedback"),
        types.InlineKeyboardButton("📢 Elan Göndər", callback_data="admin_broadcast")
    )
    
    bot.send_message(
        message.chat.id,
        "🔧 **Admin Panel**\n\nAşağıdakı əməliyyatlardan birini seçin:",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == 'admin_add_job')
def admin_add_job(call):
    if call.from_user.id != ADMIN_ID:
        return
    
    bot.edit_message_text(
        text="➕ **Yeni Vakansiya Əlavə Et**\n\n"
             "Vakansiya məlumatlarını aşağıdakı formatda göndərin:\n\n"
             "**Format:**\n"
             "Başlıq: [İş başlığı]\n"
             "Şirkət: [Şirkət adı]\n"
             "Sahə: [IT/Design/Marketing/Sales/Finance/HR/Education/Healthcare/Engineering/Other]\n"
             "Təsvir: [İş təsviri]\n"
             "Maaş: [Maaş məlumatı - məcburi deyil]\n"
             "Yer: [İş yeri - məcburi deyil]\n"
             "Əlaqə: [Əlaqə məlumatı]\n\n"
             "**Nümunə:**\n"
             "Başlıq: Frontend Developer\n"
             "Şirkət: ABC Tech\n"
             "Sahə: IT\n"
             "Təsvir: React və JavaScript bilən developer axtarılır\n"
             "Maaş: 1500-2000 AZN\n"
             "Yer: Bakı\n"
             "Əlaqə: hr@abctech.az",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )
    
    bot.register_next_step_handler(call.message, process_new_job)

def process_new_job(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        lines = message.text.strip().split('\n')
        job_data = {}
        
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                job_data[key.strip().lower()] = value.strip()
        
        required_fields = ['başlıq', 'şirkət', 'sahə', 'təsvir', 'əlaqə']
        for field in required_fields:
            if field not in job_data:
                bot.send_message(
                    message.chat.id,
                    f"❌ **{field.title()}** sahəsi məcburidir! Zəhmət olmasa yenidən cəhd edin."
                )
                return
        
        field_key = None
        for key, value in FIELDS.items():
            if job_data['sahə'].lower() in value.lower() or job_data['sahə'].lower() == key.lower():
                field_key = key
                break
        
        if not field_key:
            bot.send_message(
                message.chat.id,
                f"❌ **Sahə** düzgün deyil! Mümkün sahələr:\n" + 
                "\n".join([f"• {key}" for key in FIELDS.keys()])
            )
            return
        
        job_id = db.add_job(
            title=job_data['başlıq'],
            company=job_data['şirkət'],
            field=field_key,
            description=job_data['təsvir'],
            salary=job_data.get('maaş', ''),
            location=job_data.get('yer', ''),
            contact=job_data['əlaqə']
        )
        
        if job_id:
            bot.send_message(
                message.chat.id,
                f"✅ **Vakansiya uğurla əlavə edildi!**\n\n"
                f"🆔 ID: {job_id}\n"
                f"📋 Başlıq: {job_data['başlıq']}\n"
                f"🏢 Şirkət: {job_data['şirkət']}\n"
                f"📍 Sahə: {FIELDS[field_key]}\n\n"
                f"📤 Bu sahəni seçən istifadəçilərə bildiriş göndərilir..."
            )
            
            notify_users_about_job(job_data, field_key)
        else:
            bot.send_message(message.chat.id, "❌ Vakansiya əlavə edilərkən xəta baş verdi!")
            
    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"❌ **Format xətası!** Zəhmət olmasa düzgün format istifadə edin.\n\n"
            f"Xəta: {str(e)}"
        )

def notify_users_about_job(job_data, field_key):
    users = db.get_users_by_field(field_key)
    
    job_text = f"🆕 **Yeni Vakansiya!**\n\n"
    job_text += f"🏢 **{job_data['şirkət']}** - {job_data['başlıq']}\n"
    job_text += f"📍 Sahə: {FIELDS[field_key]}\n"
    job_text += f"📝 {job_data['təsvir']}\n"
    
    if job_data.get('maaş'):
        job_text += f"💰 Maaş: {job_data['maaş']}\n"
    if job_data.get('yer'):
        job_text += f"🌍 Yer: {job_data['yer']}\n"
    
    job_text += f"📞 Əlaqə: {job_data['əlaqə']}\n\n"
    job_text += "🔔 Daha çox vakansiya üçün /myjobs yazın"
    
    success_count = 0
    for user_id in users:
        try:
            bot.send_message(user_id, job_text)
            success_count += 1
        except:
            continue
    
    try:
        bot.send_message(
            ADMIN_ID,
            f"📊 **Bildiriş Nəticəsi**\n\n"
            f"👥 Ümumi istifadəçi sayı: {len(users)}\n"
            f"✅ Uğurla göndərilən: {success_count}\n"
            f"❌ Uğursuz: {len(users) - success_count}"
        )
    except:
        pass

@bot.callback_query_handler(func=lambda call: call.data == 'admin_stats')
def admin_stats(call):
    if call.from_user.id != ADMIN_ID:
        return
    
    total_users = len(db.get_all_active_users())
    fields_count = {}
    for field in FIELDS.keys():
        fields_count[field] = len(db.get_users_by_field(field))
    
    total_jobs = len(db.get_recent_jobs(limit=1000))
    feedback_count = db.cursor.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
    
    stats_text = f"📊 **Bot Statistikası**\n\n"
    stats_text += f"👥 Ümumi aktiv istifadəçilər: {total_users}\n"
    stats_text += f"💼 Ümumi vakansiyalar: {total_jobs}\n"
    stats_text += f"📝 Feedback sayı: {feedback_count}\n\n"
    stats_text += "📍 **Sahələr üzrə istifadəçilər:**\n"
    for field, count in fields_count.items():
        stats_text += f"• {FIELDS[field]}: {count}\n"
    
    bot.edit_message_text(
        text=stats_text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )

@bot.callback_query_handler(func=lambda call: call.data == 'admin_feedback')
def admin_feedback(call):
    if call.from_user.id != ADMIN_ID:
        return
    
    db.cursor.execute("SELECT user_id, message, created_at FROM feedback ORDER BY created_at DESC LIMIT 5")
    feedbacks = db.cursor.fetchall()
    
    if not feedbacks:
        bot.edit_message_text(
            text="📝 **Feedback-lər**\n\nHələ heç bir feedback yoxdur.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
        return
    
    feedback_text = "📝 **Son Feedback-lər**\n\n"
    for feedback in feedbacks:
        user_id, message, created_at = feedback
        feedback_text += f"🆔 İstifadəçi: {user_id}\n"
        feedback_text += f"💬 Mesaj: {message[:100]}...\n"
        feedback_text += f"🕒 Tarix: {created_at}\n"
        feedback_text += "─" * 30 + "\n\n"
    
    bot.edit_message_text(
        text=feedback_text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )

@bot.callback_query_handler(func=lambda call: call.data == 'admin_broadcast')
def admin_broadcast(call):
    if call.from_user.id != ADMIN_ID:
        return
    
    bot.edit_message_text(
        text="📢 **Elan Göndər**\n\n"
             "Bütün istifadəçilərə göndəriləcək mesajı yazın (maksimum 2000 simvol):",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )
    
    bot.register_next_step_handler(call.message, process_broadcast)

def process_broadcast(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    broadcast_text = message.text
    if len(broadcast_text) > 2000:
        bot.send_message(
            message.chat.id,
            "❌ Mesaj çox uzundur! Maksimum 2000 simvol olmalıdır."
        )
        return
    
    users = db.get_all_active_users()
    success_count = 0
    
    for user_id in users:
        try:
            bot.send_message(user_id, broadcast_text)
            success_count += 1
        except:
            continue
    
    bot.send_message(
        message.chat.id,
        f"📢 **Elan Göndərildi**\n\n"
        f"👥 Ümumi istifadəçi sayı: {len(users)}\n"
        f"✅ Uğurla göndərilən: {success_count}\n"
        f"❌ Uğursuz: {len(users) - success_count}"
    )

# Avtomatik bildirişlər üçün schedule
def send_scheduled_jobs():
    users = db.get_all_active_users()
    
    for user_id in users:
        db.cursor.execute("SELECT notification_time, selected_fields FROM users WHERE user_id = ?", (user_id,))
        result = db.cursor.fetchone()
        if not result:
            continue
        
        notification_time, selected_fields = result
        if not selected_fields or notification_time == "Heç biri":
            continue
        
        selected_fields = json.loads(selected_fields)
        current_time = time.strftime("%H:%M")
        
        # Bildiriş vaxtını yoxla
        should_send = False
        if notification_time == "Hər saat" and current_time.endswith(":00"):
            should_send = True
        elif notification_time == "Gündə 3 dəfə" and current_time in ["09:00", "13:00", "22:00"]:
            should_send = True
        elif notification_time == "Hər axşam" and current_time == "22:00":
            should_send = True
        elif notification_time == current_time:
            should_send = True
        
        if should_send:
            all_jobs = []
            for field in selected_fields:
                jobs = db.get_recent_jobs(field, MAX_JOBS_PER_DIGEST)
                all_jobs.extend(jobs)
            
            if all_jobs:
                jobs_text = f"🔔 **Gündəlik Vakansiya Xülasəsi** ({current_time})\n\n"
                for job in all_jobs[:MAX_JOBS_PER_DIGEST]:
                    jobs_text += f"🏢 **{job[1]}** - {job[2]}\n"
                    jobs_text += f"📍 Sahə: {FIELDS.get(job[3], job[3])}\n"
                    jobs_text += f"📝 {job[4][:100]}...\n"
                    if job[5]:
                        jobs_text += f"💰 Maaş: {job[5]}\n"
                    if job[6]:
                        jobs_text += f"🌍 Yer: {job[6]}\n"
                    if job[7]:
                        jobs_text += f"📞 Əlaqə: {job[7]}\n"
                    jobs_text += "─" * 30 + "\n\n"
                
                try:
                    bot.send_message(user_id, jobs_text)
                except Exception as e:
                    print(f"Bildiriş göndərmə xətası (istifadəçi {user_id}): {e}")

def schedule_notifications():
    # Hər saat başı
    schedule.every().hour.at(":00").do(send_scheduled_jobs)
    # Gündə 3 dəfə
    schedule.every().day.at("09:00").do(send_scheduled_jobs)
    schedule.every().day.at("13:00").do(send_scheduled_jobs)
    schedule.every().day.at("22:00").do(send_scheduled_jobs)
    # Xüsusi saatlar
    for hour in range(8, 20):
        schedule.every().day.at(f"{hour:02d}:00").do(send_scheduled_jobs)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

def start_schedule():
    threading.Thread(target=schedule_notifications, daemon=True).start()

if __name__ == "__main__":
    print("🤖 Vakansiya Bot işə başladı...")
    start_schedule()
    bot.infinity_polling()