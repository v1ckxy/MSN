# NOTICE:
# 
# This script has been modified to work on Python 3 (e.g. hashlib, workarounds 
# for ord() and byte strings). All credit is given where credit is due. :)

#########################################################
# md5crypt.py
#
# 0423.2000 by michal wallace http://www.sabren.com/
# based on perl's Crypt::PasswdMD5 by Luis Munoz (lem@cantv.net)
# based on /usr/src/libcrypt/crypt.c from FreeBSD 2.2.5-RELEASE
#
# MANY THANKS TO
#
#  Carey Evans - http://home.clear.net.nz/pages/c.evans/
#  Dennis Marti - http://users.starpower.net/marti1/
#
#  For the patches that got this thing working!
#
#########################################################
"""md5crypt.py - Provides interoperable MD5-based crypt() function

SYNOPSIS

	import md5crypt.py

	cryptedpassword = md5crypt.md5crypt(password, salt);

DESCRIPTION

unix_md5_crypt() provides a crypt()-compatible interface to the
rather new MD5-based crypt() function found in modern operating systems.
It's based on the implementation found on FreeBSD 2.2.[56]-RELEASE and
contains the following license in it:

 "THE BEER-WARE LICENSE" (Revision 42):
 <phk@login.dknet.dk> wrote this file.  As long as you retain this notice you
 can do whatever you want with this stuff. If we meet some day, and you think
 this stuff is worth it, you can buy me a beer in return.   Poul-Henning Kamp

apache_md5_crypt() provides a function compatible with Apache's
.htpasswd files. This was contributed by Bryan Hart <bryan@eai.com>.

"""

MAGIC = '$1$'			# Magic string
ITOA64 = "./0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

from hashlib import md5
import binascii

def to64 (v, n):
	ret = ''
	while (n - 1 >= 0):
		n = n - 1
		ret = ret + ITOA64[v & 0x3f]
		v = v >> 6
	
	return ret

def unix_md5_crypt(pw, salt):
	
	# Take care of the magic string if present
	if salt[:len(MAGIC)] == MAGIC:
		salt = salt[len(MAGIC):]
		
	
	# salt can have up to 8 characters:
	salt = salt.split('$', 1)[0]
	salt = salt[:8]
	
	ctx = md5()
	ctx.update(pw.encode())
	ctx.update(MAGIC.encode())
	ctx.update(salt.encode())
	
	final = md5()
	final.update(pw.encode())
	final.update(salt.encode())
	final.update(pw.encode())
	final = final.digest()
	
	for pl in range(len(pw),0,-16):
		if pl > 16:
			ctx.update(final[:16])
		else:
			ctx.update(final[:pl])
	
	
	# Now the 'weird' xform (??)
	
	i = len(pw)
	while i:
		if i & 1:
			ctx.update(b'\x00')  #if ($i & 1) { $ctx->add(pack("C", 0)); }
		else:
			ctx.update(pw[0].encode())
		i = i >> 1
	
	final = ctx.digest()
	
	# The following is supposed to make
	# things run slower. 
	
	# my question: WTF???
	
	for i in range(1000):
		ctx1 = md5()
		if i & 1:
			ctx1.update(pw.encode())
		else:
			ctx1.update(final[:16])
		
		if i % 3:
			ctx1.update(salt.encode())
		
		if i % 7:
			ctx1.update(pw.encode())
		
		if i & 1:
			ctx1.update(final[:16])
		else:
			ctx1.update(pw.encode())
			
		
		final = ctx1.digest()
	
	final_hex = binascii.hexlify(final)
	
	# Final xform
	
	passwd = ''
	
	passwd = passwd + to64((int(final_hex[0:2], 16) << 16)
							|(int(final_hex[12:14], 16) << 8)
							|(int(final_hex[24:26], 16)),4)
	
	passwd = passwd + to64((int(final_hex[2:4], 16) << 16)
							|(int(final_hex[14:16], 16) << 8)
							|(int(final_hex[26:28], 16)), 4)
	
	passwd = passwd + to64((int(final_hex[4:6], 16) << 16)
							|(int(final_hex[16:18], 16) << 8)
							|(int(final_hex[28:30], 16)), 4)
	
	passwd = passwd + to64((int(final_hex[6:8], 16) << 16)
							|(int(final_hex[18:20], 16) << 8)
							|(int(final_hex[30:32], 16)), 4)
	
	passwd = passwd + to64((int(final_hex[8:10], 16) << 16)
							|(int(final_hex[20:22], 16) << 8)
							|(int(final_hex[10:12], 16)), 4)
	
	passwd = passwd + to64((int(final_hex[22:24], 16)), 2)
	
	
	return MAGIC + salt + '$' + passwd
