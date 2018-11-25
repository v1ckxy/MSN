def main(*, devmode = False):
	import asyncio
	from core.backend import Backend
	import front.msn
	import front.ymsg
	import front.bot
	import settings
	
	if devmode:
		http_port = 80
	else:
		http_port = 8081
	
	loop = asyncio.get_event_loop()
	backend = Backend(loop)
	if settings.ENABLE_FRONT_MSN:
		front.msn.register(loop, backend, http_port = http_port, devmode = devmode)
	if settings.ENABLE_FRONT_YMSG:
		front.ymsg.register(loop, backend)
	if settings.ENABLE_FRONT_BOT:
		front.bot.register(loop, backend)
	backend.run_forever()

if __name__ == '__main__':
	main()
