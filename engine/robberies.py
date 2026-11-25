"""Robbery lines of the 100% checklist: BANK JOBS / PAYDAY LOAN JOBS / SMASH 'N' GRABS / STICK UPS FULLY COMPLETED,
VAULTS HIT, and the Robberies page's CONVENIENCE STORES: LOCATIONS FULLY HIT (Save Garage feature module).

WHERE THE GAME KEEPS A LOCATION'S ROBBERY STATE (worked out from 20 saves; see research_notes/checklist-robberies.md)
  Per location: Discovery section 940e954d, list FlagState [{Name: location hash, StateFlags: int}]. Name is the same
  hash as the location's stats qualifier (robbed.<location>). For robbery locations the game uses these bits:
      0x80000  location hit (the first time anything there is robbed; set even without a hold-up)
      0x00080  location fully hit (everything robbable there taken)
      0x00200  cash registers taken      0x00400  safe taken      0x00800  vault taken
  Per type (stats 0635cbd9, owner story000, base 85209c63 = 'LOCATIONS FULLY HIT'):
      85209c63.<type qualifier>  = number of locations of the type whose flags have 0x80       (20 / 20 saves, 10 types)
      robbedtillsunique.<type>   = number with 0x200, robbedsafesunique.<type> = number with 0x400,
      robbedvaultsunique.<type>  = number with 0x800                                            (20 / 20 saves)
      85209c63 (no qualifier)    = number of locations with 0x80000, plus (from A1 on) 2 shops robbed in the story's
                                   stick-up montage that have no robbery bits (Hank's Waffles, Hamlet Thrift)  (20 / 20)
  The checklist counters (85209c63, owner story000):
      bankrobbery        = fleecabanklocations + lombankbankrobberylocations + shorefrontbankrobberylocations
                           + otherbankrobberylocations                      BANK JOBS FULLY COMPLETED  x / 22
      paydayloanrobbery  = paydayloanrobberylocations                       PAYDAY LOAN JOBS ...       x / 7
      smashngrabsrobbery = jewelrystorerobberylocations + pawnstorerobberylocations
                                                                            SMASH 'N' GRABS ...        x / 34
      holdupsrobbery     = stick ups: convenience and liquor stores count   STICK UPS ...              x / 50
      robbedvaultsunique (no qualifier) = sum of robbedvaultsunique.<type>  VAULTS HIT                 x / 8
      conveniencestorerobberylocations                  Robberies page, CONVENIENCE STORES: LOCATIONS FULLY HIT x / 72
  The first three sums hold in all 20 saves. Each line's cached percentage totalprogressmade.<line> is
  float32(min(n, total) / total) * 100 (checklist.py), and the overall figure is their weighted sum.

WHAT IT CHANGES (apply)
  For every chosen location (the default: all locations of the types behind the chosen lines):
    * Discovery FlagState: StateFlags |= 0x80080 (hit + fully hit), and | 0x800 for a chosen vault. A location with
      no FlagState entry gets one appended: {"Name": "0x<hash>", "StateFlags": 0x80080} (the exact value the game
      wrote for Jim's Mini Mart, a fully hit store with no register or safe bit). Existing bits are kept.
  Stats, by what changed (counters move by the number of locations newly flagged, so values edited earlier are kept):
    * 85209c63 (no qualifier) += locations newly given 0x80000;
    * 85209c63.<type> and its line counter (bankrobbery / paydayloanrobbery / smashngrabsrobbery / holdupsrobbery)
      += locations of that type newly given 0x80;
    * robbedvaultsunique.<bank type>, robbedvaultsunique, robbedvaults.<bank type>, robbedvaults += vaults newly
      given 0x800 (a vault hit is also a vault robbery: robbedvaults never falls below robbedvaultsunique in the saves);
    * totalprogressmade.bankrobbery / paydayloanrobbery / smashngrabsrobbery / holdupsrobbery / bankvaultrobbed =
      pct32(counter, total), then the overall figure through checklist.refresh_overall.
  Not changed: robbed.<location> and robbed.<type> (TOTAL ROBBERIES / ROBBERIES COMMITTED count hold-ups, and the
  game itself fully hit Globe Oil Food Center - Hamlet without one), cash (CASH STOLEN, TOTAL ROBBERY TAKE, the bank
  balance), the register/safe bits and their 'unique' counters, the Robbery section 3a4cbf5d (History, LocationRecords,
  KeyCodes), wanted level, heat and cooldowns, ScriptFlow, ScriptHeist, contacts and every other section.

EVIDENCE (game-written before -> after; the rules above hold in A0..A6c_as, B7as_a..B7b and the five edited saves)
  * A0 -> A1: Leonida Truck Stop FlagState - -> 0x80680, Jim's Mini Mart - -> 0x80080, Globe Oil Food Center - Hamlet
    - -> 0x80280 (robbed stays 0): CONVENIENCE STORES fully hit 2 -> 5. Fleeca - Ocean Beach (small) - -> 0x80680:
    fleeca 0 -> 1, BANK JOBS 0 -> 1; the other three banks got 0x80200 / 0x80200 / 0x80600 and no count. Donovan Banks
    & Co. - -> 0x80480 and Legendary Custom Jewelry - -> 0x80680 (Richardson - -> 0x80400 does not count): jewelry
    0 -> 2, SMASH 'N' GRABS 0 -> 2. 16 locations newly 0x80000 + the 2 montage shops: 85209c63 5 -> 23.
  * A1 -> A2: Peacock - -> 0x80680 (SMASH 2 -> 3), Quick Buck - Hamlet - -> 0x80680 (PAYDAY 0 -> 1); 23 -> 25.
  * A3 -> A4: two Payday Loans Stores - -> 0x80680 (PAYDAY 1 -> 3); 247 - Emerald Springs 0x80200 -> 0x80600 is a
    safe, not a full hit (convenience stays 5, robbedsafesunique.convenience 1 -> 2); 25 -> 27.
  * A4 -> A5: Lombank - Ocean Beach - -> 0x80e80: lombank 0 -> 1, BANK JOBS 1 -> 2, robbedvaultsunique(.lombank)
    0 -> 1 (VAULTS HIT 0 -> 1), robbedvaults(.lombank) +1; Fleeca - Downtown - -> 0x80400 and ICEGEM - -> 0x80000 are
    partial hits (no fully-hit count); 27 -> 30.
  * A5as -> A6as: ShoreFront - Rockridge - -> 0x80680 (BANK JOBS 2 -> 3), Fast Cash - -> 0x80480 (pawn 0 -> 1,
    SMASH 3 -> 4), Payday Loans Store - Little Cuba - -> 0x80680 (PAYDAY 3 -> 4); 30 -> 33.
  * Totals: the location table below has exactly 22 banks (the 22 'Large/Small bank ... dye pack jammer' locations)
    and 7 payday loan stores, matching the checklist; jewelry 20 + pawn 15 = 35 for SMASH 'N' GRABS x / 34 (which one
    the game leaves out is unknown); convenience 70 by description + 2 robbery-only stores of unknown type (Dutch
    Courage, Sugar Shack, marked 'inferred') = the Robberies page's 72.
  * Stick ups: A0 had holdupsrobbery 3 = convenience 2 + liquor 1, so both are stick-up types. In A0 -> A1 holdups went
    3 -> 7 (+4) while five candidates were newly fully hit (convenience +3, clothing +1, fast food +1); which one did
    not count (or whether a store looted without a hold-up counts: Globe Oil was fully hit with robbed = 0) is not
    settled. This module counts the convenience (and, if asked, liquor) stores it marks.

LIMITS / UNCERTAIN
  * Vaults: only 8 banks have a vault ('Some banks have vaults ... which can't be accessed yet'; vault jobs come as
    tips from Yasmani). The save does not say which. The one vault hit so far is in a large bank (Lombank - Ocean
    Beach); ShoreFront - Ocean Beach (large) had registers and safe taken and is still not fully hit, so it most likely
    has one; the two small banks that were fully hit had none. The default marks the vault of all 12 'Large bank'
    locations, so VAULTS HIT reads 12 and the screen should show 8 / 8 (it capped STANDARD ISSUE WEAPONS 54 at 50 / 50);
    up to 4 of those vault bits are then on banks without a vault. Pass choice['vaults'] = [bank ids] once the map's
    vault icons show the right 8.
  * Counters above the total: STICK UPS reads 74 (convenience only) and SMASH 'N' GRABS 35 after the default edit;
    the percentage rows cap at 100 and the screen is expected to cap the counter as it did for weapons.
  * FlagState grows by up to 136 entries (447 -> 555 in A6b with the defaults). The game's limit, if any, is unknown;
    a full playthrough must hold most of them.
  * No reward or loot: no cash, marked bills or jewelry is added, robbery counts and CASH STOLEN stay as they were,
    and the bank balance is untouched.

RISK: medium. Two sections, values the game itself writes; no story, mission, heist or Robbery-history state is touched.
Content gated on these counters (contact tips, Yasmani's bank jobs) might unlock at once; nothing here completes them.
"""
import json

