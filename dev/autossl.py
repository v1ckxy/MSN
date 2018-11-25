from pathlib import Path
from functools import lru_cache

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes

CERT_DIR = Path('dev/cert')
CERT_ROOT_CA = 'DO_NOT_TRUST_DevEscargotRoot'

def create_context():
	perform_checks()
	
	import ssl
	ssl_context = ssl.create_default_context(purpose = ssl.Purpose.CLIENT_AUTH)
	
	cache = {}
	def servername_callback(socket, domain, ssl_context):
		if domain not in cache:
			ctxt = ssl.create_default_context(purpose = ssl.Purpose.CLIENT_AUTH)
			cert, key = autovivify_certificate(domain)
			ctxt.load_cert_chain(cert, keyfile = key)
			cache[domain] = ctxt
		socket.context = cache[domain]
	
	ssl_context.set_servername_callback(servername_callback)
	return ssl_context

def perform_checks():
	if autovivify_root_ca():
		return
	
	import sys
	print('*', file = sys.stderr)
	print('*', "New root CA '{}/{}' created.".format(CERT_DIR, CERT_ROOT_CA), file = sys.stderr)
	print('*', "Please remove the old one (if exists) and install this one.", file = sys.stderr)
	print('*', file = sys.stderr)
	sys.exit(-1)

def autovivify_certificate(domain):
	p_crt = CERT_DIR / '{}.crt'.format(domain)
	p_key = CERT_DIR / '{}.key'.format(domain)
	
	if not p_crt.exists():
		key = create_key()
		csr = create_csr(key, domain = domain)
		root_crt, root_key = autovivify_root_ca()
		crt = sign_csr(csr, root_crt.subject, root_key)
		save_key(key, p_key)
		save_cert(crt, p_crt)
	
	return p_crt, p_key

@lru_cache()
def autovivify_root_ca():
	CERT_DIR.mkdir(parents = True, exist_ok = True)
	
	p_crt = CERT_DIR / '{}.crt'.format(CERT_ROOT_CA)
	p_key = CERT_DIR / '{}.key'.format(CERT_ROOT_CA)
	
	if p_crt.exists() and p_key.exists():
		return load_cert(p_crt), load_key(p_key)
	
	key = create_key()
	csr = create_csr(key, common_name = CERT_ROOT_CA)
	crt = sign_csr(csr, csr.subject, key)
	
	save_key(key, p_key)
	save_cert(crt, p_crt)
	
	return None

def create_key():
	from cryptography.hazmat.primitives.asymmetric import rsa
	return rsa.generate_private_key(
		public_exponent = 65537, key_size = 2048,
		backend = default_backend()
	)

def create_csr(key, *, common_name = None, domain = None):
	from cryptography.x509.oid import NameOID
	
	if common_name is None:
		common_name = domain
	
	if common_name is None:
		raise ValueError("either `common_name` or `domain` required")
	
	csr = x509.CertificateSigningRequestBuilder()
	csr = csr.subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)]))
	if domain:
		csr = csr.add_extension(x509.SubjectAlternativeName([x509.DNSName(domain)]), critical = False)
	csr = csr.sign(key, hashes.SHA256(), default_backend())
	return csr

def sign_csr(csr, issuer, issuer_key, *, days = 30):
	from datetime import datetime, timedelta
	
	cert = x509.CertificateBuilder()
	cert = cert.subject_name(csr.subject)
	for ext in csr.extensions:
		cert = cert.add_extension(ext.value, critical = ext.critical)
	cert = cert.issuer_name(issuer)
	cert = cert.public_key(csr.public_key())
	cert = cert.serial_number(x509.random_serial_number())
	cert = cert.not_valid_before(datetime.utcnow())
	cert = cert.not_valid_after(datetime.utcnow() + timedelta(days = days))
	cert = cert.sign(issuer_key, hashes.SHA256(), default_backend())
	return cert

def load_key(path):
	backend = default_backend()
	with path.open('rb') as fh:
		return serialization.load_pem_private_key(fh.read(), None, backend)

def save_key(key, path):
	with path.open('wb') as fh:
		fh.write(key.private_bytes(
			encoding = serialization.Encoding.PEM,
			format = serialization.PrivateFormat.TraditionalOpenSSL,
			encryption_algorithm = serialization.NoEncryption(),
		))

def load_cert(path):
	backend = default_backend()
	with path.open('rb') as fh:
		return x509.load_pem_x509_certificate(fh.read(), backend)

def save_cert(crt, path):
	with path.open('wb') as fh:
		fh.write(crt.public_bytes(serialization.Encoding.PEM))
