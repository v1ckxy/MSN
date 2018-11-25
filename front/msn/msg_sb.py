from .misc import Err, MSNPHandlers

_handlers = MSNPHandlers()
apply = _handlers.apply

# State = Auth

@_handlers
def _m_usr(sess, trid, arg, token):
	#>>> USR trid email@example.com token (MSNP < 18)
	#>>> USR trid email@example.com;{00000000-0000-0000-0000-000000000000} token (MSNP >= 18)
	state = sess.state
	(email, pop_id) = _decode_email_pop(arg)
	data = state.backend.login_xfr(sess, email, token)
	if data is None:
		sess.send_reply(Err.AuthFail, trid)
		return
	(chat, extra_data) = data
	dialect = extra_data['dialect']
	state.dialect = dialect
	state.chat = chat
	state.front_specific['msn_capabilities'] = extra_data['msn_capabilities']
	state.pop_id = pop_id
	sess.send_reply('USR', trid, 'OK', arg, sess.user.status.name)

@_handlers
def _m_ans(sess, trid, arg, token, sessid):
	#>>> ANS trid email@example.com token sessionid (MSNP < 18)
	#>>> ANS trid email@example.com;{00000000-0000-0000-0000-000000000000} token sessionid (MSNP >= 18)
	state = sess.state
	(email, pop_id) = _decode_email_pop(arg)
	data = state.backend.login_cal(sess, email, token, sessid)
	if data is None:
		sess.send_reply(Err.AuthFail, trid)
		return
	(chat, extra_data) = data
	dialect = extra_data['dialect']
	state.dialect = dialect
	state.chat = chat
	state.front_specific['msn_capabilities'] = extra_data['msn_capabilities']
	state.pop_id = pop_id
	
	chat.send_participant_joined(sess)
	
	roster = [
		(sc, su) for (sc, su) in chat.get_roster(sess)
		if su != sess.user
	]
	# This part will need a rewrite. Indeed, MSNP18 requires 2 IRO commands for the same user:
	# When you receive a chat from one contact, the server need to send:
	# IRO trID 1 2 email@address.com status capabilities
	# IRO trID 2 2 email@address.com;{xxxxxx-xxxx-xxxx-xxxxxxxxxx} status capabilities
	l = len(roster)
	for i, (sc, su) in enumerate(roster):
		extra = ()
		if dialect >= 13:
			extra = (sc.state.front_specific.get('msn_capabilities') or 0,)
		sess.send_reply('IRO', trid, i + 1, l, su.email, su.status.name, *extra)
	sess.send_reply('ANS', trid, 'OK')

# State = Live

@_handlers
def _m_cal(sess, trid, callee_email):
	#>>> CAL trid email@example.com
	state = sess.state
	user = sess.user
	chat = state.chat
	try:
		state.backend.notify_call(user.uuid, callee_email, chat.id)
	except Exception as ex:
		sess.send_reply(Err.GetCodeForException(ex), trid)
	else:
		sess.send_reply('CAL', trid, 'RINGING', chat.id)

@_handlers
def _m_msg(sess, trid, ack, data):
	#>>> MSG trid [UNAD] len
	sess.state.chat.send_message_to_everyone(sess, data)
	
	# TODO: Implement ACK/NAK
	if ack == 'U':
		return
	any_failed = False
	if any_failed: # ADN
		sess.send_reply('NAK', trid)
	elif ack != 'N': # AD
		sess.send_reply('ACK', trid)

def _decode_email_pop(s):
	# Split `foo@email.com;{uuid}` into (email, pop_id)
	parts = s.split(';', 1)
	if len(parts) < 2:
		pop_id = None
	else:
		pop_id = parts[1]
	return (parts[0], pop_id)
