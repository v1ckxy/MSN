DB = 'sqlite:///msn.sqlite'
STATS_DB = 'sqlite:///stats.sqlite'
LOGIN_HOST = 'm1.escargot.log1p.xyz'
STORAGE_HOST = LOGIN_HOST
DEBUG = False
DEBUG_MSNP = False
DEBUG_HTTP_REQUEST = False
DEBUG_HTTP_REQUEST_FULL = False

ENABLE_FRONT_MSN = True
ENABLE_FRONT_YMSG = False
ENABLE_FRONT_BOT = False

try:
	from settings_local import *
except ImportError as ex:
	raise Exception("Please create settings_local.py") from ex
