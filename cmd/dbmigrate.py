import db

with db.Session() as sess:
	sess.execute('ALTER TABLE t_user ADD COLUMN password_md5 TEXT DEFAULT \'\'')