import checklist
import featurelib as fl

FEATURE = 'robberies'
SEC_DISC = 0x940e954d                    # Discovery
K_FLAGSTATE, K_NAME, K_FLAGS = fl.key('FlagState'), fl.key('Name'), fl.key('StateFlags')
FULLYHIT = 0x85209c63                    # stats base behind 'LOCATIONS FULLY HIT' (name not cracked)
TP = 'totalprogressmade'
HIT, FULL, TILLS, SAFE, VAULT = 0x80000, 0x80, 0x200, 0x400, 0x800
NEW_FLAGS = HIT | FULL                   # 0x80080

# type: (stats qualifier, line counter qualifier, label)
TYPES = {
    'fleeca': ('fleecabanklocations', 'bankrobbery', 'Fleeca banks'),
    'lombank': ('lombankbankrobberylocations', 'bankrobbery', 'Lombanks'),
    'shorefront': ('shorefrontbankrobberylocations', 'bankrobbery', 'ShoreFront banks'),
    'otherbank': ('otherbankrobberylocations', 'bankrobbery', 'Other banks'),
    'payday': ('paydayloanrobberylocations', 'paydayloanrobbery', 'Payday loan stores'),
    'jewelry': ('jewelrystorerobberylocations', 'smashngrabsrobbery', 'Jewelry stores'),
    'pawn': ('pawnstorerobberylocations', 'smashngrabsrobbery', 'Pawn shops'),
    'convenience': ('conveniencestorerobberylocations', 'holdupsrobbery', 'Convenience stores'),
    'liquor': ('liquorstorerobberylocations', 'holdupsrobbery', 'Liquor stores'),
}
BANK_TYPES = ('fleeca', 'lombank', 'shorefront', 'otherbank')

