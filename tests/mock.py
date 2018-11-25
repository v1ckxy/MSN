from collections import deque

from util.misc import gen_uuid
from models import User, Contact, UserDetail, Group, UserStatus, Lst

class UserService:
	def __init__(self):
		self._user_by_uuid = {}
		self._user_by_email = {}
		self._detail_by_uuid = {}
		
		self._add_user('test1@example.com')
		self._add_user('test2@example.com')
	
	def _add_user(self, email):
		u = User(gen_uuid(), email, True, UserStatus(email))
		self._user_by_uuid[u.uuid] = u
		self._user_by_email[u.email] = u
		self._detail_by_uuid[u.uuid] = UserDetail({})
	
	def update_date_login(self, uuid):
		pass
	
	def get_uuid(self, email):
		user = self._user_by_email.get(email)
		return user and user.uuid
	
	def get(self, uuid):
		return self._user_by_uuid.get(uuid)
	
	def get_detail(self, uuid):
		return self._detail_by_uuid.get(uuid)
	
	def save_batch(self, to_save):
		for user, detail in to_save:
			assert detail is not None
			self._detail_by_uuid[user.uuid] = detail

class MSNPWriter:
	def __init__(self):
		self._q = deque()
	
	def write(self, *m):
		self._q.append(tuple(str(x) for x in m if x is not None))
	
	def pop_message(self, *msg_expected):
		msg = self._q.popleft()
		assert len(msg) == len(msg_expected)
		for mi, mei in zip(msg, msg_expected):
			if mei is ANY: continue
			assert mi == str(mei)
		return msg
	
	def assert_empty(self):
		assert not self._q

class AnyCls:
	def __repr__(self): return '<ANY>'
ANY = AnyCls()
