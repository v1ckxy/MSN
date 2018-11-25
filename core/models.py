from enum import Enum, IntFlag

class User:
	def __init__(self, uuid, email, verified, status, date_created):
		self.uuid = uuid
		self.email = email
		self.verified = verified
		# `status`: true status of user
		self.status = status
		self.detail = None
		self.date_created = date_created

class Contact:
	def __init__(self, user, groups, lists, status, *, is_messenger_user = None):
		self.head = user
		self.groups = groups
		self.lists = lists
		# `status`: status as known by the contact
		self.status = status
		self.is_messenger_user = _default_if_none(is_messenger_user, True)
	
	def compute_visible_status(self, to_user):
		# Set Contact.status based on BLP and Contact.lists
		# If not blocked, Contact.status == Contact.head.status
		if self.head.detail is None or _is_blocking(self.head, to_user):
			self.status.substatus = Substatus.FLN
			return
		true_status = self.head.status
		self.status.substatus = true_status.substatus
		self.status.name = true_status.name
		self.status.message = true_status.message
		self.status.media = true_status.media

def _is_blocking(blocker, blockee):
	detail = blocker.detail
	contact = detail.contacts.get(blockee.uuid)
	lists = (contact and contact.lists or 0)
	if lists & Lst.BL: return True
	if lists & Lst.AL: return False
	return (detail.settings.get('BLP', 'AL') == 'BL')

class UserStatus:
	__slots__ = ('substatus', 'name', 'message', 'media')
	
	def __init__(self, name, message = None):
		self.substatus = Substatus.FLN
		self.name = name
		self.message = message
		self.media = None
	
	def is_offlineish(self):
		ss = self.substatus
		return ss == Substatus.FLN or ss == Substatus.HDN

class UserDetail:
	def __init__(self, settings):
		self.settings = settings
		self.groups = {}
		self.contacts = {}

class Group:
	def __init__(self, id, name, *, is_favorite = None):
		self.id = id
		self.name = name
		self.is_favorite = _default_if_none(is_favorite, False)

def _default_if_none(x, default):
	if x is None: return default
	return x

class Substatus(Enum):
	FLN = object()
	NLN = object()
	BSY = object()
	IDL = object()
	BRB = object()
	AWY = object()
	PHN = object()
	LUN = object()
	HDN = object()

class Lst(IntFlag):
	FL = 0x01
	AL = 0x02
	BL = 0x04
	RL = 0x08
	PL = 0x10
	
	@classmethod
	def Parse(cls, label):
		if not hasattr(cls, '_MAP'):
			map = {}
			for lst in cls:
				map[lst.label.lower()] = lst
			cls._MAP = map
		return cls._MAP.get(label.lower())
Lst.FL.label = "Follow"
Lst.AL.label = "Allow"
Lst.BL.label = "Block"
Lst.RL.label = "Reverse"
Lst.PL.label = "Pending"

class Service:
	def __init__(self, host, port):
		self.host = host
		self.port = port