# key: (label, total, counter (base, qualifier), percent qualifier or None, types, where it is shown)
LINES = {
    'bankjobs': ('BANK JOBS FULLY COMPLETED', 22, (FULLYHIT, 'bankrobbery'), 'bankrobbery', BANK_TYPES, '100% checklist'),
    'paydayloans': ('PAYDAY LOAN JOBS FULLY COMPLETED', 7, (FULLYHIT, 'paydayloanrobbery'), 'paydayloanrobbery', ('payday',), '100% checklist'),
    'smashngrabs': ("SMASH 'N' GRABS FULLY COMPLETED", 34, (FULLYHIT, 'smashngrabsrobbery'), 'smashngrabsrobbery', ('jewelry', 'pawn'), '100% checklist'),
    'stickups': ('STICK UPS FULLY COMPLETED', 50, (FULLYHIT, 'holdupsrobbery'), 'holdupsrobbery', ('convenience',), '100% checklist'),
    'vaults': ('VAULTS HIT', 8, ('robbedvaultsunique', 0), 'bankvaultrobbed', (), '100% checklist'),
    'convenience': ('CONVENIENCE STORES: LOCATIONS FULLY HIT', 72, (FULLYHIT, 'conveniencestorerobberylocations'), None, ('convenience',), 'Robberies page'),
}
LINE_ORDER = ('bankjobs', 'paydayloans', 'smashngrabs', 'stickups', 'vaults', 'convenience')

