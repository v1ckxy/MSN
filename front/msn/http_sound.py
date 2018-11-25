# TODO: This should be in its own frontend, but putting it in `front/msn`
# until it's possible for each frontend to have its own http stuff.

"""
	Messenger Plus sound server implementation
	
	GET /esnd/snd/builtin?code={code} -> builtin
	GET /esnd/snd/check?hash={hash} -> check
	GET /esnd/snd/get?hash={hash} -> get
	GET /esnd/snd/random?[catId={category}]&[lngId={language}] -> random
	POST /esnd/snd/put[?uf=1] -> put
"""

from aiohttp.web import Response
from os import path, makedirs
from collections import namedtuple
from random import randrange

from db import Sound, Session

PATH_BUILTINS = path.join('storage', 'sound', 'builtins')
PATH_USERS = path.join('storage', 'sound', 'users')

Metadata = namedtuple('Metadata', ['title', 'hash', 'category', 'language', 'is_public'])

def builtin(request):
	"""
		Get builtin sound file
		
		(GET) /esnd/snd/builtin?code={code}
		
		:type request: aiohttp.web.Request
		:return file content or 0 if file is not found
		:rtype: aiohttp.web.Response
	"""
	file_name = request.rel_url.query['code'] + '.mp3'
	file_path = path.join(PATH_BUILTINS, file_name)
	
	try:
		with open(file_path, 'rb') as file:
			return Response(status = 200, content_type = 'audio/mpeg', body = file.read())
	except FileNotFoundError:
		return Response(status = 200, body = '0')

def check(request):
	"""
		Check if sound file is available
		
		GET /esnd/snd/check?hash={hash}
		
		:type request: aiohttp.web.Request
		:return 1 if file exists 0 otherwise
		:rtype: aiohttp.web.Response
	"""
	file_hash = request.rel_url.query['hash']
	
	result = int(path.exists(_get_file_path(file_hash)))
	
	return Response(status = 200, body = str(result))

async def put(request):
	"""
		Upload new sound file.
		Overwrite existing file if uf=1
		
		POST /esnd/snd/put?[uf=1]
		
		:type request: aiohttp.web.Request
		:return 1 for success 0 for failure
		:rtype: aiohttp.web.Response
	"""
	data = await request.post()
	
	with data['file'].file as f:
		f.seek(-128, 2) # metadata offset
		metadata = _parse_metadata(f.read())
		
		file_path = _get_file_path(metadata.hash)
		
		try:
			output = open(file_path, 'xb')
		except FileNotFoundError:
			makedirs(path.dirname(file_path))
			output = open(file_path, 'xb')
		except FileExistsError:
			if request.rel_url.query.get('uf') == 1:
				output = open(file_path, 'wb')
			else:
				return Response(status = 200, body = '0')
		
		f.seek(0)
		
		with output as o:
			o.write(f.read())
	
	assert path.exists(file_path)
	
	with Session() as session:
		session.merge(Sound(**metadata._asdict()))
	
	return Response(status = 200, body = '1')

def get(request):
	"""
		Get sound file
		
		GET /esnd/snd/get?hash={hash}
		
		:type request: aiohttp.web.Request
		:return file content or 0 if file is not found
		:rtype: aiohttp.web.Response
	"""
	file_hash = request.rel_url.query['hash']
	
	try:
		with open(_get_file_path(file_hash), 'rb') as f:
			return Response(status = 200, content_type = 'audio/mpeg', body = f.read())
	except FileNotFoundError:
		return Response(status = 200, body = '0')

def random(request):
	"""
		Get random sound from library
		
		GET /esnd/snd/random?[catId={category}]&[lngId={language}]
		
		:type request: aiohttp.web.Request
		:return: file content or 0 if file is not found
		:rtype: aiohttp.web.Response
	"""
	category = request.rel_url.query.get('catId')
	language = request.rel_url.query.get('lngId')
	
	with Session() as session:
		query = session.query(Sound).filter(Sound.is_public == True)
		
		if category:
			query = query.filter(Sound.category == category)
		
		if language:
			query = query.filter(Sound.language == language)
		
		try:
			offset = randrange(0, query.count())
		except ValueError:
			return Response(status = 200, body = '0')
		
		sound = query.offset(offset).limit(1).one()
		
		file_path = _get_file_path(sound.hash)
		
		assert path.exists(file_path)
		
		with open(file_path, 'rb') as f:
			return Response(status = 200, content_type = 'audio/mpeg', body = f.read())

def _get_file_path(file_hash):
	"""
		Get file path by hash.
		Uses first 3 symbols for subdirectories e.g. 12345 -> 1/2/3/12345.mp3
		
		:type file_hash: string
		:rtype: string
	"""
	return path.join(PATH_USERS, *file_hash[:3], file_hash + '.mp3')

def _parse_metadata(raw_data):
	"""
		Parse raw metadata
		
		00:32   - TAG{title}0x00 ... 0x00
		93      - {category}
		95      - {is_public} - 0x02 = true
		109:120 - {hash}
		127     - {language}
		
		:param raw_data: 128 bytes
		:rtype: Metadata
	"""
	assert len(raw_data) == 128
	
	return Metadata(
		title = raw_data[3:33].decode('utf-8').strip('\0'),
		category = raw_data[93],
		is_public = (raw_data[95] in (0, 2)),
		hash = raw_data[109:121].decode('utf-8'),
		language = raw_data[127],
	)
