import os
import threading
from flask import Flask
import telebot
import anthropic
from openai import OpenAI
from google import genai

# ==========================================
# 1. سحب المفاتيح السرية من بيئة السيرفر (Environment Variables)
# ==========================================
TELEGRAM_COUNCIL_TOKEN = os.getenv("TELEGRAM_COUNCIL_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_COUNCIL_KEY = os.getenv("GEMINI_COUNCIL_KEY")

bot = telebot.TeleBot(TELEGRAM_COUNCIL_TOKEN)

# تهيئة عملاء الذكاء الاصطناعي
claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
gemini_client = genai.Client(api_key=GEMINI_COUNCIL_KEY) if GEMINI_COUNCIL_KEY else None

# ==========================================
# 2. ذاكرة الجلسة المؤقتة (تُفرغ عند الإغلاق لتوفير التوكن)
# ==========================================
session_state = {
    "active": False,
    "history": []  # يحفظ سياق الحوار الحالي فقط أثناء الجلسة
}

# الهويات الهندسية لأعضاء المجلس
SYSTEM_PROMPTS = {
    "claude": (
        "أنت Claude، المهندس المعماري (Architect) في مجلس إدارة مشروع AATA للتداول الذكي. "
        "رئيس المجلس هو 'حميدة'. مهمتك تصميم المعمارية، كتابة الأكواد النظيفة، واقتراح الحلول الهندسية الدقيقة "
        "لتطوير AATA في أسواق الكريبتو، الفوركس، والمعادن. أجب باختصار، بتركيز هندسي، وباللغة العربية."
    ),
    "chatgpt": (
        "أنت ChatGPT، مسؤول ضمان الجودة والتدقيق (QA & Risk Auditor) في مجلس إدارة مشروع AATA. "
        "رئيس المجلس هو 'حميدة'. مهمتك مراجعة الأكواد والأفكار المطروحة، كشف الثغرات المنطقية أو البرمجية، "
        "وتدقيق حسابات المخاطر. لا تجامل، ركز على الأخطاء والتحسينات بدقة واختصار باللغة العربية."
    ),
    "gemini": (
        "أنت Gemini، مدير البنية التحتية والتشغيل (DevOps & Operations) في مجلس إدارة مشروع AATA. "
        "رئيس المجلس هو 'حميدة'. مهمتك تقييم استهلاك الموارد، التوافق مع سيرفر Render وقاعدة بيانات Supabase، "
        "وضبط تكلفة الـ API والتوكن. أجب بتركيز عملي ومباشر باللغة العربية."
    )
}

def build_context_text():
    """تجميع سجل الجلسة الحالية في نص واحد لإرساله للنموذج المستدعى فقط"""
    return "\n\n".join(session_state["history"])

# ==========================================
# 3. دوال استدعاء النماذج (تعمل فقط عند الأمر المباشر)
# ==========================================
def ask_claude(context):
    if not claude_client:
        return "⚠️ مفتاح ANTHROPIC_API_KEY غير مضاف في الإعدادات."
    try:
        response = claude_client.messages.create(
            model="claude-3-5-sonnet-latest",
            max_tokens=1200,
            system=SYSTEM_PROMPTS["claude"],
            messages=[{"role": "user", "content": f"سجل الجلسة حتى الآن:\n{context}\n\nقدم ردك الهندسي يا كلاود:"}]
        )
        return response.content[0].text
    except Exception as e:
        return f"❌ خطأ في اتصال كلاود: {str(e)}"

def ask_chatgpt(context):
    if not openai_client:
        return "⚠️ مفتاح OPENAI_API_KEY غير مضاف في الإعدادات."
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=1000,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPTS["chatgpt"]},
                {"role": "user", "content": f"سجل الجلسة حتى الآن:\n{context}\n\nقدم تدقيقك ومراجعتك يا شات:"}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ خطأ في اتصال شات جي بي تي: {str(e)}"

def ask_gemini(context):
    if not gemini_client:
        return "⚠️ مفتاح GEMINI_COUNCIL_KEY غير مضاف في الإعدادات."
    try:
        prompt = f"{SYSTEM_PROMPTS['gemini']}\n\nسجل الجلسة حتى الآن:\n{context}\n\nقدم تقييمك التشغيلي يا جيمي:"
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"❌ خطأ في اتصال جيمي: {str(e)}"

