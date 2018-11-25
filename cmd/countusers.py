import db

def main():
	query = '''
		SELECT DATE(u.date_created), COUNT(*), SUM(CASE WHEN u.date_login IS NULL THEN 1 ELSE 0 END)
		FROM t_user u
		GROUP BY DATE(u.date_created)
		ORDER BY DATE(u.date_created)
	'''
	with db.Session() as sess:
		for date, count, zombies in sess.execute(query):
			zombiebars = int(10 * (zombies / count + 0.04))
			print('{:10} {:4} {}'.format(str(date), count, ('*' * zombiebars + '.' * (10 - zombiebars))))

if __name__ == '__main__':
	main()
