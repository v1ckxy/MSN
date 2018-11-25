import binascii

Y64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._"

def Y64Encode(string_encode):
	string_hex = binascii.hexlify(string_encode)
	limit = len(string_encode) - (len(string_encode) % 3)
	pos = 0
	out = ""
	buff = [0] * len(string_encode)
	i = 0
	hex_start = 0
	hex_end = 2
	
	while i < len(string_encode):
		buff[i] = int(string_hex[hex_start:hex_end], 16) & 0xff
		hex_start += 2
		hex_end += 2
		i += 1
	
	i = 0
	
	while i < limit:
		out += Y64[buff[i] >> 2]
		out += Y64[((buff[i] << 4) & 0x30) | (buff[i + 1] >> 4)]
		out += Y64[((buff[i + 1] << 2) & 0x3c) | (buff[i + 2] >> 6)]
		out += Y64[buff[i + 2] & 0x3f]
		
		i += 3
	
	i = limit
	
	if (len(string_encode) - i) == 1:
		out += Y64[buff[i] >> 2]
		out += Y64[((buff[i] << 4) & 0x30)]
		out += "--"
	elif (len(string_encode) - i) == 2:
		out += Y64[buff[i] >> 2]
		out += Y64[((buff[i] << 4) & 0x30) | (buff[i + 1] >> 4)]
		out += Y64[((buff[i + 1] << 2) & 0x3c)]
		out += "-"
	
	return out