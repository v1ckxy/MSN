class Client:
	__slots__ = ('program', 'version', 'via', '_tuple', '_hash')
	
	@classmethod
	def FromJSON(cls, json):
		return cls(json['program'], json['version'], json.get('via'))
	
	@classmethod
	def ToJSON(cls, client):
		return {
			'program': client.program,
			'version': client.version,
			'via': client.via,
		}
	
	def __init__(self, program, version, via = None):
		self.program = program
		self.version = version
		self.via = via
		self._tuple = (program, version, via)
		self._hash = hash(self._tuple)
	
	def __setattr__(self, attr, value):
		if getattr(self, '_hash', None) is None:
			super().__setattr__(attr, value)
			return
		raise AttributeError("Immutable")
	
	def __eq__(self, other):
		if not isinstance(other, Client):
			return False
		return self._tuple == other._tuple
	
	def __hash__(self):
		return self._hash
