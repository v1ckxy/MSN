class PresenceNotificationEvent:
	def __init__(self, contact):
		self.contact = contact

class AddedToListEvent:
	def __init__(self, lst, user):
		self.lst = lst
		self.user = user

class InvitedToChatEvent:
	def __init__(self, chatid, token, caller):
		self.chatid = chatid
		self.token = token
		self.caller = caller

class ChatParticipantJoined:
	def __init__(self, sess):
		self.sess = sess

class ChatParticipantLeft:
	def __init__(self, user):
		self.user = user

class ChatMessage:
	def __init__(self, user_sender, data):
		self.user_sender = user_sender
		self.data = data

class ReplyEvent:
	def __init__(self, data):
		self.data = data

class POPBootEvent:
	def __init__(self):
		pass

class POPNotifyEvent:
	def __init__(self):
		pass

class CloseEvent:
	pass
