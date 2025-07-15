import requests
import os
import json
import mimetypes
import time
from dotenv import load_dotenv

load_dotenv()

class MessageSender:
    def __init__(self, access_token=None, phone_number_id=None, use_mock=False):
        self.access_token = access_token or os.getenv("ACCESS_TOKEN")
        self.phone_number_id = phone_number_id or os.getenv("PHONE_ID")
        self.use_mock = use_mock
        self.api_url = f"https://graph.facebook.com/v23.0/{self.phone_number_id}/messages"
        self.media_url = f"https://graph.facebook.com/v23.0/{self.phone_number_id}/media"

    def send_message(self, number, message):
        if self.use_mock:
            print(f"[MOCK] إرسال إلى {number}: {message}")
            return {"messages": [{"id": f"mock-{number}-{int(time.time())}"}]}

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": number,
            "type": "text",
            "text": {"body": message},
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=payload)
            print(f"\n📨 [RESPONSE WHATSAPP] {number}:")
            print(f"Status Code: {response.status_code}")
            print("Response JSON:", response.text)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ فشل الإرسال لـ {number}: {e}")
            return None

    def upload_to_media(self, image_path):
        mime_type, _ = mimetypes.guess_type(image_path)

        with open(image_path, 'rb') as img_file:
            files = {
                'file': (os.path.basename(image_path), img_file, mime_type),
                'messaging_product': (None, 'whatsapp')
            }

            headers = {
                "Authorization": f"Bearer {self.access_token}"
            }

            res = requests.post(self.media_url, headers=headers, files=files)

            if res.status_code == 200:
                return res.json().get("id")
            else:
                print("❌ Upload Error:", res.status_code, res.text)
                return None

    def send_image(self, number, image_path):
        media_id = self.upload_to_media(image_path)
        if not media_id:
            return None

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        data = {
            "messaging_product": "whatsapp",
            "to": number,
            "type": "image",
            "image": {
                "id": media_id
            }
        }

        res = requests.post(self.api_url, headers=headers, json=data)
        if res.status_code != 200:
            print("❌ Error sending image:", res.status_code, res.text)
        return res.json()

    def send_template(self, number, template_name, language_code="ar", parameters=[]):
        if self.use_mock:
            print(f"[MOCK] قالب إلى {number} - {template_name} - params: {parameters}")
            return {"messages": [{"id": "mock-template-id"}]}

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        components = []

        if parameters:
            body_param = {"type": "text", "text": str(parameters[0])}
            components.append({"type": "body", "parameters": [body_param]})

        if len(parameters) > 1:
            button_param = {"type": "text", "text": str(parameters[1])}
            components.append({
                "type": "button",
                "sub_type": "url",
                "index": "0",
                "parameters": [button_param]
            })

        payload = {
            "messaging_product": "whatsapp",
            "to": number,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
                "components": components,
            },
        }

        try:
            print("📤 Sending template payload to WhatsApp:")
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            response = requests.post(self.api_url, headers=headers, json=payload)
            print("📩 Response Content:", response.text)
            response.raise_for_status()
            print(f"✅ تم إرسال القالب لـ {number}")
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ فشل إرسال القالب لـ {number}: {e}")
            return None

    def send_template_image(self, template_name, number, image_path, variable):
        media_id = self.upload_to_media(image_path)
        if not media_id:
            return None

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "messaging_product": "whatsapp",
            "to": number,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": "en"},
                "components": [
                    {
                        "type": "header",
                        "parameters": [
                            {"type": "image", "image": {"id": media_id}}
                        ]
                    },
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": variable}
                        ]
                    }
                ]
            }
        }

        try:
            print(f"📤 Sending image template to {number}")
            res = requests.post(self.api_url, headers=headers, json=payload)
            print("📩 Response Content:", res.text)
            res.raise_for_status()
            return res.json()
        except Exception as e:
            print("❌ Error sending template image:", e)
            return None

    def send_template_text(self, template_name, number, variables):
        return self.send_template(
            number=number,
            template_name=template_name,
            language_code="ar",
            parameters=variables
        )
