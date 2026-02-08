from ..query import ApiImplementations, TextGenQuery, ImageGenQuery
from ..config import Feature
import base64
import puremagic
import json

def bind(api_implementations: ApiImplementations):
    api_implementations.bind("Google", Feature.TEXT_GENERATION, lambda: GoogleChatQuery())
    api_implementations.bind("Google", Feature.IMAGE_AND_TEXT_GENERATION, lambda: GoogleImageQuery())

class GoogleChatQuery(TextGenQuery):
    def get_user_role(self):
        return "user"

    def get_assistant_role(self):
        return "model"

    def get_headers(self):
        h = {"x-goog-api-key": self.token} if self.token else {}
        return {"Content-Type": self.get_content_type().value} | h

    def get_url_suffix(self):
        return f"/{self.model}:{'streamGenerateContent?alt=sse' if self.stream else 'generateContent'}"

    def history_printer(self, l):
        return [{"role": r, "parts": self.get_content(t, i)} for (r, t, i) in l]

    @staticmethod
    def get_content(text, images_base64):
        elements = [{"text": text}]
        for image_base64 in images_base64:
            elements.append({
                "inlineData": {
                    "mimeType": puremagic.from_string(base64.b64decode(image_base64), mime=True),
                    "data": image_base64,
                },
            })
        return elements

    def is_configured(self):
        return super().is_configured() and self.token

    def get_data(self, chat_id: int, reply_to_id: int) -> str:
        return json.dumps({"contents": self.get_history(chat_id).get(reply_to_id)} | self.params)

    def get_response_text(self, s: str) -> str:
        data_prefix = "data: "
        if s.startswith(data_prefix):
            body = s[len(data_prefix):]
        else:
            body = s
        return json.loads(body)["candidates"][0]["content"]["parts"][0]["text"]


class GoogleImageQuery(ImageGenQuery):
    def __init__(self):
        super().__init__(transient_history=False)

    def get_user_role(self):
        return "user"

    def get_assistant_role(self):
        return "model"

    def get_headers(self):
        h = {"x-goog-api-key": self.token} if self.token else {}
        return {"Content-Type": self.get_content_type().value} | h

    def get_url_suffix(self):
        return f"/{self.model}:generateContent"

    def history_printer(self, l):
        return [{"role": r, "parts": self.get_content(t, i)} for (r, t, i) in l]

    @staticmethod
    def get_content(text, images_base64):
        elements = [{"text": text}]
        for image_base64 in images_base64:
            elements.append({
                "inlineData": {
                    "mimeType": puremagic.from_string(base64.b64decode(image_base64), mime=True),
                    "data": image_base64,
                },
            })
        return elements

    def is_configured(self):
        return super().is_configured() and self.token

    def get_data(self, chat_id: int, reply_to_id: int) -> str:
        return json.dumps({"contents": self.get_history(chat_id).get(reply_to_id)}
                          | {"generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}}
                          | self.params)

    def get_response_text(self, s: str) -> str | None:
        array = json.loads(s)["candidates"][0]["content"]["parts"]
        for element in array:
            if "text" in element:
                return element["text"]
        return None

    def get_response_image_base64(self, s: str) -> str | None:
        array = json.loads(s)["candidates"][0]["content"]["parts"]
        for element in array:
            if "inlineData" in element:
                return element["inlineData"]["data"]
        return None