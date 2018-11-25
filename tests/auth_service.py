from util.auth import AuthService

def test_can_use_existing():
	t = MockTime()
	a = AuthService(time = t)
	token = a.create_token('xyz', 'data', lifetime = 10)
	t.tick(5)
	assert a.pop_token('xyz', token) == 'data'
	assert a.pop_token('xyz', token) is None

def test_cant_use_expired():
	t = MockTime()
	a = AuthService(time = t)
	token = a.create_token('xyz', 'data', lifetime = 10)
	t.tick(11)
	assert a.pop_token('xyz', token) is None

def test_cant_use_wrong_purpose():
	t = MockTime()
	a = AuthService(time = t)
	token = a.create_token('xyz', 'data', lifetime = 10)
	assert a.pop_token('zyx', token) is None
	assert a.pop_token('xyz', token) is None

def test_multiple_in_order():
	t = MockTime()
	a = AuthService(time = t)
	token1 = a.create_token('xyz', 'data1', lifetime = 10)
	t.tick(5)
	token2 = a.create_token('abc', 'data2', lifetime = 15)
	t.tick(3)
	assert a.pop_token('xyz', token1) == 'data1'
	t.tick(10)
	assert a.pop_token('abc', token2) == 'data2'

def test_multiple_out_of_order():
	t = MockTime()
	a = AuthService(time = t)
	token1 = a.create_token('xyz', 'data1', lifetime = 10)
	t.tick(5)
	token2 = a.create_token('abc', 'data2', lifetime = 15)
	t.tick(3)
	assert a.pop_token('abc', token2) == 'data2'
	t.tick(1)
	assert a.pop_token('xyz', token1) == 'data1'

class MockTime:
	def __init__(self):
		self.t = 0
	
	def tick(self, dt = 1):
		self.t += dt
	
	def __call__(self):
		return self.t
