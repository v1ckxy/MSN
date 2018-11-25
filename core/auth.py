import bisect
from time import time as time_builtin
from functools import total_ordering
from util.hash import gen_salt

class AuthService:
	def __init__(self, *, time = None):
		if time is None:
			time = time_builtin
		self._time = time
		# List[TokenData], ordered by TokenData.expiry
		self._ordered = []
		# Dict[token, idx]
		self._bytoken = {}
		self._idxbase = 0
	
	def create_token(self, purpose, data, *, lifetime = 30):
		self._remove_expired()
		td = TokenData(purpose, data, self._time() + lifetime)
		assert td.token not in self._bytoken
		idx = bisect.bisect_left(self._ordered, td)
		self._ordered.insert(idx, td)
		self._bytoken[td.token] = idx + self._idxbase
		return td.token
	
	def pop_token(self, purpose, token):
		self._remove_expired()
		idx = self._bytoken.pop(token, None)
		if idx is None: return None
		idx -= self._idxbase
		td = self._ordered[idx]
		if not td.validate(purpose, token, self._time()): return None
		return td.data
	
	def _remove_expired(self):
		if not self._ordered: return
		dummy = TokenData(None, None, self._time())
		idx = bisect.bisect(self._ordered, dummy)
		if idx < 1: return
		self._idxbase += idx
		for td in self._ordered[:idx]:
			self._bytoken.pop(td.token, None)
		self._ordered = self._ordered[idx:]

@total_ordering
class TokenData:
	def __init__(self, purpose, data, expiry):
		self.token = gen_salt(20)
		self.purpose = purpose
		self.expiry = expiry
		self.data = data
	
	def __le__(self, other):
		return self.expiry <= other.expiry
	
	def validate(self, purpose, token, now):
		if self.expiry <= now: return False
		if self.purpose != purpose: return False
		if self.token != token: return False
		return True
