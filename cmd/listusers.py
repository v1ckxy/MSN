import db
from datetime import datetime, timedelta

def main(arg = None):
	verbose = False
	online_since = None
	if arg is not None:
		if arg == 'verbose':
			verbose = True
		else:
			online_since = datetime.utcnow() - timedelta(minutes = int(arg))
	else:
		online_since = datetime.utcnow() - timedelta(minutes = 60)
	
	total = 0
	total_online = 0
	with db.Session() as sess:
		for u in sess.query(db.User).all():
			total += 1
			if verbose:
				print(u.email)
			if online_since is not None and u.date_login is not None:
				total_online += (1 if u.date_login >= online_since else 0)
	
	print("Total:", total)
	if online_since is not None:
		print("Online:", total_online)

if __name__ == '__main__':
	import sys
	main(*sys.argv[1:])
