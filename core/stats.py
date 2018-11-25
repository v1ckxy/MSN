from datetime import datetime
from contextlib import contextmanager
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from HLL import HyperLogLog

from core.client import Client
from util.json_type import JSONType
import settings

class Stats:
	def __init__(self):
		self.logged_in = 0
		# Dict[DBClient.id, Dict[stat, stat value]]?
		self.by_client = {}
		# Dict[Client, DBClient.id]?
		self._client_id_cache = None
		
		hour = _current_hour()
		with Session() as sess:
			current = sess.query(CurrentStats).filter(CurrentStats.key == 'current_hour').one_or_none()
			if not current:
				return
			if current.value['hour'] != hour:
				return
			self.by_client = {
				int(client_id): _stats_from_json(stats)
				for client_id, stats in current.value['by_client'].items()
			}
	
	def on_login(self):
		self.logged_in += 1
	
	def on_logout(self):
		self.logged_in -= 1
	
	def on_user_active(self, user, client):
		self._collect('users_active', user, client)
	
	def on_message_sent(self, user, client):
		self._collect('messages_sent', user, client)
	
	def on_message_received(self, user, client):
		self._collect('messages_received', user, client)
	
	def _collect(self, stat, user, client):
		assert user is not None
		assert client is not None
		if self.by_client is None:
			self.by_client = {}
		bc = self.by_client
		client_id = self._get_client_id(client)
		if client_id not in bc:
			bc[client_id] = {}
		bhc = bc[client_id]
		if stat == 'users_active':
			if stat not in bhc:
				bhc[stat] = HyperLogLog(12)
			bhc[stat].add(user.email)
		else:
			if stat not in bhc:
				bhc[stat] = 0
			bhc[stat] += 1
	
	def flush(self):
		hour = _current_hour()
		now = datetime.utcnow()
		
		with Session() as sess:
			current = sess.query(CurrentStats).filter(CurrentStats.key == 'logged_in').one_or_none()
			if not current:
				current = CurrentStats(key = 'logged_in')
			current.date_updated = now
			current.value = self.logged_in
			sess.add(current)
			sess.flush()
			
			current = sess.query(CurrentStats).filter(CurrentStats.key == 'current_hour').one_or_none()
			if not current:
				current = CurrentStats(key = 'current_hour', value = { 'hour': hour })
			
			cs_hour = current.value['hour']
			current.date_updated = now
			current.value = self._flush_to_hourly(sess, hour)
			sess.add(current)
			
			if cs_hour != hour:
				self.by_client = {}
	
	def _flush_to_hourly(self, sess, hour):
		for client_id, stats in self.by_client.items():
			hcs = sess.query(HourlyClientStats).filter(HourlyClientStats.hour == hour, HourlyClientStats.client_id == client_id).one_or_none()
			if hcs is None:
				hcs = HourlyClientStats(hour = hour, client_id = client_id)
			hcs.messages_sent = stats.get('messages_sent') or 0
			hcs.messages_received = stats.get('messages_received') or 0
			if 'users_active' in stats:
				hcs.users_active = stats['users_active'].cardinality()
			else:
				hcs.users_active = 0
			sess.add(hcs)
		return {
			'hour': hour,
			'by_client': {
				client_id: _stats_to_json(stats)
				for client_id, stats in self.by_client.items()
			}
		}
	
	def _get_client_id(self, client):
		if self._client_id_cache is None:
			with Session() as sess:
				self._client_id_cache = {
					Client.FromJSON(row.data): row.id
					for row in sess.query(DBClient).all()
				}
		if client not in self._client_id_cache:
			with Session() as sess:
				dbobj = DBClient(data = Client.ToJSON(client))
				sess.add(dbobj)
				sess.flush()
				self._client_id_cache[client] = dbobj.id
		return self._client_id_cache[client]

def _stats_to_json(stats):
	json = {}
	if 'messages_sent' in stats:
		json['messages_sent'] = stats['messages_sent']
	if 'messages_received' in stats:
		json['messages_received'] = stats['messages_received']
	if 'users_active' in stats:
		json['users_active'] = list(stats['users_active'].registers())
	return json

def _stats_from_json(json):
	stats = {}
	if 'messages_sent' in json:
		stats['messages_sent'] = json['messages_sent']
	if 'messages_received' in json:
		stats['messages_received'] = json['messages_received']
	if 'users_active' in json:
		hll = HyperLogLog(12)
		hll.set_registers(bytearray(json['users_active']))
		stats['users_active'] = hll
	return stats

def _current_hour():
	now = datetime.utcnow()
	ts = now.timestamp()
	return ts // 3600

class Base(declarative_base()):
	__abstract__ = True

class DBClient(Base):
	__tablename__ = 't_client'
	
	id = sa.Column(sa.Integer, nullable = False, primary_key = True)
	data = sa.Column(JSONType, nullable = False)

class HourlyClientStats(Base):
	__tablename__ = 't_stats_hour_client'
	
	hour = sa.Column(sa.Integer, nullable = False, primary_key = True)
	client_id = sa.Column(sa.Integer, nullable = False, primary_key = True)
	users_active = sa.Column(sa.Integer, nullable = False, server_default = '0')
	messages_sent = sa.Column(sa.Integer, nullable = False, server_default = '0')
	messages_received = sa.Column(sa.Integer, nullable = False, server_default = '0')

class CurrentStats(Base):
	__tablename__ = 't_stats_current'
	
	key = sa.Column(sa.String, nullable = False, primary_key = True)
	date_updated = sa.Column(sa.DateTime, nullable = False)
	value = sa.Column(JSONType, nullable = False)

engine = sa.create_engine(settings.STATS_DB)
session_factory = sessionmaker(bind = engine)

@contextmanager
def Session():
	if Session._depth > 0:
		yield Session._global
		return
	session = session_factory()
	Session._global = session
	Session._depth += 1
	try:
		yield session
		session.commit()
	except:
		session.rollback()
		raise
	finally:
		session.close()
		Session._global = None
		Session._depth -= 1
Session._global = None
Session._depth = 0
