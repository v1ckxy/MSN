import io
from typing import List
from urllib.parse import unquote

from core.session import Session, SessionState
from core import event

from . import msg_ns, msg_sb
from .misc import build_msnp_presence_notif

class MSNPWriter:
	def __init__(self, logger, sess_state: SessionState):
		self._logger = logger
		self._buf = io.BytesIO()
		self._sess_state = sess_state
	
	def write(self, outgoing_event):
		if isinstance(outgoing_event, event.ReplyEvent):
			self._write(outgoing_event.data)
			return
		if isinstance(outgoing_event, event.PresenceNotificationEvent):
			for m in build_msnp_presence_notif(None, outgoing_event.contact, self._sess_state.dialect, self._sess_state.backend):
				self._write(m)
			return
		if isinstance(outgoing_event, event.AddedToListEvent):
			lst = outgoing_event.lst
			user = outgoing_event.user
			email = user.email
			name = (user.status.name or email)
			dialect = self._sess_state.dialect
			if dialect < 10:
				m = ('ADD', 0, lst.name, email, name)
			else:
				m = ('ADC', 0, lst.name, 'N={}'.format(email), 'F={}'.format(name))
			self._write(m)
			return
		if isinstance(outgoing_event, event.InvitedToChatEvent):
			chatid = outgoing_event.chatid
			token = outgoing_event.token
			caller = outgoing_event.caller
			extra = ()
			dialect = self._sess_state.dialect
			if dialect >= 13:
				extra = ('U', 'messenger.hotmail.com')
			if dialect >= 14:
				extra += (1,)
			self._write(['RNG', chatid, 'm1.escargot.log1p.xyz:1864', 'CKI', token, caller.email, caller.status.name, *extra])
			return
		if isinstance(outgoing_event, event.ChatParticipantLeft):
			user = outgoing_event.user
			self._write(['BYE', user.email])
			return
		if isinstance(outgoing_event, event.ChatParticipantJoined):
			sess = outgoing_event.sess
			user = sess.user
			extra = ()
			dialect = self._sess_state.dialect
			if dialect >= 13:
				extra = (self._sess_state.front_specific.get('msn_capabilities') or 0,)
			if dialect >= 18 and sess.state.pop_id and sess.state is not self._sess_state:
				self._write(['JOI', '{};{}'.format(user.email, sess.state.pop_id), user.status.name, *extra])
			self._write(['JOI', user.email, user.status.name, *extra])
			return
		if isinstance(outgoing_event, event.ChatMessage):
			user = outgoing_event.user_sender
			data = outgoing_event.data
			self._write(['MSG', user.email, user.status.name, data])
			return
		if isinstance(outgoing_event, event.POPBootEvent):
			self._write(['OUT', 'OTH'])
			return
		if isinstance(outgoing_event, event.POPNotifyEvent):
			# TODO: What do?
			return
		if isinstance(outgoing_event, event.CloseEvent):
			self._write(['OUT'])
			return
		
		raise Exception("Unknown outgoing_event", outgoing_event)
	
	def _write(self, m):
		_msnp_encode(m, self._buf, self._logger)
	
	def flush(self):
		data = self._buf.getvalue()
		if data:
			self._buf = io.BytesIO()
		return data

class MSNPReader:
	def __init__(self, logger):
		self.logger = logger
		self._data = b''
		self._i = 0
	
	def __iter__(self):
		return self
	
	def data_received(self, data):
		if self._data:
			self._data += data
		else:
			self._data = data
		while self._data:
			m = self._read_msnp()
			if m is None: break
			yield m
	
	def _read_msnp(self):
		try:
			m, body, e = _msnp_try_decode(self._data, self._i)
		except AssertionError:
			return None
		except Exception:
			print("ERR _read_msnp", self._i, self._data)
			raise
		
		self._data = self._data[e:]
		self._i = 0
		_truncated_log(self.logger, '>>>', m)
		m = [unquote(x) for x in m]
		if body:
			m.append(body)
		return m
	
	def _read_raw(self, n):
		i = self._i
		e = i + n
		assert e <= len(self._data)
		self._i += n
		return self._data[i:e]

def _msnp_try_decode(d, i) -> (List[str], int):
	# Try to parse an MSNP message from buffer `d` starting at index `i`
	# Returns (parsed message, end index)
	e = d.find(b'\n', i)
	assert e >= 0
	e += 1
	m = d[i:e].decode('utf-8').strip()
	assert len(m) > 1
	m = m.split()
	body = None
	if m[0] in _PAYLOAD_COMMANDS:
		n = int(m.pop())
		assert e+n <= len(d)
		body = d[e:e+n]
		e += n
	return m, body, e

_PAYLOAD_COMMANDS = {
	'UUX', 'MSG', 'ADL', 'FQY', 'RML', 'UUN'
}

def _msnp_encode(m: List[object], buf, logger) -> None:
	m = list(m)
	data = None
	if isinstance(m[-1], bytes):
		data = m[-1]
		m[-1] = len(data)
	m = tuple(str(x).replace(' ', '%20') for x in m if x is not None)
	_truncated_log(logger, '<<<', m)
	w = buf.write
	w(' '.join(m).encode('utf-8'))
	w(b'\r\n')
	if data is not None:
		w(data)

class MSNP_SessState(SessionState):
	def __init__(self, reader, backend):
		super().__init__()
		self.reader = reader
		self.backend = backend
		self.dialect = None
	
	def data_received(self, data: bytes, sess: Session) -> None:
		for incoming_event in self.reader.data_received(data):
			self.apply_incoming_event(incoming_event, sess)
	
	def apply_incoming_event(self, incoming_event, sess: Session) -> None:
		raise NotImplementedError('MSNP_SessState.apply_incoming_event')

class MSNP_NS_SessState(MSNP_SessState):
	def __init__(self, reader, backend):
		super().__init__(reader, backend)
		self.usr_email = None
		self.syn_ser = None
		self.iln_sent = False
		self.pop_id = None
	
	def get_sb_extra_data(self):
		return { 'dialect': self.dialect, 'msn_capabilities': self.front_specific.get('msn_capabilities') or 0 }
	
	def apply_incoming_event(self, incoming_event, sess) -> None:
		msg_ns.apply(incoming_event, sess)
	
	def on_connection_lost(self, sess: Session) -> None:
		self.backend.on_leave(sess)

class MSNP_SB_SessState(MSNP_SessState):
	def __init__(self, reader, backend):
		super().__init__(reader, backend)
		self.chat = None
		self.pop_id = None
	
	def apply_incoming_event(self, incoming_event, sess) -> None:
		msg_sb.apply(incoming_event, sess)
	
	def on_connection_lost(self, sess: Session) -> None:
		self.chat.on_leave(sess)

def _truncated_log(logger, pre, m):
	if m[0] in ('UUX', 'MSG', 'ADL'):
		logger.info(pre, *m[:-1], len(m[-1]))
	elif m[0] in ('CHG', 'ILN', 'NLN') and 'msnobj' in m[-1]:
		logger.info(pre, *m[:-1], '<truncated>')
	else:
		logger.info(pre, *m)
