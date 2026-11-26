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
  "version": "1.25.1",
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

## GET /api/stats?file=…

Every stat in the save as compact columns per typed group (`base`, `qual`, `owner`, `value`), the readable names
that are known, the rows that change between the downloaded saves (`varies`) and the protected rows.

## GET /api/completion?file=…

Everything the Completion tab shows, one key per part: `stunts`, `compendium`, `discovery`, `challenges`, `gyms`,
`activities`, `checklist` (the game's 100% checklist: `lines` with `key`, `label`, `section`, `value`, `of`, `percent`,
`weight`, `grade`, `module`, `done`, plus `overall`), `tasks`, `gangs`, `robberies`, `fencing`, `activities2`, `hoops`,
`vehicles` and `collectibles`. A part a save can't show yet (an early save lacks some records) is `null`, and
`errors` says why, so the other parts still work.

## GET /api/world?file=…

The time of day (`clock`), `health` and `healthMax` (250, the game's overpowered maximum), and the armour of both
characters' outfits (`armour`, `armourMax`).

## GET /api/savedata?file=…[&section=…&path=…&offset=…]

Without `section`: every section of the save (`hash`, `name` where known, `bytes`, `readOnly` reason, `risky`).
With `section` and a JSON `path`: up to 200 members of that object or list, each with its `key`, `label`, `kind` and
`raw` value, or `count` for an object or list. `means` names what a value stands for when it is the ID of something
known (`{"kind": "Item", "text": "…"}`), and `readOnly` or `min` and `max` mark single fields with their own rule
(maximum health is read-only; health is 1 to 250).

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
| `/api/preview` | `{"file": "…", "stats": [...], "completion": {...}}` | Works out the 100% checklist as it would be after these edits, without writing anything: `{"ok": true, "overall": {...}, "lines": [{key, value, of, percent, done}]}`, or `{"ok": false, "failed": [part names]}` naming the parts that fail on this save |
| `/api/patch` | `{"slot": "…", "money": [...], "ammo": [...], "stats": [...], "completion": {...}, "world": {...}, "raw": [...]}` | Applies every edit for one save to its original, re-encrypts it and gets it ready to send. `completion` holds one choice per part (see the Completion tab), `world` the time, health and armour, `raw` single Save data values |
| `/api/restore` | none | Puts the original saves back, ready to send |
| `/api/upload` | none | Starts sending the save back to the PS5 |
| `/api/cancel` | none | Stops the current task |
| `/api/quit` | none | Closes Save Garage (refused while a transfer is running) |

Each edit names the value it replaces (`value`) and the new one (`newValue`); an edit whose `value` no longer matches
the save is refused. Errors come back as HTTP 409 `{"error": "<code>", "detail": "…"}`.
