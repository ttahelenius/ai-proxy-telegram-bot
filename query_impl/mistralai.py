from .. import config
from ..query import Query

class MistralAiQuery(Query):
    def get_vendor(self) -> str | None:
        return "MistralAI"
    def get_model_parameters(self) -> dict[str, any]:
        return {"stream": True} | super().get_model_parameters()

class MistralQuery(MistralAiQuery):
    def get_command(self) -> str | None:
        return "mistral"
    def get_model(self) -> str | None:
        return "MistralModel"
    def get_model_parameters(self) -> dict[str, any]:
        return config.get_key_value_pairs(self.get_vendor(), "MistralParams") | super().get_model_parameters()