# (location hash = stats qualifier = FlagState Name, type, label, cracked qualifier name or None, flags)
# 'large' / 'small' from the game's own description of each bank; 'inferred' = type taken from the total (see above).
LOCATIONS = (
    (0xf11a988d, 'fleeca', 'Fleeca - Downtown', 'bank_dn_20_sg10608', ('large',)),
    (0x7766a407, 'fleeca', 'Fleeca - Key Lento', None, ('small',)),
    (0x2b180578, 'fleeca', 'Fleeca - Ocean Beach', 'bank_sb_17_sg8334', ('small',)),
    (0x6f955edd, 'fleeca', 'Fleeca - Ocean Beach', 'bank_sb_32_sg8335', ('large',)),
    (0x0c2f516b, 'fleeca', 'Fleeca - Peacock Bay', 'bank_ds_22_sg10610', ('large',)),
    (0x22c7ce5a, 'fleeca', 'Fleeca - Tequesta', 'bank_ds_09_sg8333', ('small',)),
    (0xb23735cd, 'fleeca', 'Fleeca - VCIA', 'bank_ss_29_sg10611', ('large',)),
    (0x1566072a, 'fleeca', 'Fleeca - Washington Beach', 'bank_nb_23_sg10606', ('large',)),
    (0x7e8e1a62, 'lombank', 'Lombank - Bayside', None, ('large',)),
    (0xc55cca6c, 'lombank', 'Lombank - Downtown', 'bank_dn_27_sg10875', ('large',)),
    (0x1dcac6d7, 'lombank', 'Lombank - Ocean Beach', 'bank_sb_47_sg11215', ('small',)),
    (0x4e0ef11d, 'lombank', 'Lombank - Ocean Beach', 'bank_sb_31_sg11197', ('large',)),
    (0xe9f95df9, 'lombank', 'Lombank - Ocean Beach', None, ('large',)),
    (0x9daaa2f6, 'lombank', 'Lombank - Peacock Bay', 'bank_ds_26_sg10927', ('small',)),
    (0xa1eac464, 'shorefront', 'ShoreFront - Ambrosia', 'bank_tw3_12_sg10616', ('small',)),
    (0x07b6e194, 'shorefront', 'ShoreFront - Downtown', 'bank_dn_25_sg10867', ('small',)),
    (0x03aa7058, 'shorefront', 'ShoreFront - Ocean Beach', 'bank_sb_47_sg10615', ('large',)),
    (0xe5ca5fc6, 'shorefront', 'ShoreFront - Ocean Beach', 'bank_sb_27_sg5522', ('small',)),
    (0x2b79e9b6, 'shorefront', 'ShoreFront - Rockridge', 'bank_sn_36_sg10609', ('small',)),
    (0xed362a35, 'shorefront', 'ShoreFront - Watson Bay', 'bank_tw7_12_sg10607', ('small',)),
    (0xa973392d, 'otherbank', 'Druthers State Bank', None, ('large',)),
    (0x9b0e2588, 'otherbank', 'Gibson Brothers Bank', None, ('large',)),
    (0xb0246bc1, 'payday', 'Cash Flow', 'loan_tw10_05e_sg10566', ()),
    (0xd5b94534, 'payday', 'Payday Loans Store - Little Cuba', 'loan_ss_10_sg11289', ()),
    (0xedde6d45, 'payday', 'Payday Loans Store - Rockridge', 'loan_sn_29_sg11266', ()),
    (0xbf67d280, 'payday', 'Payday Loans Store - Southside', 'loan_ss_60_sg11340', ()),
    (0x0f8eecb0, 'payday', 'Payline Loans 247', None, ()),
    (0xf81da5ed, 'payday', 'Quick Buck - Hamlet', 'loan_tw2_24_sg11419', ()),
    (0xc3119f9e, 'payday', 'Quick Buck - La Perle', 'loan_sn_08_sg11241', ()),
    (0xbecb39d8, 'jewelry', 'All That Glitters', 'jewelry_dn_05b_sg10829', ()),
    (0x58cf004b, 'jewelry', 'Ayoka Jewelers', None, ()),
    (0x0179139d, 'jewelry', 'Blanc & Giroux', 'jewelry_nm_01b_sg11097', ()),
    (0xffb6d4a4, 'jewelry', 'Brilliant Cuts', 'jewelry_tw5_06_sg11463', ()),
    (0x89602855, 'jewelry', 'Covgari', 'jewelry_nm_02_sg11100', ()),
    (0x47cc4c94, 'jewelry', 'Crown Jewels', 'jewelry_id_23c_sg79859', ()),
    (0xcbac4a98, 'jewelry', 'Donovan Banks & Co.', 'jewelry_ds_23_sg10926', ()),
    (0xb349f375, 'jewelry', 'ICEGEM Diamonds & Watches', 'jewelry_dn_21_sg10862', ()),
    (0x16ac21b3, 'jewelry', 'Kowalski', 'jewelry_nb_lel_02_sg11049', ()),
    (0x32ebec61, 'jewelry', 'Legendary Custom Jewelry', 'jewelry_sb_27_sg5515', ()),
    (0x66a032cd, 'jewelry', "Marshal's", 'jewelry_nb_57_sg11089', ()),
    (0xcaa6518e, 'jewelry', 'Peacock', 'jewelry_dn_05b_sg10828', ()),
    (0xbc9492c2, 'jewelry', 'Plush', 'jewelry_ds_09_sg10905', ()),
    (0x6a9ef610, 'jewelry', 'Richardson Jewelry & Diamonds', 'jewelry_dn_20_sg10855', ()),
    (0xf9dbbf07, 'jewelry', 'Rococo Rich', 'jewelry_sb_11_sg11168', ()),
    (0x428c8127, 'jewelry', 'Roval Jewelry', 'jewelry_nm_02_sg11099', ()),
    (0x827f773c, 'jewelry', 'Skala', 'jewelry_nb_lel_02_sg11063', ()),
    (0xdf2db5c7, 'jewelry', 'The Jewelry Place', 'jewelry_id_23c_sg79910', ()),
    (0xa392952e, 'jewelry', "The Siren's Chest", 'jewelry_ky_24_sg10996', ()),
    (0xf96c2437, 'jewelry', 'Victoria Lee Jeweler', 'jewelry_tw4_21_sg11453', ()),
    (0x623f0093, 'pawn', 'Avery Pawn', 'pawn_tw10_05e_sg10560', ()),
    (0xb57115fe, 'pawn', "Buck's Jewelry & Pawn", 'pawn_tw10_02c_sg10564', ()),
    (0x76ec4459, 'pawn', 'Casa de Empeño', 'pawn_sb_03_sg11161', ()),
    (0x37e744ca, 'pawn', 'Dorado Pawn Shop', 'pawn_sn_44_sg11279', ()),
    (0x2d638f9a, 'pawn', 'Down Town Pawn', 'pawn_nm_24_sg11138', ()),
    (0xe5454bee, 'pawn', "Ernesto's Pawn", 'pawn_ss_60_sg11341', ()),
    (0xd28cd5fa, 'pawn', 'Fast Cash', None, ()),
    (0xb2660dd9, 'pawn', 'Florence & Co.', None, ()),
    (0x21d99007, 'pawn', 'Hamlet Pawn', 'pawn_tw2_24_sg11420', ()),
    (0xe88ce2b2, 'pawn', 'Joyeria Empeños', 'pawn_ss_67_sg11345', ()),
    (0x77f44c32, 'pawn', 'Pawn City', 'pawn_ss_31_sg11310', ()),
    (0x3f25767f, 'pawn', 'Pawn Stash', 'pawn_sn_08_sg11240', ()),
    (0x20d8b5db, 'pawn', 'Timeless Peculiars', 'pawn_tw7_19_sg11491', ()),
    (0xffe1c6ce, 'pawn', 'Vice City Pawn', 'pawn_nm_19_sg11134', ()),
    (0x4d08abbc, 'pawn', 'White Sand Jewelry Pawn', 'pawn_sn_27_sg11265', ()),
    (0x59124834, 'convenience', '247 - Bayside', 'convenience_nm_08_sg11118', ()),
    (0xe60a0b3d, 'convenience', '247 - Belville', 'convenience_lo_spl_07_sg81513', ()),
    (0x0bab32ce, 'convenience', '247 - Downtown', 'convenience_dn_11_sg10842', ()),
    (0x45bb24f9, 'convenience', '247 - Emerald Springs', 'convenience_lo_orc_02_sg10713', ()),
    (0x31211e9a, 'convenience', '247 - Hamlet', 'convenience_tw2_10_sg10711', ()),
    (0xaee411c4, 'convenience', '247 - Key Lento', 'convenience_ky_28_sg10999', ()),
    (0x02ac6134, 'convenience', '247 - Millport', 'convenience_nb_tpk_05_sg70889', ()),
    (0x6b1d9c99, 'convenience', '247 - Ocean Beach', None, ()),
    (0xffb926cb, 'convenience', '247 - Port Gellhorn', 'convenience_tw10_04_sg10553', ()),
    (0xcb1a5297, 'convenience', '247 - Waning Sands', 'convenience_nb_lel_01_sg81524', ()),
    (0xb250c982, 'convenience', '247 - Washington Beach', 'convenience_nb_02_sg11066', ()),
    (0x2b95adf0, 'convenience', '247 - West Kalaga', 'convenience_fh_shl_05_sg84236', ()),
    (0xfaec63b5, 'convenience', '247 - West Vice-Dale County', 'convenience_ma_cnw_02_sg10715', ()),
    (0x779f8d42, 'convenience', 'Alpha Convenience Store - Belville', 'convenience_tw5_12b_sg81520', ()),
    (0xb1b87b00, 'convenience', 'Alpha Convenience Store - Gellhorn', 'convenience_lo_int1_02_sg13176', ()),
    (0xf2f92fff, 'convenience', 'Blessed Food Market', 'convenience_sn_20_sg11257', ()),
    (0xd62ec2ce, 'convenience', 'Bunch Farms Country Store', None, ()),
    (0x22a6e5a1, 'convenience', 'Cane Grocery', 'convenience_tw3_12_sg10712', ()),
    (0xd146b65b, 'convenience', "Dale's Shopwell", None, ()),
    (0xd8e7cb0b, 'convenience', 'Delgado & Sons', 'convenience_id_20_sg10959', ()),
    (0x69fddb54, 'convenience', 'Eager Beaver Express', None, ()),
    (0x90c3765c, 'convenience', 'Emerald Springs Country Store', None, ()),
    (0x9adfda57, 'convenience', "Emilio's Auto Center Food Store", 'convenience_sn_44_sg11278', ()),
    (0x975d27c5, 'convenience', 'Globe Oil Food Center - Crosstown', 'convenience_nm_36_sg10719', ()),
    (0xd55baccd, 'convenience', 'Globe Oil Food Center - Hamlet', 'convenience_tw2_11_sg10726', ()),
    (0x4ce53748, 'convenience', "Huck's Pump N Go", 'convenience_fh_shl_01_sg70901', ()),
    (0xc79987f5, 'convenience', "Hugo's Quick-Mart", 'convenience_sn_35_sg11270', ()),
    (0x63149819, 'convenience', "Jim's Mini Mart", 'convenience_tw7_08_sg11479', ()),
    (0x4647837b, 'convenience', 'LTD Food Mart - Capri', 'convenience_tw4_14_sg10727', ()),
    (0x9b4c698d, 'convenience', 'LTD Food Mart - Hamlet', 'convenience_tw2_05_sg10725', ()),
    (0x6f2e2636, 'convenience', 'LTD Food Mart - Ocean Beach', 'convenience_sb_31_sg11198', ()),
    (0x5ff9fcd3, 'convenience', 'Leonida Key Lento Mini Mart', 'convenience_ky_46_sg11013', ()),
    (0x9d630954, 'convenience', 'Leonida Truck Stop', 'convenience_tw2_03_sg10724', ()),
    (0x7f6f79ad, 'convenience', 'Poppers Convenience Store', 'convenience_tw7_18_sg11487', ()),
    (0x440c291e, 'convenience', 'Quick Picks Mini Mart', 'convenience_dn_25_sg10870', ()),
    (0x4b7f9792, 'convenience', "RON Stop'N'Snack - Balsero", 'convenience_id_25_sg10971', ()),
    (0xa8f78a48, 'convenience', "RON Stop'N'Snack - Balsero", 'convenience_id_23e_sg10970', ()),
    (0x59e19801, 'convenience', "RON Stop'N'Snack - Bayside", 'convenience_nm_06b_sg10717', ()),
    (0xc7abe44a, 'convenience', "RON Stop'N'Snack - Little Cuba", 'convenience_ss_16_sg11293', ()),
    (0xdeaf37ba, 'convenience', "RON Stop'N'Snack - Salton", 'convenience_ss_03_sg10722', ()),
    (0x79eca914, 'convenience', "RON Stop'N'Snack - Southside", 'convenience_ss_56_sg10723', ()),
    (0xd9e40fe7, 'convenience', "RON Stop'N'Snack - Washington Beach", 'convenience_nb_25_sg11082', ()),
    (0x590f5f17, 'convenience', "Ramon's Groceries", 'convenience_tw2_06_sg11397', ()),
    (0xaa369fcc, 'convenience', "Randy's Big Gas Mart", 'convenience_tw7_19_sg11489', ()),
    (0xb4138891, 'convenience', "Redshaw's General Store", None, ()),
    (0x2e364eaa, 'convenience', "Rico's Convenience Store", 'convenience_sn_37_sg11274', ()),
    (0x863e76c7, 'convenience', 'Righto Cash & Carry', None, ()),
    (0xef5c3bd1, 'convenience', "Trotman's Supermarket", 'convenience_nb_nrb_01_sg70898', ()),
    (0x73d254b9, 'convenience', "Tucker's Citrus Farms", 'convenience_lo_orc_01_sg13770', ()),
    (0xaa24df40, 'convenience', 'Vetiver Minimarket', 'convenience_sn_17_sg11250', ()),
    (0x76e8aa7a, 'convenience', 'Wells Rosa', 'convenience_ds_27_sg10928', ()),
    (0x65689e79, 'convenience', 'XYZ Market', 'convenience_nm_24_sg11137', ()),
    (0x59e0db98, 'convenience', 'Xero Food Mart - Ambrosia', 'convenience_tw3_14_sg11435', ()),
    (0xf3c726b7, 'convenience', 'Xero Food Mart - Belville', 'convenience_lo_spl_07_sg81512', ()),
    (0x7563e914, 'convenience', 'Xero Food Mart - Buckskin Swamp', None, ()),
    (0xcf3fa435, 'convenience', 'Xero Food Mart - Buckskin Swamp', None, ()),
    (0x1bbcb6f3, 'convenience', 'Xero Food Mart - Capri', 'convenience_tw4_31_sg11460', ()),
    (0xba991f38, 'convenience', 'Xero Food Mart - Crosstown', 'convenience_nm_19_sg10718', ()),
    (0x1d4eb308, 'convenience', 'Xero Food Mart - Grassrivers', 'convenience_ma_mar_05_sg11031', ()),
    (0xb36c8845, 'convenience', 'Xero Food Mart - Grassrivers', 'convenience_ma_mar_04_sg10716', ()),
    (0x16942e4a, 'convenience', 'Xero Food Mart - La Perle', 'convenience_sn_02_sg10720', ()),
    (0xd1c33c01, 'convenience', 'Xero Food Mart - Millport', 'convenience_nb_nrb_01_sg80004', ()),
    (0x242b298c, 'convenience', 'Xero Food Mart - Rockridge', 'convenience_sn_28_sg10721', ()),
    (0x83fed7a1, 'convenience', 'Xero Food Mart - Salton', 'convenience_ss_18_sg11294', ()),
    (0x8c147a96, 'convenience', 'Xero Food Mart - South Kelly County', 'convenience_ma_cfm_02_sg10714', ()),
    (0xd6034104, 'convenience', 'Xero Food Mart - Southside', None, ()),
    (0x5dbc7382, 'convenience', 'Xero Food Mart - Southwind', 'convenience_tr_abi_02_sg94026', ()),
    (0xec919f83, 'convenience', 'Xero Food Mart - Tequesta', 'convenience_ds_01_sg10888', ()),
    (0xdfb782a4, 'convenience', 'Xero Food Mart - Waning Sands', None, ()),
    (0x16703b0b, 'convenience', '¡Superprecios! Market', 'convenience_sb_33_sg11200', ()),
    (0xcbcf59dd, 'convenience', 'Dutch Courage', None, ('inferred',)),
    (0xed282625, 'convenience', 'Sugar Shack', None, ('inferred',)),
    (0xe84c867e, 'liquor', 'Ambrosia Liquors', 'liquor_tw3_06_sg10730', ()),
    (0xc36b9e22, 'liquor', 'Corked Wine Bank', 'liquor_sb_49_sg11220', ()),
    (0xada38d42, 'liquor', 'Discount Liquors', 'liquor_ss_68_sg11347', ()),
    (0x66766cdb, 'liquor', 'Liquor Store', None, ()),
    (0x7927fc97, 'liquor', 'Ocean Beach Liquor', None, ()),
    (0x7ce0aade, 'liquor', 'One Stop Liquor - Key Lento', 'liquor_ky_23_sg10994', ()),
    (0x03040242, 'liquor', 'One Stop Liquor - Ocean Beach', 'liquor_sb_47_sg11217', ()),
    (0x74b5f13b, 'liquor', 'Palmis Liquor', None, ()),
    (0xa6bc8c2f, 'liquor', 'Three Sheets Liquor', None, ()),
    (0xd51cefaa, 'liquor', "Uncle Jack's Liquor - Bayside", None, ()),
    (0x6f11c9d9, 'liquor', "Uncle Jack's Liquor - Port Gellhorn", 'liquor_tw10_05e_sg10601', ()),
    (0x75489175, 'liquor', "Uncle Jack's Liquor - Tequesta", 'liquor_ds_05_sg10896', ()),
    (0xd8d1e843, 'liquor', "Zak's Liquor", 'liquor_sn_05_sg11236', ()),
)
BY_ID = {x[0]: x for x in LOCATIONS}
BANK_IDS = tuple(x[0] for x in LOCATIONS if x[1] in BANK_TYPES)
LARGE_BANKS = tuple(x[0] for x in LOCATIONS if x[1] in BANK_TYPES and 'large' in x[4])


