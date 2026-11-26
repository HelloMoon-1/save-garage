# Local API

Save Garage serves its web UI and a JSON API from the same address, `http://127.0.0.1:7283` by default. Requests
are accepted only from allowed client networks (this computer by default) with a matching `Host` header, and POST
bodies are JSON. Long tasks run in the background: a POST returns at once and progress appears in `state.job`.

## GET /api/state

The whole app state, polled about once a second by the UI.

```jsonc
{
  "console": {"host": "192.168.1.20", "name": "PS5", "hostId": "AABBCCDDEEFF", "firmware": "14230000", "sameSubnet": true} | null,
  "paired": true,
  "network": {"ok": true, "proxy": false} | null,     // set after POST /api/network
  "hasSession": true,                                 // a save has been downloaded
  "readyToUpload": false,                             // edits are saved and waiting to be sent
  "slots": [{
    "file": "sdimg_SAVEDATASARC0001",                 // or sdimg_sce_sdmemory, the autosave
    "subtitle": "Mission name",
    "items": [{"inv": 0, "idx": 384, "kind": "bank", "value": 85000, "max": 223844, "spendable": 85000, "stuck": 0}],
    "ammo": [{"inv": 0, "idx": 120, "type": "rifle", "label": "Assault rifle ammo", "value": 280, "full": 300, "max": 9999}],
    "modified": false,
    "changes": [{"kind": "bank", "from": 5000, "to": 85000}],
    "applied": {"money": [], "ammo": [], "stats": []} | null
  }],
  "job": {"id": 3, "kind": "download", "status": "running", "stage": "need_power", "needPower": true,
          "progress": {"files": 2, "total": 5} | null, "hint": null, "error": null, "log": []},
  "fileCount": 11,                                    // saves of the downloaded account, all of which go back to the PS5
  "version": "1.28.0",
  "canQuit": false                                    // true in the desktop builds
}
```

## GET /api/slot?file=…

