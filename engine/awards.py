"""Local profile award records in Challenges set 348d4be2, version with 54 known IDs.

Names follow PSN listing order (Exophase, Grand Theft Auto VI PS5); the pairing
with save IDs is inferred from the original record sequence, not PSN account data.
Use explicit IDs for edits, even when the input save orders its records differently.
https://www.exophase.com/game/grand-theft-auto-vi-psn/trophies/
"""
import json

import challenges as ch
import featurelib as fl

SET_ID = 0x348d4be2
NAMES = {
    0xaf850e8d: ('Just Like Paradise', 'Finish Gone Fishing.'),
    0xbd49aa16: ('Paradise Lost', 'Reach the end of Chapter 1.'),
    0x21257204: ('T**s Ass Drug Money', 'Reach the end of Chapter 2.'),
    0x13a0d6fb: ('Vice City, Baby!', 'Reach the end of Chapter 3.'),
    0x45cb3b4f: ('Top Of The World, Ma', 'Reach the end of Chapter 4.'),
    0x36399c2c: ('You Gotta Know When to Get Off', 'Finish the story finale.'),
    0xd88de0da: ('Trust', 'Finish Breakfast Run.'),
    0xcadb4575: ('Break the Bank', 'Finish The Cartel Heist.'),
    0xfd1ba9f1: ('Family Matters', 'Finish Child’s Play.'),
    0x3c690b8e: ('DWNFALL', 'Finish Headliners.'),
    0x2241d73c: ('Hi-Jacked', 'Finish VCIA Takedown.'),
    0xcabd2838: ('Snow Storm', 'Finish Operation Savage Glory.'),
    0x8b8e2c87: ('A Long Road', 'Fill the overall completion checklist to 100%.'),
    0xbf719465: ('Cunning Stunts', 'Finish 250 stunts.'),
    0x2778e472: ('Master of None', 'Take part in every activity type.'),
    0x15884091: ('The Shootist', 'Take gold in every shooting range challenge.'),
    0x62ebdb5b: ('Top Fun', 'Win a drone race at each Top Fun venue.'),
    0xf92507cb: ('Earn Cash, Not Kudos', 'Win races on 20 different courses.'),
    0x44ae9ee1: ('Baited My Tackle', 'Outfish Cal in a fishing challenge.'),
    0x71df7942: ('Stick Fiddler', 'Finish one arcade game.'),
    0xd6a01a0d: ('Road to Rehabilitation', 'Finish Andy’s mission strand.'),
    0x0918fefe: ('This Was No Boat Accident', 'Finish Kenton’s mission strand.'),
    0xea51c170: ('The Lone Rider', 'Finish Billy’s mission strand.'),
    0x69dc408b: ('Strangers & Freaks', 'Finish eight stranger mission strands.'),
    0x9c9825fe: ('Supply & Demand', 'Finish Randy’s mission strand.'),
    0x8dff08cc: ('Spin On This!', 'Finish Tyrone’s mission strand.'),
    0x8450c383: ('Positive Mental Attitude', 'Visit every meditation spot and meditate there.'),
    0xcbe6d2ae: ('Fair Game', 'Hunt one of Bret’s unique animals.'),
    0x6a1d0f1c: ("Don't Touch My Deck", 'Finish three full card collections.'),
    0xad7995d4: ('You WAiNKer!', 'Use WAiNK at 100 different places.'),
    0xdda87631: ('One Last Thing', 'Finish 50 challenges.'),
    0xdcaa0171: ('Hot Together', 'Escape a four-star pursuit with your partner.'),
    0x4be1dfe3: ('Retail Therapy', 'With your partner, rob three shops in one uninterrupted pursuit.'),
    0x39c83bb0: ('Whip It Good', 'Discover 100 different vehicles.'),
    0xb56d32f8: ('Gunslinger', 'Defeat five enemies during one Combat Focus use.'),
    0xa3730f04: ('Catch Me If You Can', 'Make an unscheduled flight out of VCIA.'),
    0x12ea6df1: ('Challenging Tank', 'Find and enter a Rhino tank.'),
    0x008ac932: ('Sneakthief', 'Finish a jewelry store robbery undetected.'),
    0x5c818122: ('Maximum Withdrawal', 'Escape after robbing five bank vaults.'),
    0xca205c52: ('A Classic Blitz Play', 'Take the loot from an armored truck and escape.'),
    0x713a950b: ('The Goodtime State', 'Explore Leonida in full.'),
    0xaa5d8750: ('Pest Control', 'Rob an illegal operation for each gang.'),
    0xb8672363: ('In The Beginning…', 'Enjoy the view with a cocktail at Ocean Beach in game.'),
    0xd5005c95: ('Capital Offense', 'Break out of a vehicle showroom.'),
    0xe2c2f81a: ('Let’s Go Bowling', 'Finish the special event at the Kolt & Associates bowling alley.'),
    0xd51b5cc7: ('Personal Best', 'Max out both partners’ Strength.'),
    0xe37df98c: ('Actions Speak Louder', 'Perform 500 actions affecting the criminal profile.'),
    0xf13a1508: ('Bad Luck, I Guess', 'As Lucia, revisit the prologue loan store solo and escape on foot.'),
    0x01f9b687: ('The Truth Is Out There', 'Complete the nighttime UFO encounter near Starlet Motel.'),
    0x37bca20c: ('Ten Pin', 'Get ten bike melee hits within one minute in game.'),
    0xbf0895b1: ('Dime on the Dollar', 'Launder marked bills for a total of $250,000 through contacts.'),
    0x04a5a0ce: ('Treat Yo Self', 'Spend a combined $100,000 in shops.'),
    0x72cdfd39: ('Little Boxes', 'Buy every garage property.'),
    0x25e86353: ('On the Spot', 'Register ten vehicles with Scooter Bros.'),
}


