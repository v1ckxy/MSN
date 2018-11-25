from util.auth import AuthService
from util.msnp import Err
from ctrl_nb import NB, NBConn
from models import Service, Lst, Substatus

from tests.mock import UserService, MSNPWriter, ANY

def test_msnp_commands():
	user_service = UserService()
	auth_service = AuthService()
	nb = NB(user_service, auth_service, [Service('0.0.0.0', 0)])
	
	email = 'test1@example.com'
	uuid = user_service.get_uuid(email)
	
	w1 = MSNPWriter()
	nc1 = NBConn(nb, w1)
	
	# Login
	
	nc1._a_ver(0, 'MSNP12')
	w1.pop_message('VER', 0, 'MSNP12')
	nc1._a_cvr(1, 'a0', 'a1', 'a2', 'a3', 'a4', 'a5')
	w1.pop_message('CVR', 1, 'a5', 'a5', 'a5', ANY, ANY)
	nc1._a_usr(3, 'TWN', 'I', email)
	w1.pop_message('USR', 3, 'TWN', 'S', ANY)
	
	token = auth_service.create_token('nb/login', uuid)
	nc1._a_usr(4, 'TWN', 'S', token)
	w1.pop_message('USR', 4, 'OK', email, '1', '0')
	
	user = nc1.user
	
	nc1._l_syn(5)
	w1.pop_message('SYN', 5, ANY, ANY, ANY, ANY)
	w1.pop_message('GTC', 'A')
	w1.pop_message('BLP', 'AL')
	w1.pop_message('PRP', 'MFN', ANY)
	w1.assert_empty()
	
	# Group/Contact Management
	
	nc1._l_adg(8, 'x' * 100, 'ignored')
	w1.pop_message(Err.GroupNameTooLong, 8)
	nc1._l_adg(9, "New Group")
	msg = w1.pop_message('ADG', 9, "New Group", ANY, ANY)
	assert user.detail.groups[msg[3]].name == msg[2]
	nc1._l_rmg(10, "New%20Group")
	w1.pop_message('RMG', 10, 1, msg[3])
	assert msg[3] not in user.detail.groups
	
	nc1._l_rmg(11, '0')
	w1.pop_message(Err.GroupZeroUnremovable, 11)
	nc1._l_rmg(12, 'blahblahblah')
	w1.pop_message(Err.GroupInvalid, 12)
	
	nc1._l_adg(13, "Group Name")
	msg = w1.pop_message('ADG', 13, "Group Name", ANY, ANY)
	group_uuid = msg[3]
	assert user.detail.groups[group_uuid].name == msg[2]
	nc1._l_reg(14, group_uuid, "New Group Name", 'ignored')
	w1.pop_message('REG', 14, 1, "New Group Name", group_uuid, ANY)
	assert user.detail.groups[group_uuid].name == "New Group Name"
	
	nc1._l_adc(15, 'FL', 'N=doesnotexist')
	w1.pop_message(Err.InvalidPrincipal, 15)
	nc1._l_adc(16, 'FL', 'N=test2@example.com', 'F=Test2')
	msg = w1.pop_message('ADC', 16, 'FL', 'N=test2@example.com', ANY)
	uuid = msg[-1][2:]
	assert user.detail.contacts[uuid].head.email == 'test2@example.com'
	assert user.detail.contacts[uuid].lists == Lst.FL
	assert not user.detail.contacts[uuid].groups
	nc1._l_adc(17, 'FL', 'C={}'.format(uuid), group_uuid)
	w1.pop_message('ADC', 17, 'FL', 'C={}'.format(uuid), group_uuid)
	assert user.detail.contacts[uuid].groups == { group_uuid }
	
	assert nb._unsynced_db, "has unsynced data"
	nb._sync_db_impl()
	assert not nb._unsynced_db, "db was synced"
	
	nc1._l_adc(18, 'BL', 'N=test2@example.com')
	w1.pop_message('ADC', 18, 'BL', 'N=test2@example.com')
	assert user.detail.contacts[uuid].lists == Lst.FL | Lst.BL
	nc1._l_rem(19, 'BL', 'test2@example.com')
	w1.pop_message('REM', 19, 'BL', 'test2@example.com')
	assert user.detail.contacts[uuid].lists == Lst.FL
	nc1._l_rem(20, 'FL', uuid, 'notvalidgroupid')
	w1.pop_message(Err.GroupInvalid, 20)
	nc1._l_rem(21, 'FL', uuid, group_uuid)
	w1.pop_message('REM', 21, 'FL', uuid, group_uuid)
	assert not user.detail.contacts[uuid].groups
	nc1._l_rem(22, 'FL', 'notvaliduserid')
	w1.pop_message(Err.PrincipalNotOnList, 22)
	nc1._l_rem(23, 'FL', uuid)
	w1.pop_message('REM', 23, 'FL', uuid)
	assert uuid not in user.detail.contacts
	
	# Misc
	
	nc1._l_png()
	w1.pop_message('QNG', ANY)
	
	nc1._l_url(6, 'blah')
	w1.pop_message('URL', 6, ANY, ANY, ANY)
	
	nc1._l_uux(7, {
		'PSM': "my message",
		'CurrentMedia': "song name",
	})
	w1.pop_message('UUX', 7, ANY)
	assert user.status.message == "my message"
	assert user.status.media == "song name"
	
	nc1._l_gtc(24, 'Y')
	w1.pop_message('GTC', 24, 'Y')
	
	nc1._l_blp(25, 'AL')
	w1.pop_message('BLP', 25, 'AL')
	
	nc1._l_chg(26, 'NLN', 0)
	w1.pop_message('CHG', 26, 'NLN', 0)
	assert user.status.substatus == Substatus.NLN
	
	nc1._l_rea(27, 'test1@example.com', "My Name")
	w1.pop_message(Err.CommandDisabled, 27)
	
	nc1._l_snd(28, 'email@blah.com')
	w1.pop_message('SND', 28, 'email@blah.com')
	
	nc1._l_prp(29, 'MFN', "My Name")
	w1.pop_message('PRP', 29, 'MFN', "My Name")
	assert user.status.name == "My Name"
	
	nc1._l_sbp(30, uuid, 'MFN', "Buddy Name")
	w1.pop_message('SBP', 30, uuid, 'MFN', "Buddy Name")
	
	nc1._l_xfr(31, 'SB')
	w1.pop_message('XFR', 31, 'SB', ANY, 'CKI', ANY)
