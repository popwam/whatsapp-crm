from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
import pandas as pd
import json, os
from datetime import datetime
from dotenv import load_dotenv
from sender import MessageSender
import requests

load_dotenv()

app = Flask(__name__)
sender = MessageSender()
app.secret_key = "popwam_mmdouh_2025_capital_gate"
DATA_DIR = "data"
UPLOAD_DIR = "uploads"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

MESSAGES_FILE = os.path.join(DATA_DIR, "messages.json")
USERS_FILE = os.path.join(DATA_DIR, "users_temp.json")
EXCEL_FILE = os.path.join(UPLOAD_DIR, "users.xlsx")
CSV_EXPORT_FILE = os.path.join(DATA_DIR, "clients.csv")

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
PHONE_ID = os.getenv("PHONE_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "my_secret_token")

API_URL = f"https://graph.facebook.com/v23.0/{PHONE_ID}/messages"


def check_whatsapp_number(number):
    if number.startswith("20") or number.startswith("966") or number.startswith("971"):
        return "valid"
    return "invalid"
def send_message(number, message):
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": number,
        "type": "text",
        "text": {"body": message}
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        print("\n📨 [RESPONSE WHATSAPP]", number)
        print("Status Code:", response.status_code)
        print("Response JSON:", response.json())
        return response.json()
    except Exception as e:
        print("❌ Error sending message:", e)
        return None
def time_ago(timestamp):
    try:
        dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        diff = datetime.now() - dt
        minutes = int(diff.total_seconds() / 60)
        if minutes < 1:
            return "الآن"
        elif minutes < 60:
            return f"منذ {minutes} دقيقة"
        hours = int(minutes / 60)
        if hours < 24:
            return f"منذ {hours} ساعة"
        return dt.strftime("%Y-%m-%d")
    except:
        return timestamp

@app.route("/")
def index():
    messages_in = []
    messages_out = []

    if os.path.exists(MESSAGES_FILE):
        with open(MESSAGES_FILE, "r", encoding="utf-8") as f:
            all_messages = json.load(f)
            for msg in all_messages:
                raw_time = msg.get("updated") or msg.get("timestamp")
                if isinstance(raw_time, int) or (isinstance(raw_time, str) and raw_time.isdigit()):
                    raw_time = datetime.fromtimestamp(int(raw_time)).strftime("%Y-%m-%d %H:%M:%S")
                msg["time_ago"] = time_ago(raw_time)
                msg["display_time"] = raw_time
                msg["unread"] = msg.get("status") != "read" if msg.get("direction") == "out" else False
                if msg.get("direction") == "in":
                    messages_in.append(msg)
                elif msg.get("direction") == "out":
                    messages_out.append(msg)

    return render_template(
    "index.html",
    messages_in=messages_in,
    messages_out=messages_out,
    all_messages=messages_in + messages_out  # أو حسب ترتيبك
)
@app.route("/send_bulk_confirm")
def send_bulk_confirm():
    numbers = session.get("bulk_numbers", [])
    return render_template("send_bulk_confirm.html", numbers=numbers)
@app.route("/send_single", methods=["POST"])
def send_single():
    number = request.form.get("number")
    message = request.form.get("message", "").strip()
    template = request.form.get("template")
    image_file = request.files.get("image")
    variable = request.form.get("variable")
    link = request.form.get("link")

    if not number:
        return "❌ رقم غير صالح", 400

    response = None
    msg_data = {
        "from": "أنت",
        "to": number,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "direction": "out",
        "status": "pending"
    }

    # 🧩 إرسال قالب
    if template:
        if template == "marketing_dee":
            if not image_file or image_file.filename == "":
                return "❌ يجب رفع صورة لهذا القالب", 400
            image_path = os.path.join("uploads", image_file.filename)
            image_file.save(image_path)
            name_var = message if message else "عميلنا العزيز"
            response = sender.send_template_image(template, number, image_path, name_var)
            msg_data["image_url"] = f"/media/{image_file.filename}"
            msg_data["template"] = template
            msg_data["text"] = f"🧩 تم إرسال قالب {template} بـ {name_var}"

        elif template in ["verification", "verification_ar"]:
            if not variable or not link:
                return "❌ لازم تدخل الكود والرابط", 400
            response = sender.send_template(number, template, parameters=[variable, link])
            msg_data["template"] = template
            msg_data["text"] = f"🔐 كود: {variable}"

        elif template == "welcome_template":
            response = sender.send_template(number, "welcome_template")
            msg_data["template"] = template
            msg_data["text"] = f"📩 قالب ترحيبي تم إرساله"

    # 💬 إرسال نص عادي أو صورة
    elif image_file and image_file.filename != "":
        image_path = os.path.join("uploads", image_file.filename)
        image_file.save(image_path)
        response = sender.send_image(number, image_path)
        msg_data["image_url"] = f"/media/{image_file.filename}"
    elif message:
        response = sender.send_message(number, message)
        msg_data["text"] = message
    else:
        return "❌ لازم رسالة نصية أو اختيار قالب", 400

    if response:
        msg_data["message_id"] = response.get("messages", [{}])[0].get("id")

    all_msgs = []
    if os.path.exists(MESSAGES_FILE):
        with open(MESSAGES_FILE, "r", encoding="utf-8") as f:
            all_msgs = json.load(f)

    all_msgs.append(msg_data)

    with open(MESSAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(all_msgs, f, ensure_ascii=False, indent=2)

    return redirect("/")
def get_media_url(media_id):
    media_info = requests.get(
        f"https://graph.facebook.com/v23.0/{media_id}",
        headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}
    )
    if media_info.status_code == 200:
        return media_info.json().get("url")
    else:
        print("❌ فشل في جلب رابط الصورة:", media_info.text)
        return None
def download_image(media_url, filename):
    res = requests.get(media_url, headers={"Authorization": f"Bearer {ACCESS_TOKEN}"})
    if res.status_code == 200:
        path = os.path.join("uploads", filename)
        with open(path, "wb") as f:
            f.write(res.content)
        return f"/media/{filename}"
    else:
        print("❌ فشل تحميل الصورة:", res.text)
        return None

@app.route("/media/<filename>")
def media(filename):
    return send_from_directory("uploads", filename) 

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200
        else:
            return "Forbidden", 403

    elif request.method == "POST":
        data = request.get_json()
        print("📩 Webhook Received:", json.dumps(data, indent=2, ensure_ascii=False))

        try:
            all_msgs = []
            if os.path.exists(MESSAGES_FILE):
                with open(MESSAGES_FILE, "r", encoding="utf-8") as f:
                    all_msgs = json.load(f)

            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})

                    # استقبال رسائل جديدة
                    for i, msg in enumerate(value.get("messages", [])):
                        number = msg.get("from")
                        timestamp = msg.get("timestamp", "")
                        name = value.get("contacts", [{}])[i].get("profile", {}).get("name", "غير معروف")
                        
                        msg_type = msg.get("type")
                        received_msg = {
                            "from": number,
                            "name": name,
                            "timestamp": timestamp,
                            "direction": "in",
                            "type": msg_type
                        }

                        if msg_type == "text":
                            received_msg["text"] = msg["text"]["body"]
                        elif msg_type == "image":
                            media_id = msg["image"]["id"]
                            media_url = get_media_url(media_id)
                            if media_url:
                                filename = f"{media_id}.jpg"
                                local_url = download_image(media_url, filename)
                                received_msg["media"] = local_url
                            received_msg["caption"] = msg["image"].get("caption", "")
                        elif msg_type == "document":
                            received_msg["media_id"] = msg["document"]["id"]
                            received_msg["filename"] = msg["document"].get("filename", "")

                        all_msgs.append(received_msg)

                    # تحديث حالة الرسائل المرسلة
                    for status in value.get("statuses", []):
                        message_id = status.get("id")
                        status_type = status.get("status")
                        number = status.get("recipient_id")
                        timestamp = int(status.get("timestamp", 0))
                        updated_time = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

                        for msg in all_msgs:
                            if msg.get("message_id") == message_id and msg.get("to") == number and msg.get("direction") == "out":
                                msg["status"] = status_type
                                msg["updated"] = updated_time
                                break

            with open(MESSAGES_FILE, "w", encoding="utf-8") as f:
                json.dump(all_msgs, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print("❌ Webhook Error:", e)

        return jsonify({"status": "received"}), 200


@app.route("/upload_excel", methods=["GET", "POST"])
def upload_excel():
    if request.method == "POST":
        file = request.files.get("excel_file")
        if not file or not file.filename.endswith(".xlsx"):
            return "❌ برجاء رفع ملف Excel صالح", 400

        df = pd.read_excel(file)

        numbers = []
        for _, row in df.iterrows():
            number = str(row.get("number") or "").strip()
            name = str(row.get("name") or "").strip()

            if number:
                numbers.append({"number": number, "name": name})
        session["bulk_numbers"] = numbers
        return redirect("/send_bulk_confirm")

    return render_template("upload_excel.html")

@app.route("/send_bulk", methods=["POST"])
def send_bulk():
    selected_numbers = request.form.getlist("selected_numbers")  # جاي من الـ checkbox
    message = request.form.get("message", "")
    template = request.form.get("template")
    image_file = request.files.get("image")

    if not selected_numbers:
        return "❌ لازم تختار أرقام", 400

    sender = MessageSender()
    results = []

    for number in selected_numbers:
        try:
            name = number.split("|")[1] if "|" in number else ""
            number = number.split("|")[0]
            if template == "marketing_dee":
                if not image_file:
                    continue
                image_path = os.path.join("uploads", image_file.filename)
                image_file.save(image_path)
                res = sender.send_template_image(template, number, image_path, name or message)
            elif template in ["verification", "verification_ar"]:
                link = request.form.get("link")
                res = sender.send_template(number, template, parameters=[message, link])
            elif template == "welcome_template":
                res = sender.send_template(number, "welcome_template")
            else:
                res = sender.send_message(number, message)

            results.append({"number": number, "status": "sent"})
        except Exception as e:
            results.append({"number": number, "status": f"failed: {e}"})

    return render_template("send_bulk_result.html", results=results)

if __name__ == "__main__":
    app.run()
