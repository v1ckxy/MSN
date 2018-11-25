from util.hash import hasher
from ctrl_nb import Lst
from db import Base, Session, User, engine
from uuid import uuid4

Base.metadata.create_all(engine)

with Session() as sess:
	sess.query(User).delete()

	uuid = [str(uuid4()), str(uuid4()), str(uuid4())]
	
	sess.add(User(
		uuid = uuid[0],
		email = 'foo@hotmail.com',
		verified = True,
		name = "~~Foo~~",
		message = "Ahoy!",
		password = hasher.encode('foopass'),
		password_md5 = "cbbb9b3bc98eb2d52be3c223b7dadf35",
		settings = {},
		groups = [
			{ 'id': '1', "name": "Space Group" },
			{ 'id': '2', "name": "GroupA" },
			{ 'id': '3', "name": "GroupZ" },
		],
		contacts = [
			{
				'uuid': uuid[1],
				'name': "Bob Ross 1",
				'message': "The Joy of Painting Rules!!!1",
				'lists': (Lst.FL | Lst.AL),
				'groups': ['2', '3'],
			},
			{
				'uuid': uuid[2],
				'name': "Bob Ross 2",
				'message': "because everybody needs a friend",
				'lists': (Lst.RL),
				'groups': [],
			},
		],
	))
	sess.add(User(
		uuid = uuid[1],
		email = 'bob1@hotmail.com',
		verified = True,
		name = "Bob Ross 1",
		message = "The Joy of Painting Rules!!!1",
		password = hasher.encode('foopass'),
		password_md5 = "cbbb9b3bc98eb2d52be3c223b7dadf35",
		settings = {},
		groups = [],
		contacts = [],
	))
	sess.add(User(
		uuid = uuid[2],
		email = 'bob2@hotmail.com',
		verified = True,
		name = "Bob Ross 2",
		message = "because everybody needs a friend",
		password = hasher.encode('foopass'),
		password_md5 = "cbbb9b3bc98eb2d52be3c223b7dadf35",
		settings = {},
		groups = [],
		contacts = [
			{
				'uuid': uuid[0],
				'name': "Foo",
				'message': "Ahoy!",
				'lists': (Lst.FL | Lst.AL),
				'groups': [],
			},
		],
	))