# ---------------------------------------------------------------- FlagState (Discovery section)
def _hex_data(t, s):
    for k, a, z in fl.members(t, s):
        if k == '$data':
            return int(t[a + 1:z - 1], 16) & fl.M32
    raise fl.FeatureError('layout_changed')


def _flagstate(t):
    """(array_start, array_end, {name hash: (flags_start, flags_end, value)}) of Discovery FlagState."""
    s, e = fl.walk(t, fl.CODE, fl.key(SEC_DISC), K_FLAGSTATE)
    if t[s] != ord('['):
        raise fl.FeatureError('layout_changed')
    out = {}
    for a, z in fl.elements(t, s):
        mem = {k: (x, y) for k, x, y in fl.members(t, a)}
        if K_NAME not in mem or K_FLAGS not in mem or t[mem[K_NAME][0]] != ord('{'):
            raise fl.FeatureError('layout_changed')
        name = _hex_data(t, mem[K_NAME][0])
        fs, fe = mem[K_FLAGS]
        tok = t[fs:fe]
        if not tok.isdigit() or name in out:
            raise fl.FeatureError('layout_changed')
        out[name] = (fs, fe, int(tok))
    return s, e, out


def _entry(h, flags):
    return b'{"%s":{"$data":"0x%08x"},"%s":%d}' % (K_NAME.encode(), h, K_FLAGS.encode(), flags)


