from .. import config
from ..query import Query

class GoogleQuery(Query):
    def get_vendor(self) -> str | None:
        return "Google"
    def get_model_parameters(self) -> dict[str, any]:
        return {"stream": True} | super().get_model_parameters()

class GemmaQuery(GoogleQuery):
    def __init__(self):
        super().__init__(history_printer = self.history_printer, image_url_in_base64=True)
    def history_printer(self, l):
        return [self.print_input(r, t, i) for (r, t, i) in l]
    @staticmethod
    def print_input(role, text, image):
        if image:
            return {"role": role, "content": text, "images": [image]}
        return {"role": role, "content": text}
    def get_command(self) -> str | None:
        return "gemma"
    def get_model(self) -> str | None:
        return "GemmaModel"
    def get_model_parameters(self) -> dict[str, any]:
        return config.get_key_value_pairs(self.get_vendor(), "GemmaParams") | super().get_model_parameters()