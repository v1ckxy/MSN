from datetime import datetime
from lxml.objectify import fromstring as parse_xml

from core import session
from core.models import Substatus, Lst
from core.client import Client

from .misc import build_msnp_presence_notif, MSNPHandlers, encode_msnobj, Err

_handlers = MSNPHandlers()
apply = _handlers.apply

MSNP_DIALECTS = ['MSNP{}'.format(d) for d in (
	# Not actually supported
	21, 20, 19, 18, 17, 16,
	# Actually supported
	15, 14, 13, 12, 11, 10,
	9, 8, 7, 6, 5, 4, 3, 2,
)]

# State = Auth

@_handlers
def _m_ver(sess, trid, *args):
	dialects = [a.upper() for a in args]
	d = None
	for d in MSNP_DIALECTS:
		if d in dialects: break
	if d not in dialects:
		sess.send_reply('VER', trid, 0, *MSNP_DIALECTS)
		return
	sess.state.dialect = int(d[4:])
	# For older clients that don't do a CVR
	sess.client = Client('msn', d, 'gw' if isinstance(sess, session.PollingSession) else 'direct')
	sess.send_reply('VER', trid, d)

@_handlers
def _m_cvr(sess, trid, *args):
	v = args[5]
	sess.client = Client('msn', v, 'gw' if isinstance(sess, session.PollingSession) else 'direct')
	sess.send_reply('CVR', trid, v, v, v, 'https://escargot.log1p.xyz', 'https://escargot.log1p.xyz')

@_handlers
def _m_inf(sess, trid):
	if sess.state.dialect < 8:
		sess.send_reply('INF', trid, 'MD5')
	else:
		sess.send_reply(Err.CommandDisabled, trid)

@_handlers
def _m_usr(sess, trid, authtype, stage, *args):
	state = sess.state
	backend = state.backend
	
	if authtype == 'SHA':
		# Used in MSNP18 (at least, for now) to validate Circle tickets
		# found in ABFindAll or ABFindContactsPaged response
		sess.send_reply('USR', trid, 'OK', state.usr_email, 0, 0)
		return
	
	if authtype == 'MD5':
		if state.dialect >= 8:
			sess.send_reply(Err.CommandDisabled, trid)
			return
		if stage == 'I':
			email = args[0]
			salt = backend.login_md5_get_salt(email)
			if salt is None:
				# Account is not enabled for login via MD5
				# TODO: Can we pass an informative message to user?
				sess.send_reply(Err.AuthFail, trid)
				return
			state.usr_email = email
			sess.send_reply('USR', trid, authtype, 'S', salt)
			return
		if stage == 'S':
			md5_hash = args[0]
			backend.login_md5_verify(sess, state.usr_email, md5_hash)
			_util_usr_final(sess, trid, None)
			return
	
	if authtype in ('TWN', 'SSO'):
		if stage == 'I':
			#>>> USR trid TWN/SSO I email@example.com
			state.usr_email = args[0]
			if authtype == 'TWN':
				#extra = ('ct={},rver=5.5.4177.0,wp=FS_40SEC_0_COMPACT,lc=1033,id=507,ru=http:%2F%2Fmessenger.msn.com,tw=0,kpp=1,kv=4,ver=2.1.6000.1,rn=1lgjBfIL,tpf=b0735e3a873dfb5e75054465196398e0'.format(int(time())),)
				# This seems to work too:
				extra = ('ct=1,rver=1,wp=FS_40SEC_0_COMPACT,lc=1,id=1',)
			else:
				# https://web.archive.org/web/20100819015007/http://msnpiki.msnfanatic.com/index.php/MSNP15:SSO
				extra = ('MBI_KEY_OLD', '8CLhG/xfgYZ7TyRQ/jIAWyDmd/w4R4GF2yKLS6tYrnjzi4cFag/Nr+hxsfg5zlCf')
			sess.send_reply('USR', trid, authtype, 'S', *extra)
			return
		if stage == 'S':
			#>>> USR trid TWN S auth_token
			#>>> USR trid SSO S auth_token b64_response
			token = args[0]
			if token[0:2] == 't=':
				token = token[2:22]
			backend.login_twn_verify(sess, state.usr_email, token)
			_util_usr_final(sess, trid, token)
			return
	
	sess.send_reply(Err.AuthFail, trid)

