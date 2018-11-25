# Developer Guide

## Setup 

- you will need python 3.6+
- ([MSYS2](https://github.com/valtron/llvm-stuff/wiki/Set-up-Windows-dev-environment-with-MSYS2) env recommended for Windows users)
- `cd` into `msn-server`
- install dependencies: `python -m pip install -r requirements.txt`
- create `settings_local.py` and set debug options:
	```
	DEBUG = True
	DEBUG_MSNP = True
	DEBUG_HTTP_REQUEST = True
	```
- run `python cmd/dbcreate.py`; if you get `ModuleNotFoundError: No module named '...'`, add `export PYTHONPATH=".;$PYTHONPATH"` in your `.bashrc`
- run `python cmd/dummydata.py` (creates a few dummy accounts, check the file to see what they are/their passwords)
- to create users, run `python cmd/user.py -h` for instructions
- for MSN <= 7.5, use a **patched** install, and in your `HOSTS` add `127.0.0.1 m1.escargot.log1p.xyz`
- for WLM, use a 8.1.0178 **clean** install, replace [msidcrl40.dll](https://storage.googleapis.com/escargot-storage-1/public/msidcrl.dll), and in your `HOSTS` add:
	```
	127.0.0.1 messenger.hotmail.com
	127.0.0.1 gateway.messenger.hotmail.com
	127.0.0.1 byrdr.omega.contacts.msn.com
	127.0.0.1 config.messenger.msn.com
	127.0.0.1 tkrdr.storage.msn.com
	127.0.0.1 ows.messenger.msn.com
	127.0.0.1 rsi.hotmail.com
	```
- run `python dev`

The **first time** you run `python dev`, a root certificate `DO_NOT_TRUST_DevEscargotRoot.crt` is created in `dev/cert`,
it tells you to install it, and exits. To install (on Windows):

- double click the certificate
- click "Install Certificate..."
- select "Current User" for "Store Location"
- select "Place all certificates in the following store", click "Browse...", and select "Trusted Root Certification Authorities"
- click "Next" and then "Finish"

Now run `python dev` again, and it should start all the services: NB, SB, http, https.
When you visit a domain that's redirected to `127.0.0.1` using https, the dev server automatically creates a certificate.

When you run MSN now, assuming it's patched, all traffic will be going to your local dev server.
However, MSN <= 6.2 still cache the IP of the server in the registry, so you might need to clear that out
if you're testing those versions. It's located:

- MSN 1.0 - 4.7: `HKEY_CURRENT_USER\SOFTWARE\Microsoft\MessengerService\Server`
- MSN 5.0 - 6.2: `HKEY_CURRENT_USER\SOFTWARE\Microsoft\MSNMessenger\Server`

All generated certificates expire after 30 days for "security" purposes (i.e. I didn't
set it to a long period of time so as to not open anyone up to... vulnerabilities...
if they forget to uninstall the root certificate).

## Testing

Run all tests:

```
python tests
```

Run a specific test:

```
python tests tests/auth_service.py::test_multiple_in_order
```