Editor data for one save: featured stats with the exact rows to edit, ammo and the weapons each character carries.
For the bank, `boxMax` is what the bank's own money boxes hold, and `max` adds a $85,000 stack for every inventory slot left
above the 300 kept free (at most $999,999,999; equal to `boxMax` when the save has no $85,000 box yet). `stacks` counts
the extra stacks the bank already has, `spendable` is the money the game can spend, and `stuck` is money an older version
left in Family Savings boxes under the bank (shown by BuckMe, not spendable; editing the bank moves it).
For ammo, `full` is a full load in the game (`null` where it isn't known) and `max` is the most Save Garage writes.
Each weapon is
`{"inv": 0, "id": "5dd5e66d", "name": "weaponspec_autorifle_assault_default", "label": "Kozlov KZ-59", "kind": "Assault rifle"}`:
`label` is what the game calls it (empty while the weapon isn't identified) and `kind` is the type of weapon when the
label doesn't say it.

`guns` lists the guns each character can be given (`null`, with the reason in `errors.guns`, when the save can't show
them): `characters`, one per character (`key` `lucia` or `jason`, `name`), with `problem` (a refusal code, below, while
no gun can be added), `items` (the inventory's Items entries) and `itemsFree` (entries left above the 300 kept free),
and three lists of guns: `offered` (can be added), `owned` (already there) and `left` (a grenade or sticky bomb whose
ammo the character has without the weapon, a state no save has shown, so it is left alone). Each gun is
`{"id": "5ea6e528", "name": "weaponspec_smg_heavy_default", "label": "BZI Vatra", "kind": "Heavy SMG", "rows": 11,
"thrown": false, "ammo": null, "discovered": true}`: `rows` is the inventory entries it takes, `ammo` the grenades or
sticky bombs that come with a thrown weapon, `discovered` whether the compendium lists it already. `notOffered` names,
per character, the guns seen in game saves that can't be added yet, and `itemLimit` and `itemReserve` are 4,095 and 300.

## GET /api/stats?file=…

Every stat in the save as compact columns per typed group (`base`, `qual`, `owner`, `value`), the readable names
that are known, the rows that change between the downloaded saves (`varies`) and the protected rows.

## GET /api/completion?file=…

Everything the Completion tab shows, one key per part: `stunts`, `compendium`, `discovery`, `challenges`, `gyms`,
`activities`, `checklist` (the game's 100% checklist: `lines` with `key`, `label`, `section`, `value`, `of`, `percent`,
`weight`, `grade`, `module`, `done`, plus `overall`), `tasks`, `gangs`, `robberies`, `fencing`, `activities2`, `hoops`,
`vehicles`, `collectibles` and `cheats`. A part a save can't show yet (an early save lacks some records) is `null`, and
`errors` says why, so the other parts still work.

`cheats` is the cheat unlock trackers (challenge set `d6d53427`, 62 records): `done` of `of` complete, `problem` (a
refusal code, then `entries` is empty) and `entries` in the order the tab lists them. Each entry is one pick:
`{"key": "0c7d4ae2", "kind": "single" | "pair" | "unmatched", "ids": ["0c7d4ae2"], "done": 0, "of": 1, "cheats":
[{"name": "Super Jump", "effect": "Increases the height of your jump by 10x with no fall damage.", "unlock": "Jump a
vehicle 15 meters or more over a drawbridge 50 times."}]}`. `effect` and `unlock` are the game's words; `name` is the
game's name for the cheat where its text has one that plainly matches, else `null`. A `pair` is a challenge category's
two trackers (5 challenges and all of them), which the save can't tell apart; `unmatched` is the 23 trackers that held
no progress in any save checked, with the 23 cheats they are between them.

## GET /api/world?file=…

The time of day (`clock`), `health` and `healthMax` (250, the game's overpowered maximum), and the armour of both
characters' outfits (`armour`, `armourMax`). Two more parts are read on their own; one a save can't show is `null`,
and `errors` says why:

- `player`: `characters`, one per character (`key` `lucia` or `jason`, `name`), with `meter` (attribute slot 24),
  `skills` (the values of slots 9, 10, 13, 14, 15, 19, 20 and 35), `profile` (the criminal profile score),
  `attributesProblem` (a refusal code when the attributes can't be edited) and `vest`
  (`{"state": "can_add" | "worn" | "no_vest" | "unknown", "armour", "max", "owned"}`); `relationship` (`value`,
  `lowerCap` and `cap`, the range the story allows now, `level`, `locked`, `disabled` and `problem`, a refusal code
  while it can't be changed); and the limits: `meterFull` (100), `skillMin` and `skillMax` (1 and 99),
  `skillChoices` (60 and 99), `profileMin` and `profileMax` (-100 and 0.25), `profileNewGame` (-25), `vestArmour` (150).
- `fog`: the map's fog of war. `regions` uncovered in the save (`named` and `cells`), `known` (the 722 regions Save
  Garage knows: `knownNamed` 52, `knownCells` 670), `mapTotal` (889), `missing` (known regions the save still lacks),
  `unknown` (regions in the save that Save Garage doesn't know, kept as they are) and `problem` (a refusal code).

## GET /api/savedata?file=…[&section=…&path=…&offset=…]

Without `section`: every section of the save (`hash`, `name` where known, `bytes`, `readOnly` reason, `risky`).
With `section` and a JSON `path`: up to 200 members of that object or list, each with its `key`, `label`, `kind` and
`raw` value, or `count` for an object or list. `means` names what a value stands for when it is the ID of something
known (`{"kind": "Item", "text": "…"}`), and `readOnly` or `min` and `max` mark single fields with their own rule,
the same limits the World tab keeps to: maximum health is read-only; health is 1 to 250; the criminal profile is -100
to 0.25; the relationship stays within the story's caps and is read-only while the story has it locked or switched
off, and those caps and flags are read-only themselves; the skill slots of a character's attributes go up to 99 and
slot 24 to 100; an armour part's fArmour goes up to its fMaxArmour, and fMaxArmour up to 150. FogOfWar is read-only
(the World tab reveals the map).

## POST endpoints

| Path | Body | What it does |
|---|---|---|
| `/api/network` | none | Checks that GarlicSaves is reachable |
| `/api/discover` | none | Searches the network for PS5 consoles |
| `/api/console` | `{"host": "192.168.1.20"}` | Selects a console |
| `/api/pair` | none | Starts pairing (once per console) |
| `/api/download` | none | Downloads, backs up and decrypts the GTA VI saves |
| `/api/choose-account` | `{"owner": "<account id>"}` | Answers the download's question when several PS5 accounts have a GTA VI save: while the job's stage is `choose_account`, `job.accounts` lists `{id, name, saves}` and only those ids are accepted |
| `/api/stunt-edits` | `{"file": "…", "groups": ["jumps", "base", "bridges"]}` | The stat edits that mark those stunt types found and completed, for the page to add to `stats` |
| `/api/preview` | `{"file": "…", "stats": [...], "completion": {...}, "guns": {...}}` | Works out the 100% checklist as it would be after these edits, without writing anything: `{"ok": true, "overall": {...}, "lines": [{key, value, of, percent, done}]}`, or `{"ok": false, "failed": [part names]}` naming the parts that fail on this save (`guns` among them) |
| `/api/patch` | `{"slot": "…", "money": [...], "ammo": [...], "stats": [...], "guns": {...}, "completion": {...}, "world": {...}, "raw": [...]}` | Applies every edit for one save to its original, re-encrypts it and gets it ready to send. `guns` the Ammo tab's guns to add (below), `completion` holds one choice per part (see the Completion tab, and the cheats below), `world` the World tab's edits (below), `raw` single Save data values |
| `/api/restore` | none | Puts the original saves back, ready to send |
| `/api/upload` | none | Starts sending the save back to the PS5 |
| `/api/cancel` | none | Stops the current task |
| `/api/quit` | none | Closes Save Garage (refused while a transfer is running) |

Each edit names the value it replaces (`value`) and the new one (`newValue`); an edit whose `value` no longer matches
the save is refused. Errors come back as HTTP 409 `{"error": "<code>", "detail": "…"}`.

### Download errors

A download that fails ends with `job.status` `error` and `job.error` `{"code": "…", "detail": "…"}`, where `detail` is
the transfer code's own error, such as `TimeoutError: timed out`. A timeout gets its code from when it came and from
what GarlicSaves' key service did: `power_timeout` while the power prompt was up (stage `need_power`), `key_timeout` when
a transfer-key derivation didn't give the transfer code its keys within its 30 s wait (it gave up, was still waiting or
answered later), and `console_timeout` otherwise, for a PS5 that didn't answer. A `key_timeout` before the power prompt,
with nothing downloaded yet, starts the download once more by itself after 5 s, with the stage `key_retry` in between
(`/api/cancel` then ends it); a second one ends the download. The other codes are `not_paired`, `garlic_unreachable`,
`console_rejected`, `download_failed`, `no_gta_save` and `no_story_slot`. The job's `log` has a line for each
derivation, such as `Key service: answered in 4.2 s (1 request)` or `Key service: no answer after 30 s (3 requests)`:
timings and request counts only.

### The World tab's edits

```jsonc
"world": {
  "time": {"hour": 21, "minute": 30},       // the date stays the same
  "health": 250,                            // 1 to 250
  "armour": "full",                         // every armour part of both characters up to its maximum
  "fog": "known",                           // reveal every map region Save Garage knows
  "lucia": {"meter": "full", "skills": 99, "profile": -25.0, "vest": true},
  "jason": {"skills": 60},                  // any of the four, for either character
  "relationship": 69                        // within the story's caps
}
```

Every key may be left out, and every edit is checked against the save before anything is written:

- `fog` appends each known region the save lacks, the way the game writes one, and never changes, removes or moves
  an entry. It is refused when the map data's version isn't 9 (`fog_version`), an entry has other keys, a type other
  than 1 or 2 or a known region with the other type (`fog_entry`), or a region is listed twice (`fog_repeat`).
- `meter` fills attribute slot 24 to 100; `skills` raises slots 9, 10, 13, 14, 15, 19, 20 and 35 to the value given
  (1 to 99). Both only ever raise, and slots 17 and 23 and the core slots 0-3 and 30-33 are never written. The
  attributes must have their 37 values (`attributes_layout`).
- `profile` sets the criminal profile, -100 to 0.25, written as the game writes it (float32 with six decimals).
- `vest` puts on the vest a character owns when that character wears no armour: armour part 1 becomes 150 of 150
  and the outfit's cached-armour flag true. Refused when the character has no vest in the wardrobe (`no_vest`); a
  character who already wears armour is left as is.
- `relationship` is refused while the story has it locked (`relationship_locked`) or switched off
  (`relationship_disabled`), and outside its caps (`out_of_range`). Its level isn't changed.

Out-of-range values are `out_of_range`, wrong types `bad_value`, and unknown keys in a character's object
`bad_request` (other keys of `world` are ignored); in the job's error they carry the `save_` prefix. Applying the
same edits again changes nothing.

### Guns to add (Ammo tab)

```jsonc
"guns": {
  "lucia": ["5ea6e528", "c24e18bf"],        // weapon ids from guns.characters[].offered, or "all"
  "jason": "all"
}
```

Each gun a character doesn't have (no row of that weapon in its weapons list) is added the way the game writes a gun
you buy, row for row as the game itself wrote bought guns in a save: the weapon row under the character's weapon
container, its `_001` kit and default `regular_01` parts under it, their ParentGuids and Items entries, and the weapon in
OwnedWeaponsHistory (not for the grenade and sticky bomb, which the game leaves out). The grenade and sticky bomb come
with the ammo row the game added with them (5 and 4). A weapon the compendium doesn't list yet is added to it, with its
counters, and the 100% figure is worked out again. Nothing a character has is changed: guns it has are skipped, so the
same edit applied again changes nothing. No money is spent, and the purchase counters stay as they are.

Refused, with nothing written: `guns_layout` (the inventory isn't shaped as the game writes it: InventoryId, list
columns, one character root with one weapon container, a sorted OwnedWeaponsHistory), `inventory_damaged` (a Guid used
twice, Items not listing every row exactly once, a parent index that dangles or a ParentGuids entry without a child),
`item_limit` (Items would pass 4,095 less the 300 kept free), `not_offered` (a gun that can't be added to that
character), `bad_request`, `verify_failed` (the result isn't the old inventory plus exactly the new rows).

### Cheats (Completion tab)

```jsonc
"completion": {"cheats": {"trackers": ["0c7d4ae2", "d40c07aa", "c2737d73"]}}     // or {"trackers": "all"}
```

Each chosen cheat tracker that isn't complete is completed the way the game completes one when its condition is met:
`isComplete` true and the empty parameter, nothing else. No counter or 100% line counts these trackers, so the
checklist and the 100% figure stay as they are; the profile-wide awards, the goals and the unlock catalogs aren't
touched. Whether the cheat then shows in the game's Progress menu isn't known yet. Using a cheat in the game turns off
trophies and saving for the rest of that session. Refused: `cheats_layout` (the set isn't the 62 known trackers, or a
record isn't shaped as the game writes it), `not_editable` (a record of another challenge set), `unknown_challenge`,
`bad_request`, `verify_failed`. Errors carry the `save_` prefix in the job's error.