def _util_usr_final(sess, trid, token):
	user = sess.user
	dialect = sess.state.dialect
	
	if user is None:
		sess.send_reply(Err.AuthFail, trid)
		return
	
	if token:
		sess.state.backend.util_set_sess_token(sess, token)
	
	if dialect < 18:
		sess.state.backend.me_pop_boot_others(sess)
	else:
		sess.state.backend.me_pop_notify_others(sess)
	
	if dialect < 10:
		args = (user.status.name,)
	else:
		args = ()
	if dialect >= 8:
		#verified = user.verified
		verified = True
		args += ((1 if verified else 0), 0)
	
	sess.send_reply('USR', trid, 'OK', user.email, *args)
	
	if dialect < 13:
		return
	
	(high, low) = _uuid_to_high_low(user.uuid)
	(ip, port) = sess.get_peername()
	now = datetime.utcnow()
	
	if dialect == 21:
		sess.send_reply('CHL', 0, '1663122458434562624782678054')
		msg0 = _encode_payload(PAYLOAD_MSG_0,
			email_address = user.email,
			endpoint_ID = '{00000000-0000-0000-0000-000000000000}',
			timestamp = now.isoformat()[:19] + 'Z',
		)
		sess.send_reply('NFY', 'PUT', msg0)
	else:
		sess.send_reply('SBS', 0, 'null')
		if 18 <= dialect < 21:
			# MSNP21 doesn't use this; unsure if 19/20 use it
			sess.send_reply('UBX', '1:' + user.email, b'')
		sess.send_reply('PRP', 'MFN', user.status.name)
	
	msg1 = _encode_payload(PAYLOAD_MSG_1,
		time = now.timestamp(), high = high, low = low,
		token = token, ip = ip, port = port,
	)
	sess.send_reply('MSG', 'Hotmail', 'Hotmail', msg1)
	
	msg2 = _encode_payload(PAYLOAD_MSG_2)
	sess.send_reply('MSG', 'Hotmail', 'Hotmail', msg2)

# State = Live

