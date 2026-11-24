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
- Modules this app doesn't use (`dt_export_zip.py`, `dt_ftp_server.py`, `dt_save_editor.py`) and the `local_worker`
  and `ncdt_oracle` folders for jailbroken consoles are not included.
