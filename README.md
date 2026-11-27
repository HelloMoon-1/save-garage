# GTA6 剧情存档编辑器 · GTA6 Story Save Editor

[简体中文使用指南](README.zh-CN.md)

如果这个工具帮到了你，欢迎给原作者 NotHGM 的 [Save Garage 原仓库点个 Star ⭐](https://github.com/NotHGM/save-garage)。

If this editor helped you, please [star NotHGM’s original Save Garage project](https://github.com/NotHGM/save-garage).

> **This is a modified Chinese build of [Save Garage](https://github.com/NotHGM/save-garage) by NotHGM. It is not the official version.** Official releases: https://github.com/NotHGM/save-garage/releases

<p align="center">
  <a href="../../releases/latest"><b>Download the latest release</b></a>
  &nbsp;&nbsp;|&nbsp;&nbsp; Windows, macOS and Linux &nbsp;&nbsp;|&nbsp;&nbsp; Free and open source (GPL-3.0)
</p>

This editor (formerly MoonSlot) uses its own release channel and signing key. Based on Save Garage by NotHGM (https://github.com/NotHGM/save-garage).

This editor lets you change your **GTA VI story-mode save on PS5**: money, ammo and stats. It needs no jailbreak and installs
nothing on the console. Your PS5 sends the save to your computer through its own Data Transfer feature, you edit it in
your browser, and the PS5 takes it back the same way.

<p align="center"><img src="assets/screens/editor-money.png" alt="The Money tab: the bank up to what its own money boxes hold, with larger amounts as an experimental option" width="88%"></p>

## What you can change

| | What | Status |
|---|---|---|
| **Money** | Bank account, Family Savings and cash for Lucia and Jason. Family Savings goes up to about $2,000,000. The bank goes up to what its own money boxes hold at your point in the story, because shops spend from those. An experimental option goes past them with $85,000 stacks, up to about $230 million, but the game may not let you spend that money. Cash goes up to $20,000. | Tested on PS5; the $85,000 stacks are experimental, and a player couldn't spend them (issue #8) |
| **Ammo** | Every ammo type each character is carrying, named the way the game names it, with one click to refill to a full load (for example 300 assault rifle rounds) or to set the maximum of 9,999. Also lists the weapons each character carries, and adds guns a character doesn't have yet: 15 for Lucia plus the grenade and sticky bomb, and 16 for Jason, each with the kit and default parts the game gives a gun you buy. | Ammo tested on PS5 up to a full load, and a save with more loads fine; adding guns is experimental and not tested on a PS5 yet |
| **Stats** | 90 stats named the way the game's own stats screens name them: 100% completion, time played, health, stamina and focus overpowers and buffs, distance, money earned, wanted stars, kills, shots fired, vehicles stolen, fish caught and more. Each one has a sensible maximum: the game's own total where there is one (130 stunt jumps, 80 challenges, 8 vaults), otherwise a cap far above a long playthrough. | Tested on PS5, except times, distances and the story and styles percentages |
| **Trophy counters** | Stunts, challenges, discoverables, collectibles, collectible cards and vaults robbed. | Tested on PS5 |
| **Completion** | Marks every stunt done (jumps, base jumps, under-the-bridge flights and knife flights), discovers every animal and seen weapon in the compendium and every kind of shop and place on the map, completes challenges by category, adds all 8 gym memberships, completes the meditation spots, marks every robbery location and vault fully hit, records the fencing still missing, completes races, ranges, video games, pool, mini golf, drone trials and Bret's decks, scores all 100 basketball hoops, fills the vehicle compendium to 200 base models and marks every collectible card, luxury watch and identified magazine found (book swaps, magazine styles and cocaine flamingos as experimental options), each with the counters the 100% checklist reads, then works out the 100% figure the way the game does. Shows the game's whole 100% checklist, what each line can be set to, and the new 100% figure before you save. Also unlocks the cheats you pick, each shown with what it does and how the game says to unlock it (experimental). | A save with every option loads and plays on PS5; gym memberships, map discoveries, meditation and fencing confirmed in game, the rest not checked yet; cheats not tested on a PS5 yet |
| **World** | The time of day (the date stays the same), health up to overpowered, and full armour for both characters. Reveals the map: clears the fog of war from the regions known so far, about 722 of the map's 889. For Lucia and Jason: fills the special meter, raises the skills (to 60, the most the game itself wrote, to 99, or to a value you pick; never lowered), sets the criminal profile, and puts on a vest a character owns but isn't wearing. Sets their relationship within the limits the story allows at that point. | Not tested yet; skills, criminal profile, vest and relationship are experimental |
| **All stats** | Every one of the 23,760 stats in the save, searchable, with the game's own wording for the stats it shows and recovered names for most of the rest. Where a real name is still unknown, a plain description of what the stat holds is shown instead, so 99% of the rows in a full-story save read as words. | Can break your save |
| **Save data** | Every section of the save, with names for 64 of the 82 sections and 610 of the 843 keys. Values that are the ID of a known item, stat, place, mission, news article or social media post show its name or opening words. Any number or true/false value can be changed; text, the story flow, heists, vehicle records and the map's fog stay read-only, and the fields the World tab edits keep to its limits. | Can break your save |
| **Trophies** | Not editable. The Trophies page in the app explains what a save edit can and can't do for them. | |
| **Languages** | The app in English (the default), Deutsch, Nederlands, Français, Español, Português (Brasil), Italiano, Polski, Русский, العربية (right to left), 日本語, 한국어 and 中文（简体）. Pick one at the top of the page; the choice is remembered. Names from the game stay as the game writes them. The translations were made with the help of AI, not by native speakers, so corrections are welcome as an issue or pull request (`ui/i18n/<language>.json`). | |

Every edit in the app carries one of those labels, so you always know how safe it is. Edits are always applied to
your original save, and the original is backed up on your computer before anything changes.

<p align="center"><img src="assets/screens/editor-completion.png" alt="The Completion tab: the game's 100% checklist, from 67.51% to 89.81% after picking everything" width="49%">&nbsp;<img src="assets/screens/editor-guns.png" alt="The Ammo tab: picking guns Lucia doesn't have yet" width="49%"></p>

## Before you start

- A PS5 with GTA VI (PPSA01547, PPSA38500 or PPSA29660). Tested on system software 14.23.
- A Windows 10 or 11 PC, a Mac, or a Linux computer on the **same home network** as the PS5.
- An internet connection: decrypting and re-encrypting the save runs on the [GarlicSaves](https://garlicsaves.com) service.
- A GarlicSaves account. From version 1.30.0 Save Garage asks you to sign in to GarlicSaves once on each computer (see
  [Signing in to GarlicSaves](#signing-in-to-garlicsaves)).

## How to use it

1. **Download and start Save Garage** from [Releases](../../releases/latest). Your browser opens the editor at
   `http://127.0.0.1:7283`. Keep the small Save Garage window open while you use it.
   - **Windows:** unzip `MoonSlot-…-windows-x64.zip` and double-click **Start MoonSlot.bat**. Everything it
     needs is inside the folder. If SmartScreen appears, click More info, then Run anyway. When Windows Firewall asks
     about Python, allow it on private networks: the PS5 needs to reach your PC.
   - **Mac:** unzip `MoonSlot-…-macos.zip` and double-click **Start MoonSlot.command**. The first time, right-click
     it and choose Open. It needs Python 3.9 or newer ([python.org](https://www.python.org/downloads/macos/)) and sets
     itself up on the first start. Allow access to devices on your local network when asked.
   - **Linux:** unpack `MoonSlot-…-linux-x64.tar.gz` and run `./MoonSlot --open`. See [Linux notes](#linux-notes).
2. **Connect.** Click Find my PS5, or type its IP address.
3. **Sign in to GarlicSaves (once per computer).** Click Sign in to GarlicSaves. Save Garage shows a code; click Open
   GarlicSaves (or open the address it shows on your phone), sign in to your GarlicSaves account there and enter the
   code. Save Garage carries on by itself once you have approved it.
4. **Pair (once per console).** Click Start pairing, then on the PS5 go to Settings, then System, then System
   Software, then Data Transfer, and pick **Save Garage Pairing**. The PS5 says it can't transfer data. That's
   expected: pairing has already happened.
5. **Download.** In GTA VI, save your game and go back to the PS5 home screen. Click Download save. When the app
   asks, press the PS5 power button once and let go at the beep. The console restarts into transfer mode, and
   again when the download is done. If more than one account on the PS5 has a GTA VI save, the app asks which
   account's save to edit; pick one straight away, while the PS5 waits in transfer mode.
6. **Edit.** Pick a save (the autosave is what Continue loads), change what you want and click Save edits.
7. **Send back.** Delete the GTA VI save on the PS5 (it won't overwrite an existing one): Settings, then Saved
   Data and Game/App Settings, then Saved Data (PS5), then Console Storage, then Delete. Then click Send save to
   PS5 and on the PS5 open Data Transfer, pick **Save Garage** and choose Start Transfer.

<p align="center"><img src="assets/screens/send-back.png" alt="The Send back step: what is being sent and every save that goes back" width="88%"></p>

Start small: change a couple of things, send the save back and check it loads before you change more. If a save
won't load, delete it on the PS5, click **Put the originals back** and send again.

## What leaves your computer

Your save is encrypted with a key that never leaves the PS5, so Save Garage sends the encrypted save to the
[GarlicSaves](https://garlicsaves.com) service to decrypt it, and the edited save to re-encrypt it for your account.
That upload includes your PSN account ID, which is stored in the save. GarlicSaves runs the work on PS5 consoles of
its own. Its consoles also work out the keys for each Data Transfer session. Every request to GarlicSaves carries the
key of your GarlicSaves sign-in (below), so GarlicSaves knows which account it works for.

Nothing else is uploaded. The editor runs only on your computer, and by default only your computer can open it.
In packaged builds, downloads and their original backups are stored in the `saves` folder beside the launcher.
Extract the package to a writable folder. Source runs keep saves in `data`.

## Related

- [GTA 6 hash database](https://github.com/NotHGM/gta6-hash-database): every name Save Garage has decoded (stats, items,
  vehicles, missions, save keys) with the evidence for each, plus 1.1 million GTA VI hashes from the community's name
  lists, as searchable text tables.

From version 1.30.0, Save Garage also asks GitHub whether a new version is out (see [Updates](#updates)). That request
carries nothing about you, your PS5 or your saves.

## Signing in to GarlicSaves

**Why.** GarlicSaves now requires each app installation to be authorised with your own GarlicSaves account. Until
version 1.29.1, every copy of Save Garage sent the worker key that GarlicTransfer used to have built in; GarlicSaves
has revoked that key, so those versions can no longer download (1.29.1 says "GarlicSaves isn't accepting key
requests"). From 1.30.0 Save Garage signs in the way GarlicTransfer 0.4.0 does, with GarlicSaves' device authorisation:

<p align="center"><img src="assets/screens/signin.png" alt="The Sign in step: the code to enter on GarlicSaves" width="88%"></p>

1. On the Sign in step, click **Sign in to GarlicSaves**. Save Garage asks GarlicSaves for a code, as an
   installation called "Save Garage" (nothing about your computer).
2. Click **Open GarlicSaves**, or open the address shown on another device, sign in to your GarlicSaves account and
   enter the code. The code works for up to 10 minutes; the page counts down.
3. Save Garage checks every few seconds and carries on by itself once you have approved it. Cancel stops it.

You do this once on each computer. Pairing, downloading, saving edits and sending saves back all go through
GarlicSaves, so until you are signed in the page shows the Sign in step instead of starting them.

**What is stored where.** GarlicSaves gives Save Garage on this computer a worker key of its own, with an installation
ID and your GarlicSaves username. Save Garage keeps the three as `"garlicSaves"` in `config.json` in its data folder
(see [What leaves your computer](#what-leaves-your-computer) for where that is), a file only you can read: mode 600 on
macOS and Linux, and on Windows the data folder is your own. The key goes to GarlicSaves only, with each of its
requests (it is handed to curl on its standard input, not on its command line). It never appears on the page, in Show
details or in an error message; the page shows your GarlicSaves username, and only on your computer. Updates never
touch `config.json`, so you stay signed in when Save Garage updates itself or puts an older version back. The
`workerKey` setting of earlier versions is no longer used.

**Signing out.** Go to the Sign in step and click **Sign out**. Save Garage forgets the key on this computer (it
takes `"garlicSaves"` out of `config.json`); it doesn't tell GarlicSaves. To use Save Garage again, sign in again.

**When GarlicSaves refuses the sign-in.** If GarlicSaves turns the key down (the sign-in was turned off or has
expired), the download, edit or send stops with "GarlicSaves refused your sign-in", the top of the page says "GarlicSaves
sign-in refused", and a **Sign in again** button gets you a new key.

## Updates

From version 1.30.0, MoonSlot keeps itself up to date. When it starts, and every 6 hours while it runs, it asks
GitHub for the latest release. When there is a newer version, it downloads it in the background, checks it (below) and
installs it the next time you start MoonSlot. **Restart now**, at the bottom of the page, does that straight away;
it can't be used while a download, an edit or a send is running. If the new version doesn't start within 90 seconds,
or stops before it does, MoonSlot puts the old version back by itself and stays on it. The previous version is kept:
in `MoonSlot/.update/previous` on Windows and macOS, and next to the folder with the Linux build (`.MoonSlot.previous`
for a folder called `MoonSlot`). The bottom of the page says what is happening and links to the release notes.

**What it contacts.** `api.github.com`, for the latest release of this project, and `github.com` for that release's
files (GitHub passes downloads on to its file servers, such as `release-assets.githubusercontent.com`). The requests
carry no account, token or cookie, and nothing about you, your PS5 or your saves: just a fixed User-Agent,
`MoonSlot-update-check (+https://github.com/HelloMoon-1/save-garage)`. GitHub sees your IP address, as it would for any
web page. They go through the same proxy as
the rest of MoonSlot. A download only happens when there is a new version.

**How to turn it off.** Untick **Update automatically** at the bottom of the page. MoonSlot then contacts GitHub only
when you click **Check for updates**, and only tells you that a new version is out; an update it had already downloaded
is dropped and not installed. The setting is saved as `"autoUpdate": false` in `config.json` in the data folder above.

**How the signing protects you.** Every release from 1.30.0 on comes with `SHA256SUMS.txt`, the SHA-256 of each
download, and `SHA256SUMS.txt.sig`, an Ed25519 signature of that list, made with a key that only the maintainer holds
and that never leaves their computer. MoonSlot has the public half built in, and it installs an update only when:

- the signature matches that key;
- the download's SHA-256 matches the signed list, and every file the list names carries the new version number;
- the version is newer than yours (it never goes back, so an old release can't be passed off as a new one), and the
  release is published, not a draft or a prerelease;
- the archive holds only ordinary files inside its `MoonSlot` folder (no links, no `..`, no absolute paths), within
  size limits.

So even someone who took over the GitHub account, GitHub's download servers or your network couldn't make MoonSlot
install anything the maintainer didn't sign. A release that fails a check is not installed, and the page says why.
You can check a release yourself with OpenSSL 3: save this public key as `moonslot-release.pem` (its fingerprint, the
SHA-256 of the 32 key bytes, is `5bce5dcbfbb14119ab37762c19f26beb8778a263d2babb173b5582ad8e8608df`)

```
-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAWmamnS4PF+PM8YdqY4Bk9bo98SWlWIEJBf5axE734yQ=
-----END PUBLIC KEY-----
```

and run, in the folder with the downloads:

```
openssl pkeyutl -verify -pubin -inkey moonslot-release.pem -rawin -in SHA256SUMS.txt -sigfile SHA256SUMS.txt.sig
sha256sum -c --ignore-missing SHA256SUMS.txt
```

**What it updates.** The Windows and macOS downloads (the app files and launchers in the `MoonSlot` folder; files of
your own there are left alone) and the Linux build (the whole folder, so only a folder that holds nothing but the
download's files). If a new version needs a different Python than the one in your Windows folder, or other Python
packages on a Mac, the page says a new version is out, with a link, and you download that one yourself. When you run
MoonSlot from a git checkout, or from any folder that isn't laid out like a download (or that it can't write to), it
never changes a file and only tells you a new version is out. It doesn't install, or put anything back, while another
copy of MoonSlot is running. What it did is logged in `update/update.log` in the data folder. An update or a
rollback changes only the app's own folder and its working files in `update` in the data folder, never your saves,
backups or GarlicSaves sign-in.

## Related

- [GTA 6 hash database](https://github.com/NotHGM/gta6-hash-database): every name Save Garage has decoded (stats, items,
  vehicles, missions, save keys) with the evidence for each, plus 1.1 million GTA VI hashes from the community's name
  lists, as searchable text tables.

## Good to know

- **Money is capped by the game.** Each account holds money in boxes of a fixed size. Family Savings gets the larger
  boxes the game itself uses for savings goals. The bank stays within its own boxes, because shops only spend money
  from those: versions before 1.24.0 put extra money in Family Savings boxes under the bank, which BuckMe showed but
  shops couldn't spend (issue #3). Editing the bank again, or **Make it spendable** on the Money tab, moves it back.
  Past its boxes, the bank can also take $85,000 stacks under its $85,000 box, which BuckMe shows in the balance.
  Versions 1.26.0 to 1.30.0 put anything past the boxes in such stacks, but they may not be spendable: a player on
  1.30.0 with about $2,000,000 in the bank couldn't make a $150,000 phone payment (issue #8). Since 1.30.1 the stacks
  are an experimental option on the Money tab, off by default, until a PS5 shows the game spends them. Each stack takes
  one inventory slot, and Save Garage always leaves 300 free, so their limit depends on the save (about $230 million in
  a late save, and at most $999,999,999). An early save, before the story gives the bank its $85,000 box, has no
  stacks. A bank already past its boxes shows how much of it is in stacks, and **Make it spendable** sets it to what
  its boxes hold, emptying the stacks. Cash stays at the $20,000 wallet.
- **A balance of 0 can't be edited.** The game doesn't store it. Get a little money in the game, save and download again.
- **Only ammo you carry is listed.** Pick some up in the game first to add a new type.
- **Adding guns is experimental.** A gun is built row for row the way the game wrote guns that were bought in a save:
  the weapon, its standard kit and default parts, and its place in the list of weapons a character has owned. Only
  guns the game wrote with nothing but their default parts in a save Save Garage was built from are offered: 15 for
  Lucia plus the grenade and sticky bomb, and 16 for Jason. The others were only ever seen with bought mods or mission
  kits, so they aren't offered yet: the assault, battle, carbine and special rifles, the GPMG and combat MG, the .50,
  military and polymer pistols, the civilian, long and magnum revolvers, the pump-action shotgun and the short
  shotguns, the micro and tactical SMGs and the short compact SMG, both sniper rifles, the carbine, hunting and
  sporting tactical rifles, both bats, and Lucia's civilian pistol. Guns come without ammo (buy or pick some up, then
  refill it on the Ammo tab); the grenade and sticky bomb come with 5 and 4. A gun the compendium doesn't list yet is
  added to it too, as the game does, which can raise STANDARD ISSUE WEAPONS and the 100% figure. Nothing a character
  has is changed, each gun takes a few inventory slots (300 are always left free), and an inventory that already
  breaks one of the game's rules is left alone. Not tested on a PS5 yet.
- **Cheats are experimental, and using one in the game turns off trophies and saving for the rest of that session.**
  The game says so when you use one; unlocking a cheat in Save Garage doesn't use it. GTA VI keeps a tracker for each
  of its 62 cheats in the save, and Save Garage completes the trackers you pick the way the game does when you meet a
  cheat's condition. Whether the cheat then shows in the game's Progress menu isn't known yet: not tested on a PS5.
  The two cheats of each challenge category (5 challenges and all of them) can't be told apart in the save, so they
  are completed together, and 23 trackers that held no progress in any save checked can only be completed all at
  once. Trophies, the 100% figure, the profile-wide awards and anything else are left alone.
- **The map reveal is partial.** Save Garage knows 722 of the map's 889 regions: the 52 named regions and the 670
  smaller areas found in game saves. The rest stay covered until you explore them. Regions are only ever added, and
  none the save already has is changed.
- **Skills, the criminal profile, the vest and the relationship are experimental.** No save the game wrote has more
  than 60 in a skill; 99 is what GarlicSaves writes and reports working in the game. Skills and the special meter are
  only ever raised. The criminal profile is the game's temperament score (Professional, Hardened, Violent, Psycho,
  Irredeemable); which score gives which profile isn't known yet, and a new game starts Lucia at -25. A vest is put on
  only for a character who owns one and wears no armour. The relationship can be changed only when the story hasn't
  locked it, and only within the limits it sets. None of these has been tested on a PS5 yet.
- **Turn off PS Plus auto-sync for GTA VI** while you test an edited save, so it can't replace your cloud backup.
- **Trophies can't be written by a save editor.** Spending money you added still unlocks money trophies the normal way.
  Trophy-hunting sites such as PSNProfiles may flag trophies earned with a save editor.
- **Online play isn't affected.** Save Garage edits story-mode saves only.

## Troubleshooting

| Problem | Fix |
|---|---|
| The PS5 doesn't list Save Garage Pairing | Check the PS5 and computer are on the same network, and that your firewall allows TCP 1004-1005 and UDP 1006 from the PS5. |
| Pairing or sending fails at once with a permission error | On Linux, ports below 1024 need permission. See [Linux notes](#linux-notes). |
| Ports 1004 to 1006 are in use | Close any other save-transfer tool or second copy of Save Garage. |
| The PS5 says there's nothing to transfer | A GTA VI save is still on the console. Delete it, then open Data Transfer again. |
| Decryption service offline | Check your internet connection. GarlicSaves may also be down for a while. |
| A download stops with "GarlicSaves' key service didn't answer in time" | The GarlicSaves consoles that work out the transfer keys were busy. Before the power prompt, Save Garage tries once more by itself; if that fails too, wait a minute and download again. Nothing is wrong with your PS5. Show details lists how long the key service took and why, for example no worker free or a worker that took too long. |
| A download or saving edits stops with "GarlicSaves is getting too many requests right now" | GarlicSaves takes only so many requests a minute from each sign-in's key. Before the power prompt, Save Garage waits as long as GarlicSaves asks, about a minute (the page counts down), and tries once more by itself. Otherwise, or if that is limited too, wait a minute and try again. Nothing is wrong with your PS5 or Save Garage. |
| Pairing, a download, saving edits or sending stops with "GarlicSaves refused your sign-in" | GarlicSaves turned down the key of your sign-in: the sign-in may have been turned off, or it may have expired. Click Sign in again and approve Save Garage on GarlicSaves once more, then try again. |
| Signing in says the code expired | Click Sign in to GarlicSaves again for a new code, and enter it on GarlicSaves before the time shown runs out. |
| Version 1.29.1 or older stops with "GarlicSaves isn't accepting key requests from Save Garage's shared key" | GarlicSaves revoked that key. Update to 1.30.0 or newer and sign in to GarlicSaves. |
| A download stops with "The PS5 didn't answer" | Go back to the PS5 home screen, close any other save-transfer tool so Data Transfer is free, and try again. |
| A download stops with "The power-button wait timed out" | Download again, and when the app asks, press the PS5 power button once within about 5 minutes and let go at the beep. |
| The bottom of the page says "Update failed" | Nothing changed: Save Garage stays on the version you have. A download that didn't finish or failed a check is tried again at the next check (or click Check for updates); a version that didn't start isn't tried again. You can always download the new version yourself from [Releases](../../releases/latest). `update/update.log` in the data folder says what happened. |
| The Linux `MoonSlot` folder is gone after a power cut during an update | Rename `.MoonSlot.backup` (named after your folder), next to where it was, back to `MoonSlot`. |

## Linux notes

Run from source (below). The PS5 protocol uses ports 1004 to 1006, which Linux keeps for root. Allow them while you
use Save Garage, and set it back afterwards:

```
sudo sysctl -w net.ipv4.ip_unprivileged_port_start=1004
sudo sysctl -w net.ipv4.ip_unprivileged_port_start=1024
```

To use the editor from another device on your network, start it with your computer's address, for example
`python3 engine/main.py --host 192.168.1.20`. Only devices on that /24 network are allowed in.

## Run from source

Python 3.10 or newer and `curl` are required.

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt          # Windows: .venv\Scripts\pip install -r requirements.txt
.venv/bin/python engine/main.py --open             # Windows: .venv\Scripts\python engine\main.py --open
```

Options: `--port N` (default 7283), `--host ADDRESS`, `--allow NETWORKS`, `--no-browser`.

For development and tests only, the environment variable `SAVEGARAGE_DEV_WORKER_KEY` gives Save Garage a GarlicSaves
worker key to use in place of the sign-in.

A git checkout never updates itself: it only shows at the bottom of the page when a new version is out.

Release files are built on Linux with [`scripts/package_release.sh`](scripts/package_release.sh): a portable Windows
folder with the official embeddable Python, a Mac launcher, and a self-contained Linux build, plus `SHA256SUMS.txt`.
Each holds a `build.json` that tells the updater what kind of build it is. [`scripts/sign_release.py`](scripts/sign_release.py)
signs `SHA256SUMS.txt` with the release key and checks the signature the way the app does.
`scripts/build_windows.bat` and `scripts/build_macos.sh` make single-folder builds with PyInstaller on those systems.

## Credits and license

Based on [Save Garage](https://github.com/NotHGM/save-garage) by NotHGM, who wrote its save engine and research, every
editor (money, stats, completion, world, guns and more), the GarlicSaves sign-in, the updater and the interface. This
copy is a modified build, not the official one.

Save Garage is free software under the [GNU GPL v3](LICENSE). It started from

Save Garage, Copyright (C) 2026 NotHGM. It is free software under the [GNU GPL v3](LICENSE), with the additional terms in
[NOTICE](NOTICE) that section 7 of the licence allows. In short, for the parts written by NotHGM: a copy or modified
version must keep the credit "Based on Save Garage by NotHGM (https://github.com/NotHGM/save-garage)", a modified
version must say clearly that it is modified and not the official Save Garage, and a modified version you distribute
must use its own name and logo.

Save Garage started from
[gta6-save-editor](https://github.com/CoreyLyu76/gta6-save-editor) by CoreyLyu76 and includes PS5 Data Transfer code
and the GarlicSaves sign-in flow from [GarlicTransfer](https://github.com/earthonion/GarlicTransfer) by earthonion, both
GPL-3.0. Details in
[CREDITS.md](CREDITS.md).

Save Garage is not affiliated with or endorsed by Rockstar Games, Take-Two Interactive or Sony Interactive
Entertainment. Grand Theft Auto and PlayStation are trademarks of their owners. Use it on your own single-player saves.
Editing a save can break it, so keep your backups.
