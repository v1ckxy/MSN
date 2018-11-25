import argparse
from db import Session, User
from util.misc import gen_uuid
from util import hash

def main():
	parser = argparse.ArgumentParser(description = "Create user/change password.")
	parser.add_argument('email', help = "email of new/existing user")
	parser.add_argument('password')
	parser.add_argument(
		'--old', dest = 'old_msn_support', action = 'store_const',
		const = True, default = False, help = "old MSN support"
	)
	args = parser.parse_args()
	
	email = args.email
	pw = args.password
	
	with Session() as sess:
		user = sess.query(User).filter(User.email == email).one_or_none()
		if user is None:
			print("Creating new user...")
			user = User(
				uuid = gen_uuid(), email = email, verified = False,
				name = email, message = '',
				settings = {}, groups = {}, contacts = {},
			)
		else:
			print("User exists, changing password...")
		_set_passwords(user, pw, args.old_msn_support)
		sess.add(user)
	
	print("Done.")

def _set_passwords(user, pw, support_old):
	user.password = hash.hasher.encode(pw)
	user.password_md5 = (hash.hasher_md5.encode(pw) if support_old else '')

if __name__ == '__main__':
	main()
