from ..query import Query
from .. import config
import json

class OpenAIQuery(Query):
    def __init__(self):
        super().__init__(history_printer = self.history_printer, image_url_in_base64 = True)

    def get_vendor(self) -> str | None:
        return "OpenAI"

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

    def get_response_text(self, s: str) -> str:
        data_prefix = "data: "
        if s.startswith(data_prefix):
            body = s[len(data_prefix):]
        else:
            body = s
        if body == "[DONE]":
            return ""
        delta = json.loads(body)["choices"][0]["delta"]
        if delta:
            return delta["content"]
        return ""

    def get_model_parameters(self) -> dict[str, any]:
        return {"stream": True} | super().get_model_parameters()



class OpenAIGPTQuery(OpenAIQuery):
    def get_command(self) -> str | None:
        return "gpt"
    def get_model(self) -> str | None:
        return "GPTModel"
    def get_model_parameters(self) -> dict[str, any]:
        return config.get_key_value_pairs(self.get_vendor(), "GPTParams") | super().get_model_parameters()


class OpenAIO1Query(OpenAIQuery):
    def get_command(self) -> str | None:
        return "o1"
    def get_model(self) -> str | None:
        return "O1Model"
    def get_model_parameters(self) -> dict[str, any]:
        return config.get_key_value_pairs(self.get_vendor(), "O1Params") | super().get_model_parameters()