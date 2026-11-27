# vendor/poc

PS5 Data Transfer code (discovery, pairing, download and upload) from
[GarlicTransfer](https://github.com/earthonion/GarlicTransfer) v0.3.7 by earthonion, licensed under GPL-3.0.

Changes made for Save Garage:

- `dt_pair.py`: on macOS the pairing listener binds to `0.0.0.0`, because a normal user can bind ports below 1024
  only on the wildcard address there. The pairing source is named "Save Garage Pairing".
- `dt_source.py`: when `DT_CONSOLE_IP` is set (the app sets it on macOS only), the source keeps announcing itself to
  the console instead of waiting for its search broadcast, which a Mac on Wi-Fi often misses. On macOS the discovery
  socket is bound without `SO_REUSEADDR` and the data port opens when the PS5 connects. The default source name is
  "Save Garage".
- `dt_source.py` (1.31.0, GitHub issue #7, pull request #10): a console that sends `01000000` at bytes 52-55 of its
  power request (hardware 3 on 14.23) gets the newer console-info layout (0 at 16, the version at 40 and 52, 1 at 48,
  the data address at 56) with the computer's IPv6 link-local address on the adapter carrying the connection (found
  with psutil), an IPv6 data listener and oracle keys on that data channel. Every other console gets the original
  reply, byte for byte. The data accept loop keeps running after any failed connection.
- Modules this app doesn't use (`dt_export_zip.py`, `dt_ftp_server.py`, `dt_save_editor.py`) and the `local_worker`
  and `ncdt_oracle` folders for jailbroken consoles are not included.
