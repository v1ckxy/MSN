import pytest

def main(prog, *args):
	opts = []
	tests = []
	for a in args:
		# Hack to work around msys's path conversion
		a = a.replace(';', '::')
		if a.startswith('-'):
			opts.append(a)
		else:
			tests.append(a)
	if not tests:
		tests.append(prog)
	pytest.main(opts + tests)

if __name__ == '__main__':
	import sys
	sys.exit(main(*sys.argv))