# ---------------------------------------------------------------- read
def _line_state(st, key):
    label, total, (base, qual), pq, _, where = LINES[key]
    value = st.value(base, qual)
    pct = st.value(TP, pq) if pq else None
    return {'key': key, 'label': label, 'value': value, 'of': total, 'shown': None if value is None else min(value, total),
            'percent': pct, 'percentRow': ('%s.%s' % (TP, pq)) if pq else None,
            'percentConsistent': None if pq is None or pct is None or value is None else abs(pct - fl.pct32(value, total)) <= 2e-6,
            'done': value is not None and value >= total, 'where': where}


def read(b):
    s = fl.Save(b)
    st = fl.Stats(s.text(fl.STATS))
    _, _, fs = _flagstate(s.text(SEC_DISC))
    locs = []
    for h, typ, label, name, flags in LOCATIONS:
        f = fs.get(h)
        locs.append({'id': fl.hexid(h), 'label': label, 'type': typ, 'name': name, 'inferred': 'inferred' in flags,
                     'size': 'large' if 'large' in flags else 'small' if 'small' in flags else None,
                     'flags': None if f is None else '0x%x' % f[2], 'hit': bool(f and f[2] & HIT), 'fullyHit': bool(f and f[2] & FULL),
                     'registers': bool(f and f[2] & TILLS), 'safe': bool(f and f[2] & SAFE), 'vault': bool(f and f[2] & VAULT),
                     'robberies': st.value('robbed', h)})
    types = []
    for typ, (q, line_q, label) in TYPES.items():
        mine = [x for x in locs if x['type'] == typ]
        full = sum(1 for x in mine if x['fullyHit'])
        counter = st.value(FULLYHIT, q)
        row = {'type': typ, 'label': label, 'locations': len(mine), 'fullyHit': full, 'counter': counter,
               'consistent': counter == full, 'lineCounter': line_q}
        if typ in BANK_TYPES:
            vb = sum(1 for x in mine if x['vault'])
            vc = st.value('robbedvaultsunique', q)
            row.update({'vaultsHit': vb, 'vaultCounter': vc, 'vaultConsistent': vc == vb})
        types.append(row)
    hit_bits = sum(1 for _, _, v in fs.values() if v & HIT)
    all_counter = st.value(FULLYHIT, 0)
    lines = [_line_state(st, k) for k in LINE_ORDER]
    return {'feature': FEATURE, 'lines': lines, 'types': types,
            'locationsHit': {'counter': all_counter, 'flagged': hit_bits,
                             'offset': None if all_counter is None else all_counter - hit_bits},
            'locations': locs, 'largeBanks': [fl.hexid(h) for h in LARGE_BANKS],
            'flagStateEntries': len(fs), 'overall': st.value(*checklist.OVERALL),
            'possible': [x['key'] for x in lines if not x['done']],
            'risk': 'medium',
            'notes': ['Marks robbery locations fully hit the way the game records it (Discovery FlagState bits 0x80000 and 0x80) '
                      'and moves the per-type and checklist counters, the 100% rows and the overall figure by the same amount.',
                      'No cash, loot, robbery count or CASH STOLEN is added; wanted level, heat and cooldowns are not touched.',
                      'Only 8 banks have a vault and the save does not say which; by default the 12 large banks get their vault marked '
                      '(VAULTS HIT then reads 12 and should show 8 / 8).',
                      'STICK UPS and SMASH \'N\' GRABS end above their totals (74 / 50, 35 / 34); the percentages cap at 100.']}


