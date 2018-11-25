from util.auth import AuthService
from util.msnp import Err
from ctrl_nb import NB, NBConn
from ctrl_sb import SB, SBConn
from models import Service

from tests.mock import UserService, MSNPWriter, ANY

def test_msnp_commands():
	user_service = UserService()
	auth_service = AuthService()
	
	nb = NB(user_service, auth_service, [Service('0.0.0.0', 0)])
	sb = SB(user_service, auth_service)
	
	# User 1 login
	nc1 = NBConn(nb, MSNPWriter())
	user1 = _login_msnp(nc1, 'test1@example.com')
	nc1._l_adc(1, 'FL', 'N=test2@example.com', 'F=Test2')
	nc1.writer.pop_message('ADC', 1, 'FL', 'N=test2@example.com', ANY)
	
	# User 2 login
	nc2 = NBConn(nb, MSNPWriter())
	user2 = _login_msnp(nc2, 'test2@example.com')
	nc1.writer.pop_message('NLN', 'NLN', 'test2@example.com', ANY, ANY, ANY)
	nc1.writer.pop_message('UBX', 'test2@example.com', ANY)
	nc2.writer.pop_message('ILN', 5, 'NLN', 'test1@example.com', ANY, ANY, ANY)
	nc2.writer.pop_message('UBX', 'test1@example.com', ANY)
	
	# User 1 starts convo
	nc1._l_xfr(1, 'SB')
	msg = nc1.writer.pop_message('XFR', 1, 'SB', ANY, 'CKI', ANY)
	token = msg[-1]
	
	sc1 = SBConn(sb, nb, MSNPWriter())
	sc1._a_usr(0, 'test1@example.com', token)
	sc1.writer.pop_message('USR', 0, 'OK', 'test1@example.com', ANY)
	assert sc1.user.uuid == user1.uuid
	
	sc1._l_cal(1, 'doesnotexist')
	sc1.writer.pop_message(Err.InternalServerError, 1)
	
	sc1._l_cal(2, 'test2@example.com')
	sc1.writer.pop_message('CAL', 2, 'RINGING', ANY)
	
	msg = nc2.writer.pop_message('RNG', ANY, ANY, 'CKI', ANY, user1.email, ANY)
	sbsess_id = msg[1]
	token = msg[4]
	
	# User 2 joins convo
	sc2 = SBConn(sb, nb, MSNPWriter())
	sc2._a_ans(0, 'test2@example.com', token, sbsess_id)
	sc2.writer.pop_message('IRO', 0, 1, 1, 'test1@example.com', ANY)
	sc2.writer.pop_message('ANS', 0, 'OK')
	sc1.writer.pop_message('JOI', 'test2@example.com', ANY)
	
	# User 1 sends message
	sc1._l_msg(3, 'A', b"my message")
	sc1.writer.pop_message('ACK', 3)
	sc2.writer.pop_message('MSG', 'test1@example.com', ANY, b"my message")

def _login_msnp(nc, email):
	w = nc.writer
	nc._a_ver(0, 'MSNP12')
	w.pop_message('VER', 0, 'MSNP12')
	nc._a_cvr(1, 'a0', 'a1', 'a2', 'a3', 'a4', 'a5')
	w.pop_message('CVR', 1, 'a5', 'a5', 'a5', ANY, ANY)
	nc._a_usr(3, 'TWN', 'I', email)
	w.pop_message('USR', 3, 'TWN', 'S', ANY)
	
	uuid = nc.nb._user_service.get_uuid(email)
	token = nc.nb._auth_service.create_token('nb/login', uuid)
	nc._a_usr(4, 'TWN', 'S', token)
	w.pop_message('USR', 4, 'OK', email, '1', '0')
	
	nc._l_chg(5, 'NLN', 0)
	w.pop_message('CHG', 5, 'NLN', 0)
	
	return nc.user
