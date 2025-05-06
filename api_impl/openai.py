from ..query import Query, ApiImplementations
import json

def bind(api_implementations: ApiImplementations):
    api_implementations.bind("OpenAI", "Text gen", lambda: OpenAIQuery())

class OpenAIQuery(Query):
    def history_printer(self, l):
        return [{"role": r, "content": self.get_content(t, i)} for (r, t, i) in l]

    @staticmethod
    def get_content(text, image_url):
        if image_url is None:
            return text
        return [
            {"type": "text", "text": text},
            {
                "type": "image_url",
                "image_url": {
                    "url": "data:image/jpeg;base64," + image_url,
                },
            },
        ]

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
