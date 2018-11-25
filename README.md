# MSN Server

This is an MSN server. Support is planned for all MSN and WLM clients.

See [escargot.log1p.xyz](https://escargot.log1p.xyz) for how to connect.


## Support status

Currently, MSNP2 through MSNP12 are implemented. It's been tested and works with MSN 1 through MSN 7.5, with some caveats:

- Because of MSNP limitations, if you want to log in to MSN < 5, you have to store an MD5-encoded password (`User.password_md5`)

## Developers

See [CONTRIBUTING.md](/CONTRIBUTING.md).
