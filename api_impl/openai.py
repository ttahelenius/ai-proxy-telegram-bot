from ..query import ApiImplementations, TextGenQuery, ImageGenQuery, ImageEditQuery, ContentType
from ..config import Feature
import json
import base64
from io import BytesIO
import puremagic

def bind(api_implementations: ApiImplementations):
    api_implementations.bind("OpenAI", Feature.TEXT_GENERATION, lambda: OpenAIChatQuery())
    api_implementations.bind("OpenAI", Feature.IMAGE_GENERATION, lambda: OpenAIImageQuery())
    api_implementations.bind("OpenAI", Feature.IMAGE_EDIT, lambda: OpenAIImageEditQuery())

class OpenAIChatQuery(TextGenQuery):
    def history_printer(self, l):
        return [{"role": r, "content": self.get_content(t, i)} for (r, t, i) in l]

    @staticmethod
    def get_content(text, images_base64):
        if not images_base64:
            return text
        elements = [{"type": "text", "text": text}]
        for image_base64 in images_base64:
            elements.append({
                "type": "image_url",
                "image_url": {
                    "url": "data:image/jpeg;base64," + image_base64,
                },
            })
        return elements

    def is_configured(self):
        return super().is_configured() and self.token

    def get_data(self, chat_id: int, reply_to_id: int) -> str:
        return json.dumps({"model": self.model, "messages": self.get_history(chat_id).get(reply_to_id)}
                          | {"stream": self.stream}
                          | self.params)

    def get_response_text(self, s: str) -> str:
        data_prefix = "data: "
        if s.startswith(data_prefix):
            body = s[len(data_prefix):]
        else:
            body = s
        if body == "[DONE]":
            return ""

        choice = json.loads(body)["choices"][0]

        if not self.stream:
            return choice["message"]["content"]

        delta = choice["delta"]
        if delta:
            return delta["content"]
        return ""


class OpenAIImageQuery(ImageGenQuery):
    def __init__(self):
        super().__init__(transient_history=True)

    def history_printer(self, l):
        return [t for (r, t, i) in l]

    def is_configured(self):
        return super().is_configured() and self.token

    def get_data(self, chat_id: int, reply_to_id: int) -> str:
        return json.dumps({"model": self.model, "prompt": self.get_history(chat_id).get(reply_to_id)[-1]} | self.params)

    def get_response_image_base64(self, s: str) -> str:
        return json.loads(s)["data"][0]["b64_json"]


class OpenAIImageEditQuery(ImageEditQuery):
    def __init__(self):
        super().__init__(transient_history=True)

    def get_content_type(self) -> 'ContentType':
        return ContentType.FORM

    def history_printer(self, l):
        return [(t, self.decode_base64(i)) for (r, t, i) in l]

    @staticmethod
    def decode_base64(images_base64: list[str]):
        return [base64.b64decode(image) for image in images_base64]

    def is_configured(self):
        return super().is_configured() and self.token

    def get_data(self, chat_id: int, reply_to_id: int) -> any:
        files = []
        files.append(("model", (None, self.model)))
        files.append(("prompt", (None, self.get_history(chat_id).get(reply_to_id)[-1][0])))
        i = 1
        for image in self.get_history(chat_id).get(reply_to_id)[-1][1]:
            files.append(("image[]", (f"img{i}", BytesIO(image), puremagic.from_string(image, mime=True))))
            i += 1
        for k, v in self.params.items():
            files.append((k, (None, v)))
        return files

    def get_response_image_base64(self, s: str) -> str:
        return json.loads(s)["data"][0]["b64_json"]