# ==========================================
# 4. معالج أوامر رئيس المجلس (حميدة) في تيليجرام
# ==========================================
@bot.message_handler(func=lambda message: True)
def council_orchestrator(message):
    text = message.text.strip()

    # 1. أمر بدء الجلسة
    if text == "بدء الجلسة":
        session_state["active"] = True
        session_state["history"] = []
        bot.reply_to(
            message,
            "🟢 **تم افتتاح جلسة مجلس AATA بنجاح.**\n"
            "جميع الأعضاء في وضع الاستماع الصامت (0 استهلاك توكن).\n"
            "تفضل بطرح الفكرة أو المشروع يا ريس، ثم وجه الأمر لمن تريد بصيغة:\n"
            "• `ردك يا كلاود`\n"
            "• `ردك يا شات`\n"
            "• `ردك يا جيمي`"
        )
        return

    # 2. أمر إغلاق الجلسة
    if text in ["إغلاق الجلسة", "اغلاق الجلسة", "ايقاف الجلسة", "إيقاف الجلسة"]:
        session_state["active"] = False
        session_state["history"] = []
        bot.reply_to(
            message,
            "🔴 **تم إغلاق الجلسة وتفريغ الذاكرة المؤقتة.**\n"
            "تم تأمين الميزانية وإيقاف الاستماع حتى الجلسة القادمة."
        )
        return

    # إذا كانت الجلسة مغلقة، يتجاهل البوت أي رسائل تماماً
    if not session_state["active"]:
        return

    # 3. أوامر استدعاء الأعضاء بالاسم
    if "ردك يا كلاود" in text or "ردك ي كلاود" in text:
        # إذا كتب الرئيس ملاحظة مع الأمر، نضيفها للسجل أولاً
        clean_note = text.replace("ردك يا كلاود", "").replace("ردك ي كلاود", "").strip()
        if clean_note:
            session_state["history"].append(f"👤 الرئيس (حميدة): {clean_note}")

        bot.send_chat_action(message.chat.id, 'typing')
        context = build_context_text()
        reply = ask_claude(context)
        formatted_reply = f"🏛️ **[Claude - المهندس المعماري]:**\n\n{reply}"
        session_state["history"].append(formatted_reply)
        bot.reply_to(message, formatted_reply)
        return

    if "ردك يا شات" in text or "ردك ي شات" in text:
        clean_note = text.replace("ردك يا شات", "").replace("ردك ي شات", "").strip()
        if clean_note:
            session_state["history"].append(f"👤 الرئيس (حميدة): {clean_note}")

        bot.send_chat_action(message.chat.id, 'typing')
        context = build_context_text()
        reply = ask_chatgpt(context)
        formatted_reply = f"🔍 **[ChatGPT - مدقق الجودة]:**\n\n{reply}"
        session_state["history"].append(formatted_reply)
        bot.reply_to(message, formatted_reply)
        return

    if "ردك يا جيمي" in text or "ردك ي جيمي" in text:
        clean_note = text.replace("ردك يا جيمي", "").replace("ردك ي جيمي", "").strip()
        if clean_note:
            session_state["history"].append(f"👤 الرئيس (حميدة): {clean_note}")

        bot.send_chat_action(message.chat.id, 'typing')
        context = build_context_text()
        reply = ask_gemini(context)
        formatted_reply = f"⚙️ **[Gemini - مدير التشغيل]:**\n\n{reply}"
        session_state["history"].append(formatted_reply)
        bot.reply_to(message, formatted_reply)
        return

    # 4. أمر التنفيذ الصريح
    if text == "نفذ":
        bot.reply_to(
            message,
            "✅ **تم استلام أمر التنفيذ الصريح من رئيس المجلس.**\n"
            "جاري تجهيز الحزمة النهائية المعتمدة للتطبيق..."
        )
        return

    # 5. أي رسالة أخرى منك تُحفظ في سجل النقاش بصمت تام دون صرف سنت واحد
    session_state["history"].append(f"👤 الرئيس (حميدة): {text}")
    bot.reply_to(message, "📝 *(تم تسجيل طرحك في محضر الجلسة بانتظار توجيهك لأحد الأعضاء)*")

# ==========================================
# 5. خادم ويب مصغر لإبقاء الخدمة حية على Render
# ==========================================
app = Flask(__name__)

@app.route('/')
def health_check():
    return "AATA Council Room is Running!", 200

if __name__ == "__main__":
    threading.Thread(target=lambda: bot.infinity_polling(skip_pending=True), daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
  
