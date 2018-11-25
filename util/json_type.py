from sqlalchemy import types
import json

class StringyJSON(types.TypeDecorator):
	impl = types.TEXT
	
	def process_bind_param(self, value, dialect):
		if value is not None:
			value = json.dumps(value)
		return value
	
	def process_result_value(self, value, dialect):
		if value is not None:
			value = json.loads(value)
		return value

JSONType = StringyJSON
