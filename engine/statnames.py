"""Known names for GTA VI stat keys.

The save stores stat names as joaat hashes. These names were recovered by hashing dictionary words and keeping
exact matches against the hashes in a real save, so they are hash-verified but can't be 100% certain.
INFERRED labels describe unnamed stats whose meaning was worked out from how their values change across saves.
"""

BASE_NAMES = (
    'accuracy', 'acquired', 'activity_distance_in', 'attempts', 'busted', 'carjackings', 'civilians_sp', 'completed',
    'cosmetics', 'deaths', 'destroyed', 'dismembered', 'dist', 'exploded', 'extractions', 'feed', 'fenced', 'found',
    'headshots', 'hits', 'holdups', 'kills', 'knockouts', 'looted', 'misses', 'pat', 'photographed', 'points',
    'praised', 'purchased', 'rank', 'robbed', 'scold', 'shots', 'started', 'stolen', 'studied', 'suicides', 'throws',
    'time', 'unlocked',
)

QUALIFIER_NAMES = (
    'accomplice', 'activities', 'adrenaline', 'advanced', 'aircraft', 'ajax', 'alcohol', 'all', 'ammo',
    'ammo_marksman', 'ammo_mg', 'ammo_minigun', 'ammo_molotov', 'ammo_pistol', 'ammo_revolver', 'ammo_rifle',
    'ammo_shotgun', 'ammo_smg', 'ammo_sniper', 'ammo_sporting', 'ammo_thrown_grenade', 'ammo_turret', 'animal',
    'animals', 'any', 'appearance', 'armed', 'armor', 'armour', 'arms', 'ascot', 'assault', 'atm', 'bar', 'barber',
    'basketball', 'beginner', 'bf', 'bicycle', 'bike', 'binoculars', 'bird', 'black', 'bleed', 'blue', 'boat',
    'bravado', 'brute', 'buck', 'buckme', 'burglary', 'busted', 'cafe', 'canoe', 'car', 'card', 'cardio', 'cash',
    'cctv', 'chest', 'cigarettes', 'cigars', 'civilian', 'clarion', 'clean', 'clothes', 'clothing', 'coil', 'coke',
    'collectibles', 'combat', 'cop', 'cover', 'crate', 'crest', 'criminal', 'critter', 'dances', 'dancing', 'dips',
    'doe', 'doubloons', 'drink', 'drown', 'enemies', 'enemy', 'eoaw', 'execution', 'exercise', 'exercising',
    'explosion', 'explosives', 'fall', 'fathom', 'fire', 'fish', 'flashlight', 'focus', 'food', 'grill', 'groin',
    'group_heavy', 'group_launcher', 'group_melee', 'group_pistol', 'group_revolver', 'group_rifle', 'group_shotgun',
    'group_smg', 'group_sniper', 'group_sports', 'group_stungun', 'group_thrown', 'gun', 'gut', 'hair', 'hands',
    'headphones', 'heads', 'headshot', 'health', 'healthy', 'heart', 'heli', 'hit', 'hulls', 'human', 'humans',
    'hungry', 'hvy', 'interest', 'intermediate', 'interstate', 'intimidation', 'inv_lenders', 'investment',
    'jailbreak', 'jogging', 'kidnapping', 'kills', 'kingfishers', 'knife', 'lapwing', 'law', 'lcc', 'legs', 'level1',
    'level2', 'level3', 'level4', 'level5', 'level6', 'looting', 'makeup', 'mammoth', 'masks', 'master', 'melee',
    'metaldetector', 'meteorites', 'military', 'minigun', 'misc', 'modshop', 'money', 'mtl', 'mugged', 'murder',
    'muscle', 'nails', 'obey', 'objects', 'ocelot', 'orange', 'osprey', 'outfits', 'packages', 'parachute', 'partner',
    'ped', 'pickups', 'piercings', 'plane', 'player', 'pocket', 'poison', 'pool', 'properties', 'rampage', 'red',
    'rentals', 'respawn', 'rifle', 'robberies', 'robbery', 'running', 'safe', 'seashark', 'secretly', 'shooting',
    'shop', 'shotgun', 'slotid_a_card', 'snacks', 'speeder', 'sports', 'sprinting', 'squat', 'stamina', 'stealth',
    'story', 'streak', 'styles', 'super', 'swat', 'swimming', 'taci', 'tank', 'tasks', 'tattoo', 'tattoos', 'taxis',
    'theft', 'threaten', 'throat', 'throwing', 'tickets', 'till', 'tipping', 'tired', 'tollbooth', 'total', 'train',
    'transport', 'travelled', 'treadmill', 'trespass', 'trophy', 'trunks', 'tuff', 'unaware', 'underwater',
    'unhealthy', 'vandalism', 'vape', 'vapid', 'vault', 'vehicle', 'vehicles', 'walking', 'wallet', 'wasted',
    'watercraft', 'weapon', 'weapons', 'weed', 'weight', 'western', 'xtrx', 'yellow', 'zenith',
)

OWNER_NAMES = (
    'air_gang', 'ambrosia', 'brian', 'downtown', 'dunk', 'griffin', 'hamlet', 'randy', 'raul', 'rob_death',
    'rob_drive',
)

# Unnamed base stats whose meaning was inferred from values across story saves (hash -> label).
INFERRED_BASE = {
    0xd3526971: 'completion %',
    0x845acae3: 'collected',
    0xdef0d42f: 'fitness level',
    0x53f5b035: 'fitness points',
    0xd5188146: 'money earned',
    0x60d17e5d: 'times wanted',
    0x4771a1ee: 'time wanted (ms)',
    0x348d8fa4: 'vehicle use',
    0x17ae107f: 'collected items',
}
# Qualifier used for whole-game totals of time and distance (unnamed).
INFERRED_QUALIFIER = {0xc357dc5a: 'overall'}
# Owner table: 0 is the game-wide total, 1 is Lucia, 2 is Jason (from wallet and wardrobe matches).
OWNER_LABELS = {0: 'Total', 1: 'Lucia', 2: 'Jason'}