# ---------------------------------------------------------------- apply
def _ids(x, allowed, code):
    if isinstance(x, (str, bytes)) or not hasattr(x, '__iter__'):
        raise fl.FeatureError('bad_request')
    out = []
    for v in x:
        h = fl.h(v if isinstance(v, int) else ('0x' + v if not str(v).lower().startswith('0x') else v))
        if h not in allowed:
            raise fl.FeatureError(code)
        out.append(h)
    return list(dict.fromkeys(out))


def targets(choice):
    """(locations to mark fully hit, banks to mark vault hit) for a choice; see apply()."""
    choice = choice or {}
    if 'locations' in choice:
        full = _ids(choice['locations'], BY_ID, 'unknown_location')
        v = choice.get('vaults', 'none')
        if v in (None, 'none'):
            vault = []
        elif v == 'large':
            vault = list(LARGE_BANKS)
        else:
            vault = _ids(v, BANK_IDS, 'unknown_bank')
        return full, vault
    vaults = choice.get('vaults', 'large')
    lines = choice.get('lines', 'all')
    if lines == 'all':
        lines = list(LINE_ORDER)
    elif isinstance(lines, (str, bytes)) or not hasattr(lines, '__iter__') or set(lines) - set(LINE_ORDER):
        raise fl.FeatureError('unknown_line')
    stick = choice.get('stickups', 'convenience')
    if stick not in ('convenience', 'convenience_liquor'):
        raise fl.FeatureError('bad_request')
    types = set()
    for k in lines:
        types |= set(LINES[k][4])
    if 'stickups' in lines and stick == 'convenience_liquor':
        types.add('liquor')
    full = [x[0] for x in LOCATIONS if x[1] in types]
    vault = []
    if 'vaults' in lines:
        if vaults == 'large':
            vault = list(LARGE_BANKS)
        elif vaults in (None, 'none'):
            raise fl.FeatureError('bad_request')            # the VAULTS HIT line was asked for with no vaults
        else:
            vault = _ids(vaults, BANK_IDS, 'unknown_bank')
    return full, vault


