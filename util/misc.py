import asyncio
import functools
from uuid import uuid4

EMPTY_SET = frozenset()

def gen_uuid():
	return str(uuid4())

def first_in_iterable(iterable):
	for x in iterable: return x
	return None

class Runner:
	def __init__(self, host, port, *, ssl = None):
		self.host = host
		self.port = port
		self.ssl_context = ssl
	
	def setup(self, loop):
		raise NotImplementedError('Runner.setup')
	
	def teardown(self, loop):
		pass

class ProtocolRunner(Runner):
	def __init__(self, host, port, protocol, *, args = None, ssl = None):
		super().__init__(host, port, ssl = ssl)
		if args:
			protocol = functools.partial(protocol, *args)
		self._protocol = protocol
	
	def setup(self, loop):
		return self._protocol

class AIOHTTPRunner(Runner):
	def __init__(self, host, port, app, *, ssl = None):
		super().__init__(host, port, ssl = ssl)
		self.app = app
		self.handler = None
	
	def setup(self, loop):
		from aiohttp.log import access_logger
		self.handler = self.app.make_handler(loop = loop, access_log = access_logger)
		loop.run_until_complete(self.app.startup())
		return self.handler
	
	def teardown(self, loop):
		loop.run_until_complete(self.app.shutdown())
		loop.run_until_complete(self.handler.shutdown(60))
		loop.run_until_complete(self.app.cleanup())

class Logger:
	def __init__(self, prefix, obj):
		import settings
		self.prefix = '{}/{:04x}'.format(prefix, hash(obj) % 0xFFFF)
		self._log = settings.DEBUG and settings.DEBUG_MSNP
	
	def info(self, *args):
		if self._log:
			print(self.prefix, *args)
	
	def log_connect(self):
		self.info("con")
	
	def log_disconnect(self):
		self.info("dis")

def run_loop(loop, runners):
	for runner in runners:
		print("Serving on {}:{}".format(runner.host, runner.port))
	
	task = loop.create_task(_windows_ctrl_c_workaround())
	
	servers = loop.run_until_complete(asyncio.gather(*(
		loop.create_server(runner.setup(loop), runner.host, runner.port, ssl = runner.ssl_context)
		for runner in runners
	)))
	
	try:
		loop.run_forever()
	except KeyboardInterrupt:
		# To prevent "Task exception was never retrieved"
		if task.done():
			task.exception()
		raise
	finally:
		for server in servers:
			server.close()
		loop.run_until_complete(asyncio.gather(*(
			server.wait_closed() for server in servers
		)))
		for runner in runners:
			runner.teardown(loop)
		loop.close()

async def _windows_ctrl_c_workaround():
	import os
	if os.name != 'nt': return
	
	# https://bugs.python.org/issue23057
	while True:
		await asyncio.sleep(0.1)

def create_jinja_env(tmpl_dir, globals = None):
	import jinja2
	jinja_env = jinja2.Environment(
		loader = jinja2.FileSystemLoader(tmpl_dir),
		autoescape = jinja2.select_autoescape(default = True),
	)
	if globals:
		jinja_env.globals.update(globals)
	return jinja_env
