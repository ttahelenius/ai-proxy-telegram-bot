from query import Query
import config
import json

class ChatGPTQuery(Query):
	def __init__(self):
		url = config.get("OpenAI", "Url")
		model = config.get("OpenAI", "Model")
		super().__init__("^gpt ((.+\n*.*)+)$", url, model)
		self.token = config.get("OpenAI", "Token")
		self.headers = {"Authorization": "Bearer " + self.token,
				  		"Content-Type": "application/json"}
		
	def is_configured(self):
		return self.url and self.model and self.token
		
	def get_response_text(self, str: str) -> str:
		data_prefix = "data:"
		if str.startswith(data_prefix):
			body = str[len(data_prefix):]
		else:
			body = str
		if body == " [DONE]":
			return ""
		delta = json.loads(body)["choices"][0]["delta"]
		if delta:
			return delta["content"]
		return ""

	def get_data(self, chat_id: int, reply_to_id: int) -> str:
		return json.dumps({"model": self.model, "messages": self.get_history(chat_id).get(reply_to_id),
					 		"max_completion_tokens": config.get_int("OpenAI", "MaxCompletionTokens"), "stream": True})