@_handlers
def _m_syn(sess, trid, *extra):
	user = sess.user
	dialect = sess.state.dialect
	detail = user.detail
	contacts = detail.contacts
	groups = detail.groups
	settings = detail.settings
	
	if dialect < 10:
		sess.state.syn_ser = int(extra[0])
		ser = _ser(sess.state)
		if dialect < 6:
			sess.send_reply('SYN', trid, ser)
			for lst in (Lst.FL, Lst.AL, Lst.BL, Lst.RL):
				cs = [c for c in contacts.values() if c.lists & lst]
				if cs:
					for i, c in enumerate(cs):
						sess.send_reply('LST', trid, lst.name, ser, len(cs), i + 1, c.head.email, c.status.name)
				else:
					sess.send_reply('LST', trid, lst.name, ser, 0, 0)
			sess.send_reply('GTC', trid, ser, settings.get('GTC', 'A'))
			sess.send_reply('BLP', trid, ser, settings.get('BLP', 'AL'))
		elif dialect < 8:
			sess.send_reply('SYN', trid, ser)
			num_groups = len(groups) + 1
			sess.send_reply('LSG', trid, ser, 1, num_groups, '0', "Other Contacts", 0)
			for i, g in enumerate(groups.values()):
				sess.send_reply('LSG', trid, ser, i + 2, num_groups, g.id, g.name, 0)
			for lst in (Lst.FL, Lst.AL, Lst.BL, Lst.RL):
				cs = [c for c in contacts.values() if c.lists & lst]
				if cs:
					for i, c in enumerate(cs):
						gs = ((','.join(c.groups) or '0') if lst == Lst.FL else None)
						sess.send_reply('LST', trid, lst.name, ser, i + 1, len(cs), c.head.email, c.status.name, gs)
				else:
					sess.send_reply('LST', trid, lst.name, ser, 0, 0)
			sess.send_reply('GTC', trid, ser, settings.get('GTC', 'A'))
			sess.send_reply('BLP', trid, ser, settings.get('BLP', 'AL'))
		else:
			num_groups = len(groups) + 1
			sess.send_reply('SYN', trid, ser, len(contacts), num_groups)
			sess.send_reply('GTC', settings.get('GTC', 'A'))
			sess.send_reply('BLP', settings.get('BLP', 'AL'))
			sess.send_reply('LSG', '0', "Other Contacts", 0)
			for g in groups.values():
				sess.send_reply('LSG', g.id, g.name, 0)
			for c in contacts.values():
				sess.send_reply('LST', c.head.email, c.status.name, c.lists, ','.join(c.groups) or '0')
	else:
		sess.send_reply('SYN', trid, TIMESTAMP, TIMESTAMP, len(contacts), len(groups))
		sess.send_reply('GTC', settings.get('GTC', 'A'))
		sess.send_reply('BLP', settings.get('BLP', 'AL'))
		sess.send_reply('PRP', 'MFN', user.status.name)
		
		for g in groups.values():
			sess.send_reply('LSG', g.name, g.id)
		for c in contacts.values():
			sess.send_reply('LST', 'N={}'.format(c.head.email), 'F={}'.format(c.status.name), 'C={}'.format(c.head.uuid),
				c.lists, (None if dialect < 12 else 1), ','.join(c.groups)
			)

@_handlers
def _m_gcf(sess, trid, filename):
	sess.send_reply('GCF', trid, filename, SHIELDS)

@_handlers
def _m_png(sess):
	sess.send_reply('QNG', (60 if sess.state.dialect >= 9 else None))

@_handlers
def _m_uux(sess, trid, data):
	elm = parse_xml(data.decode('utf-8'))
	
	psm = elm.find('PSM')
	cm = elm.find('CurrentMedia')
	if psm or cm:
		sess.state.backend.me_update(sess, {
			'message': str(elm.find('PSM')),
			'media': str(elm.find('CurrentMedia')),
		})
	
	mg = elm.find('MachineGuid')
	if mg:
		sess.state.pop_id = str(mg)[1:-1]
	
	sess.send_reply('UUX', trid, 0)

@_handlers
def _m_url(sess, trid, *ignored):
	sess.send_reply('URL', trid, '/unused1', '/unused2', 1)

@_handlers
def _m_adg(sess, trid, name, ignored = None):
	#>>> ADG 276 New Group
	try:
		group = sess.state.backend.me_group_add(sess, name)
	except Exception as ex:
		sess.send_reply(Err.GetCodeForException(ex), trid)
		return
	sess.send_reply('ADG', trid, _ser(sess.state), name, group.id, 0)

@_handlers
def _m_rmg(sess, trid, group_id):
	#>>> RMG 250 00000000-0000-0000-0001-000000000001
	if group_id == 'New%20Group':
		# Bug: MSN 7.0 sends name instead of id in a particular scenario
		for g in sess.user.detail.groups.values():
			if g.name != 'New Group': continue
			group_id = g.id
			break
	
	try:
		sess.state.backend.me_group_remove(sess, group_id)
	except Exception as ex:
		sess.send_reply(Err.GetCodeForException(ex), trid)
		return
	
	sess.send_reply('RMG', trid, _ser(sess.state) or 1, group_id)

@_handlers
def _m_reg(sess, trid, group_id, name, ignored = None):
	#>>> REG 275 00000000-0000-0000-0001-000000000001 newname
	try:
		sess.state.backend.me_group_edit(sess, group_id, name)
	except Exception as ex:
		sess.send_reply(Err.GetCodeForException(ex), trid)
		return
	if sess.state.dialect < 10:
		sess.send_reply('REG', trid, _ser(sess.state), group_id, name, 0)
	else:
		sess.send_reply('REG', trid, 1, name, group_id, 0)