def apply(b, choice=None):
    """choice (all optional):
         'lines':     'all' (default) or a list of 'bankjobs', 'paydayloans', 'smashngrabs', 'stickups', 'vaults', 'convenience';
         'stickups':  'convenience' (default) or 'convenience_liquor' (also mark the 13 liquor stores);
         'vaults':    'large' (default: the 12 large banks), 'none', or a list of bank ids;
         'locations': a list of location ids to mark fully hit instead of whole lines (vaults only if 'vaults' is given).
       -> (new bytes, log). Unchanged bytes when everything chosen is already marked."""
    full, vault = targets(choice)
    s = fl.Save(b)
    t = s.text(SEC_DISC)
    _, arr_e, fs = _flagstate(t)
    want = {}
    for h in full:
        want[h] = want.get(h, 0) | NEW_FLAGS
    for h in vault:
        want[h] = want.get(h, 0) | HIT | VAULT
    st = fl.Stats(s.text(fl.STATS))
    new_hit, new_full, new_vault, edits, appends, log = 0, {}, {}, [], [], []
    for h, typ, label, _, _ in LOCATIONS:              # table order keeps the output deterministic
        if h not in want:
            continue
        old = fs[h][2] if h in fs else None
        cur = old or 0
        nv = cur | want[h]
        if nv == cur and old is not None:
            continue
        if not cur & HIT:
            new_hit += 1
        if nv & FULL and not cur & FULL:
            new_full[typ] = new_full.get(typ, 0) + 1
        if nv & VAULT and not cur & VAULT:
            new_vault[typ] = new_vault.get(typ, 0) + 1
        if old is None:
            appends.append(_entry(h, nv))
        else:
            edits.append((fs[h][0], fs[h][1], b'%d' % nv))
        log.append({'what': 'location', 'id': fl.hexid(h), 'label': label, 'type': typ,
                    'from': None if old is None else '0x%x' % old, 'to': '0x%x' % nv})
    if not log:
        return b, []

    def bump(base, qual, n, label):
        cur = st.value(base, qual)
        if cur is None:
            raise fl.FeatureError('layout_changed')
        st.set(base, qual, cur + n, label)
        return cur + n

    if new_hit:
        bump(FULLYHIT, 0, new_hit, 'Robbery locations hit')
    line_n = {}
    for typ, n in new_full.items():
        q, line_q, label = TYPES[typ]
        bump(FULLYHIT, q, n, '%s: locations fully hit' % label)
        line_n[line_q] = line_n.get(line_q, 0) + n
    for line_q, n in line_n.items():
        bump(FULLYHIT, line_q, n, 'Locations fully hit: %s' % line_q)
    if new_vault:
        for typ, n in new_vault.items():
            q = TYPES[typ][0]
            bump('robbedvaultsunique', q, n, '%s: vaults hit' % TYPES[typ][2])
            bump('robbedvaults', q, n, '%s: vaults robbed' % TYPES[typ][2])
        total = sum(new_vault.values())
        bump('robbedvaultsunique', 0, total, 'Vaults hit')
        bump('robbedvaults', 0, total, 'Vaults robbed')
    for key in LINE_ORDER:                                  # cached 100% rows of the checklist lines
        label, of, (base, qual), pq, _, _ = LINES[key]
        if pq is None:
            continue
        cnt = st.value(base, qual)
        if st.row(TP, pq) is None or cnt is None:
            raise fl.FeatureError('layout_changed')
        st.set(TP, pq, fl.pct32(cnt, of), '%s, part of 100%% completion' % label.capitalize())
    checklist.refresh_overall(st)

    # Discovery text: flag tokens in place, new entries appended; applied from the end backwards
    if appends:
        close = arr_e - 1                                   # index of ']'
        joined = b','.join(appends)
        edits.append((close, close, (b',' + joined) if fs else joined))
    edits.sort(key=lambda x: -x[0])
    last = len(t) + 1
    for a, z, new in edits:
        if z > last:
            raise fl.FeatureError('layout_changed')
        t = t[:a] + new + t[z:]
        last = a
    json.loads(t)
    s.set_text(SEC_DISC, t)
    txt, slog = st.apply()
    s.set_text(fl.STATS, txt)
    return s.build(), log + slog
