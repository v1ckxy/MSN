from core.session import Session, SessionState
from core.client import Client
from core.models import Substatus, Lst
from core import event

CLIENT = Client('testbot', '0.1')
BOT_EMAIL = 'test@bot.log1p.xyz'

def register(loop, backend):
	state = Bot_NS_SessState(backend)
	sess = DirectSession(state)
	sess.client = CLIENT
	backend.login_IKWIAD(sess, BOT_EMAIL)
	backend.me_update(sess, { 'substatus': Substatus.NLN })
	
	user = sess.user
	uuid = backend.util_get_uuid_from_email('test1@example.com')
	if uuid not in user.detail.contacts:
		backend.me_contact_add(sess, uuid, Lst.FL, "Test 1")
		backend.me_contact_add(sess, uuid, Lst.AL, "Test 1")

class DirectSession(Session):
	def send_event(self, outgoing_event):
		self.state.apply_outgoing_event(outgoing_event, self)

class Bot_NS_SessState(SessionState):
	def __init__(self, backend):
		super().__init__()
		self.backend = backend
		self.chats = []
	
	def get_sb_extra_data(self):
		return {}
	
	def apply_outgoing_event(self, outgoing_event, sess: Session) -> None:
		if isinstance(outgoing_event, event.InvitedToChatEvent):
			cs = DirectSession(Bot_SB_SessState(self.backend))
			data = self.backend.login_cal(cs, BOT_EMAIL, outgoing_event.token, outgoing_event.chatid)
			if data:
				chat, _ = data
				self.chats.append(chat)
				cs.state.chat = chat
				chat.send_message_to_everyone(cs, (MSG_HEADER + "Hello, world!").encode('utf-8'))
			return
		print("NS outgoing", outgoing_event)
	
	def on_connection_lost(self, sess: Session) -> None:
		self.backend.on_leave(sess)

MSG_HEADER = '''
MIME-Version: 1.0
Content-Type: text/plain; charset=UTF-8
X-MMS-IM-Format: FN=MS%20Shell%20Dlg; EF=; CO=0; CS=0; PF=0

'''.replace('\n', '\r\n')

class Bot_SB_SessState(SessionState):
	def __init__(self, backend):
		super().__init__()
		self.backend = backend
		self.chat = None
	
	def apply_outgoing_event(self, outgoing_event, sess: Session) -> None:
		if isinstance(outgoing_event, event.ChatMessage):
			sender = outgoing_event.user_sender
			data = outgoing_event.data.decode('utf-8')
			if 'Content-Type: text/plain' not in data:
				return
			data = data.split('\r\n\r\n')[-1]
			msg = "You, {}, insist that \"{}\".".format(sender.status.name, data)
			self.chat.send_message_to_everyone(sess, (MSG_HEADER + msg).encode('utf-8'))
			return
		print("SB outgoing", outgoing_event)
	
	def on_connection_lost(self, sess: Session) -> None:
		self.chat.on_leave(sess)