@_handlers
def _m_adc(sess, trid, lst_name, arg1, arg2 = None):
	if arg1.startswith('N='):
		#>>> ADC 249 BL N=bob1@hotmail.com
		#>>> ADC 278 AL N=foo@hotmail.com
		#>>> ADC 277 FL N=foo@hotmail.com F=foo@hotmail.com
		contact_uuid = sess.state.backend.util_get_uuid_from_email(arg1[2:])
		group_id = None
		name = (arg2[2:] if arg2 else None)
	else:
		# Add C= to group
		#>>> ADC 246 FL C=00000000-0000-0000-0002-000000000002 00000000-0000-0000-0001-000000000003
		contact_uuid = arg1[2:]
		group_id = arg2
		name = None
	
	_add_common(sess, trid, lst_name, contact_uuid, name, group_id)

@_handlers
def _m_add(sess, trid, lst_name, email, name = None, group_id = None):
	#>>> ADD 122 FL email name group
	contact_uuid = sess.state.backend.util_get_uuid_from_email(email)
	_add_common(sess, trid, lst_name, contact_uuid, name, group_id)

def _add_common(sess, trid, lst_name, contact_uuid, name = None, group_id = None):
	lst = getattr(Lst, lst_name)
	
	try:
		ctc, ctc_head = sess.state.backend.me_contact_add(sess, contact_uuid, lst, name)
		if group_id:
			sess.state.backend.me_group_contact_add(sess, group_id, contact_uuid)
	except Exception as ex:
		sess.send_reply(Err.GetCodeForException(ex), trid)
		return
	
	if sess.state.dialect >= 10:
		if lst == Lst.FL:
			if group_id:
				sess.send_reply('ADC', trid, lst_name, 'C={}'.format(ctc_head.uuid), group_id)
			else:
				sess.send_reply('ADC', trid, lst_name, 'N={}'.format(ctc_head.email), 'C={}'.format(ctc_head.uuid))
		else:
			sess.send_reply('ADC', trid, lst_name, 'N={}'.format(ctc_head.email))
	else:
		sess.send_reply('ADD', trid, lst_name, _ser(sess.state), ctc_head.email, name, group_id)

@_handlers
def _m_rem(sess, trid, lst_name, usr, group_id = None):
	lst = getattr(Lst, lst_name)
	if lst is Lst.RL:
		sess.close()
		return
	if lst is Lst.FL:
		#>>> REM 279 FL 00000000-0000-0000-0002-000000000001
		#>>> REM 247 FL 00000000-0000-0000-0002-000000000002 00000000-0000-0000-0001-000000000002
		if sess.state.dialect < 10:
			contact_uuid = sess.state.backend.util_get_uuid_from_email(usr)
		else:
			contact_uuid = usr
	else:
		#>>> REM 248 AL bob1@hotmail.com
		contact_uuid = sess.state.backend.util_get_uuid_from_email(usr)
	try:
		if group_id:
			sess.state.backend.me_group_contact_remove(sess, group_id, contact_uuid)
		else:
			sess.state.backend.me_contact_remove(sess, contact_uuid, lst)
	except Exception as ex:
		sess.send_reply(Err.GetCodeForException(ex), trid)
		return
	sess.send_reply('REM', trid, lst_name, _ser(sess.state), usr, group_id)

@_handlers
def _m_gtc(sess, trid, value):
	if sess.state.dialect >= 13:
		sess.send_reply(Err.CommandDisabled, trid)
		return
	# "Alert me when other people add me ..." Y/N
	#>>> GTC 152 N
	sess.state.backend.me_update(sess, { 'gtc': value })
	sess.send_reply('GTC', trid, _ser(sess.state), value)