def records(text):
    selected = [r for r in ch._records(text) if r['set'] == SET_ID]
    if len(selected) != len(NAMES) or {r['id'] for r in selected} != NAMES.keys():
        raise fl.FeatureError('award_layout')
    for r in selected:
        members = fl.members(text, r['rec'][0])
        if len(members) != 4 or {k for k, _, _ in members} != ch.CHEAT_RECORD_KEYS:
            raise fl.FeatureError('award_layout')
        param = json.loads(text[slice(*r['param'])])
        if not isinstance(param, dict) or '$type' not in param:
            raise fl.FeatureError('award_layout')
    return {r['id']: r for r in selected}


def read(b):
    recs = records(fl.Save(b).text(ch.SEC))
    return [{'id': fl.hexid(i), 'name': name, 'condition': condition, 'done': recs[i]['done']} for i, (name, condition) in NAMES.items()]


def apply(b, choice):
    if not isinstance(choice, dict) or set(choice) != {'ids'}:
        raise fl.FeatureError('bad_request')
    requested = choice['ids']
    if not isinstance(requested, list) or not requested or not all(isinstance(x, str) for x in requested):
        raise fl.FeatureError('bad_request')
    ids = {i for i in NAMES if fl.hexid(i) in requested}
    if len(ids) != len(set(requested)):
        raise fl.FeatureError('unknown_challenge')
    save = fl.Save(b)
    text = save.text(ch.SEC)
    recs = records(text)
    targets = [recs[i] for i in NAMES if i in ids and not recs[i]['done']]
    if not targets:
        return b, []
    changes = [(r['done_span'], b'true') for r in targets]
    changes.extend((r['param'], ch.EMPTY_PARAM) for r in targets)
    for (a, z), value in sorted(changes, reverse=True):
        text = text[:a] + value + text[z:]
    after = records(text)
    if any(after[i]['done'] != (r['done'] or i in ids) for i, r in recs.items()):
        raise fl.FeatureError('verify_failed')
    save.set_text(ch.SEC, text)
    return save.build(), [{'what': 'award', 'label': NAMES[r['id']][0], 'id': fl.hexid(r['id'])} for r in targets]