@_handlers
def _m_blp(sess, trid, value):
	# Check "Only people on my Allow List ..." AL/BL
	#>>> BLP 143 BL
	sess.state.backend.me_update(sess, { 'blp': value })
	sess.send_reply('BLP', trid, _ser(sess.state), value)

@_handlers
def _m_chg(sess, trid, sts_name, capabilities = None, msnobj = None):
	#>>> CHG 120 BSY 1073791020 <msnobj .../>
	capabilities = capabilities or 0
	sess.state.backend.me_update(sess, {
		'substatus': getattr(Substatus, sts_name),
	})
	sess.state.front_specific['msn_capabilities'] = capabilities
	sess.state.front_specific['msn_msnobj'] = msnobj
	sess.send_reply('CHG', trid, sts_name, capabilities, encode_msnobj(msnobj))
	
	# Send ILNs
	state = sess.state
	if state.iln_sent:
		return
	state.iln_sent = True
	user = sess.user
	dialect = state.dialect
	for ctc in user.detail.contacts.values():
		for m in build_msnp_presence_notif(trid, ctc, dialect, sess.state.backend):
			sess.send_reply(*m)

@_handlers
def _m_rea(sess, trid, email, name):
	if sess.state.dialect >= 10:
		sess.send_reply(Err.CommandDisabled, trid)
		return
	if email == sess.user.email:
		sess.state.backend.me_update(sess, { 'name': name })
	sess.send_reply('REA', trid, _ser(sess.state), email, name)

@_handlers
def _m_snd(sess, trid, email):
	# Send email about how to use MSN. Ignore it for now.
	sess.send_reply('SND', trid, email)

@_handlers
def _m_prp(sess, trid, key, value, *rest):
	#>>> PRP 115 MFN ~~woot~~
	if key == 'MFN':
		sess.state.backend.me_update(sess, { 'name': value })
	# TODO: Save other settings?
	sess.send_reply('PRP', trid, key, value)

@_handlers
def _m_sbp(sess, trid, uuid, key, value):
	#>>> SBP 153 00000000-0000-0000-0002-000000000002 MFN Bob%201%20New
	# Can be ignored: core handles syncing contact names
	sess.send_reply('SBP', trid, uuid, key, value)

@_handlers
def _m_xfr(sess, trid, dest):
	if dest != 'SB':
		sess.send_reply(Err.InvalidParameter, trid)
		return
	dialect = sess.state.dialect
	token = sess.state.backend.sb_token_create(sess, extra_data = {
		'dialect': dialect, 'msn_capabilities': sess.state.front_specific.get('msn_capabilities') or 0,
	})
	extra = ()
	if dialect >= 13:
		extra = ('U', 'messenger.msn.com')
	if dialect >= 14:
		extra += (1,)
	sess.send_reply('XFR', trid, dest, 'm1.escargot.log1p.xyz:1864', 'CKI', token, *extra)

# These four commands appear to be useless:
@_handlers
def _m_adl(sess, trid, data):
	sess.send_reply('ADL', trid, 'OK')
@_handlers
def _m_rml(sess, trid, data):
	sess.send_reply('RML', trid, 'OK')
@_handlers
def _m_fqy(sess, trid, data):
	sess.send_reply('FQY', trid, b'')
@_handlers
def _m_uun(sess, trid, email, arg0, data):
	sess.send_reply('UUN', trid, 'OK')

# Utils

def _ser(state):
	if state.dialect >= 10:
		return None
	state.syn_ser += 1
	return state.syn_ser

def _encode_payload(tmpl, **kwargs):
	return tmpl.format(**kwargs).replace('\n', '\r\n').encode('utf-8')

PAYLOAD_MSG_0 = '''Routing: 1.0
To: 1:{email_address};epid={endpoint_ID}
From: 1:{email_address}

Reliability: 1.0

Notification: 1.0
NotifNum: 0
Uri: /user
NotifType: Partial
Content-Type: application/user+xml
Content-Length: 53

<user><s n="PF" ts="{timestamp}"></s></user>'''

PAYLOAD_MSG_1 = '''MIME-Version: 1.0
Content-Type: text/x-msmsgsprofile; charset=UTF-8
LoginTime: {time}
MemberIdHigh: {high}
MemberIdLow: {low}
lang_preference: 1033
preferredEmail:
country:
PostalCode:
Gender:
Kid: 0
Age:
BDayPre:
Birthday:
Wallet:
Flags: 536872513
sid: 507
MSPAuth: t={token}Y6+H31sTUOFkqjNTDYqAAFLr5Ote7BMrMnUIzpg860jh084QMgs5djRQLLQP0TVOFkKdWDwAJdEWcfsI9YL8otN9kSfhTaPHR1njHmG0H98O2NE/Ck6zrog3UJFmYlCnHidZk1g3AzUNVXmjZoyMSyVvoHLjQSzoGRpgHg3hHdi7zrFhcYKWD8XeNYdoz9wfA2YAAAgZIgF9kFvsy2AC0Fl/ezc/fSo6YgB9TwmXyoK0wm0F9nz5EfhHQLu2xxgsvMOiXUSFSpN1cZaNzEk/KGVa3Z33Mcu0qJqvXoLyv2VjQyI0VLH6YlW5E+GMwWcQurXB9hT/DnddM5Ggzk3nX8uMSV4kV+AgF1EWpiCdLViRI6DmwwYDtUJU6W6wQXsfyTm6CNMv0eE0wFXmZvoKaL24fggkp99dX+m1vgMQJ39JblVH9cmnnkBQcKkV8lnQJ003fd6iIFzGpgPBW5Z3T1Bp7uzSGMWnHmrEw8eOpKC5ny4x8uoViXDmA2UId23xYSoJ/GQrMjqB+NslqnuVsOBE1oWpNrmfSKhGU1X0kR4Eves56t5i5n3XU+7ne0MkcUzlrMi89n2j8aouf0zeuD7o+ngqvfRCsOqjaU71XWtuD4ogu2X7/Ajtwkxg/UJDFGAnCxFTTd4dqrrEpKyMK8eWBMaartFxwwrH39HMpx1T9JgknJ1hFWELzG8b302sKy64nCseOTGaZrdH63pjGkT7vzyIxVH/b+yJwDRmy/PlLz7fmUj6zpTBNmCtl1EGFOEFdtI2R04EprIkLXbtpoIPA7m0TPZURpnWufCSsDtD91ChxR8j/FnQ/gOOyKg/EJrTcHvM1e50PMRmoRZGlltBRRwBV+ArPO64On6zygr5zud5o/aADF1laBjkuYkjvUVsXwgnaIKbTLN2+sr/WjogxT1Yins79jPa1+3dDenxZtE/rHA/6qsdJmo5BJZqNYQUFrnpkU428LryMnBaNp2BW51JRsWXPAA7yCi0wDlHzEDxpqaOnhI4Ol87ra+VAg==
ClientIP: {ip}
ClientPort: {port}
ABCHMigrated: 1
MPOPEnabled: 1

'''

PAYLOAD_MSG_2 = '''MIME-Version: 1.0
Content-Type: text/x-msmsgsinitialmdatanotification; charset=UTF-8

Mail-Data: <MD><E><I>0</I><IU>0</IU><O>0</O><OU>0</OU></E><Q><QTM>409600</QTM><QNM>204800</QNM></Q></MD>
Inbox-URL: /cgi-bin/HoTMaiL
Folders-URL: /cgi-bin/folders
Post-URL: http://www.hotmail.com
'''

SHIELDS = '''<?xml version="1.0" encoding="utf-8" ?>
<config>
	<shield><cli maj="7" min="0" minbld="0" maxbld="9999" deny=" " /></shield>
	<block></block>
</config>'''.encode('utf-8')
TIMESTAMP = '2000-01-01T00:00:00.0-00:00'

def _uuid_to_high_low(u):
	import uuid
	u = uuid.UUID(u)
	high = u.time_low % (1<<32)
	low = u.node % (1<<32)
	return (high, low)
