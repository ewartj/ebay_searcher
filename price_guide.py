"""
Black Library Price Guide — UK secondary market values (GBP).

Keys are lowercase substrings matched against listing titles (case-insensitive).

Three formats supported:

    # Hardback price only (most entries):
    "horus rising": 30.0,

    # Separate hardback and paperback prices:
    "eisenhorn": {"hardback": 50.0, "paperback": 25.0},

    # Paperback only (e.g. titles only released in PB):
    "some title": {"paperback": 15.0},

If a listing is a paperback and only a hardback price exists, it goes to Claude
for pricing instead so valuable omnibuses still get a fair estimate.
"""
from typing import TypedDict


class PriceEntry(TypedDict, total=False):
    hardback: float
    paperback: float


# Type alias — each entry is either a plain float (hardback) or a PriceEntry dict
Entry = float | PriceEntry

PRICE_GUIDE: dict[str, Entry] = {

    # -------------------------------------------------------------------------
    # Horus Heresy — Main Series
    # -------------------------------------------------------------------------
    "horus rising":                  {"hardback": 20.0, "paperback": 5.0},
    "false gods":                    {"hardback": 28.0, "paperback": 5.0},
    "galaxy in flames":              {"hardback": 28.0, "paperback": 5.0},
    "flight of the eisenstein":      {"hardback": 28.0, "paperback": 5.0},
    "fulgrim":                       {"hardback": 35.0, "paperback": 5.0},
    "descent of angels":             {"hardback": 25.0, "paperback": 7.0},
    "horus heresy: legion":          {"hardback": 40.0, "paperback": 25.0},
    "battle for the abyss":          {"hardback": 22.0, "paperback": 18.0},
    "mechanicum":                    {"hardback": 35.0, "paperback": 20.0},
    "tales of heresy":               {"hardback": 25.0, "paperback": 20.0},
    "fallen angels":                 {"hardback": 25.0, "paperback": 18.0},
    "legion abnett":                 {"hardback": 25.0, "paperback": 15.0},
    "a thousand sons":               {"hardback": 40.0, "paperback": 15.0},
    "nemesis":                       {"hardback": 30.0, "paperback": 7.0},
    "the first heretic":             {"hardback": 15.0, "paperback": 5.0},
    "prospero burns":                {"hardback": 40.0, "paperback": 9.0},
    "horus heresy age of darkness":  {"hardback": 28.0, "paperback": 11.0},
    "the outcast dead":              {"hardback": 28.0, "paperback": 7.0},
    "deliverance lost":              {"hardback": 28.0, "paperback": 22.0},
    "know no fear":                  {"hardback": 40.0, "paperback": 9.0},
    "the primarchs":                 {"hardback": 35.0, "paperback": 8.0},
    "fear to tread":                 {"hardback": 35.0, "paperback": 8.0},
    "shadows of treachery":          {"hardback": 28.0, "paperback": 7.0},
    "angel exterminatus":            {"hardback": 35.0, "paperback": 8.0},
    "betrayer":                      {"hardback": 40.0, "paperback": 10.0},
    "mark of calth":                 {"hardback": 28.0, "paperback": 20.0},
    "vulkan lives":                  {"hardback": 28.0, "paperback": 7.0},
    "the unremembered empire":       {"hardback": 35.0, "paperback": 8.0},
    "vengeful spirit":               {"hardback": 35.0, "paperback": 8.0},
    "the damnation of pythos":       {"hardback": 22.0, "paperback": 18.0},
    "legacies of betrayal":          {"hardback": 30.0, "paperback": 7.0},
    "deathfire":                     {"hardback": 28.0, "paperback": 7.0},
    "war without end":               {"hardback": 28.0, "paperback": 7.0},
    "master of mankind":             {"hardback": 45.0, "paperback": 10.0},
    "garro":                         {"hardback": 35.0, "paperback": 8.0},
    "shattered legions":             {"hardback": 28.0, "paperback": 7.0},
    "the crimson king":              {"hardback": 38.0, "paperback": 9.0},
    "tallarn":                       {"hardback": 28.0, "paperback": 7.0},
    "ruinstorm":                     {"hardback": 35.0, "paperback": 8.0},
    "old earth":                     {"hardback": 28.0, "paperback": 7.0},
    "the burden of loyalty":         {"hardback": 28.0, "paperback": 7.0},
    "wolfsbane":                     {"hardback": 35.0, "paperback": 8.0},
    "born of flame":                 {"hardback": 28.0, "paperback": 7.0},
    "slaves to darkness":            {"hardback": 35.0, "paperback": 8.0},
    "malevolence":                   {"hardback": 35.0, "paperback": 8.0},
    "lost and the damned":           {"hardback": 40.0, "paperback": 9.0},
    "first wall":                    {"hardback": 40.0, "paperback": 9.0},
    "solar war":                     {"hardback": 45.0, "paperback": 8.0},
    "saturnine":                     {"hardback": 55.0, "paperback": 12.0},
    "mortis":                        {"hardback": 45.0, "paperback": 10.0},
    "warhawk":                       {"hardback": 40.0, "paperback": 9.0},
    "echoes of eternity":            {"hardback": 40.0, "paperback": 9.0},
    "end and the death":             {"hardback": 55.0, "paperback": 12.0},
    "promethian sun":             {"hardback": 30.0, "paperback": 12.0},

    # -------------------------------------------------------------------------
    # Siege of Terra
    # -------------------------------------------------------------------------
    "siege of terra":    45.0,
    "ghost of terra":    45.0,

    # -------------------------------------------------------------------------
    # Horus Heresy — Primarchs Series
    # -------------------------------------------------------------------------
    "roboute guilliman":          35.0,
    "leman russ: the great wolf": 35.0,
    "magnus the red":             40.0,
    "perturabo":                  35.0,
    "lorgar: bearer of the word": 35.0,
    "konrad curze":               40.0,
    "jaghatai khan":              35.0,
    "corvus corax":               35.0,
    "alpharius: head of the hydra": 40.0,
    "lion el'jonson":             40.0,
    "rogal dorn":                 35.0,
    "ferrus manus":               35.0,
    "vulkan: lord of drakes":     35.0,
    "mortarion":                  40.0,
    "sanguinius: the great angel": 45.0,
    "the seventh serpent": 40.0,

    # -------------------------------------------------------------------------
    # Eisenhorn / Ravenor / Bequin — omnibus PBs are valuable
    # -------------------------------------------------------------------------
    "eisenhorn":       {"hardback": 50.0, "paperback": 25.0},
    "ravenor rogue":   {"hardback": 40.0, "paperback": 12.0},
    "ravenor returned":{"hardback": 38.0, "paperback": 12.0},
    "ravenor":         {"hardback": 40.0, "paperback": 20.0},
    "pariah":          {"hardback": 35.0, "paperback": 10.0},
    "penitent":        {"hardback": 35.0, "paperback": 10.0},
    "bequin":          {"hardback": 35.0, "paperback": 10.0},

    # -------------------------------------------------------------------------
    # Gaunt's Ghosts — omnibus PBs sell well
    # -------------------------------------------------------------------------
    "first and only":        {"hardback": 30.0, "paperback": 8.0},
    "ghostmaker":            {"hardback": 28.0, "paperback": 7.0},
    "necropolis":            {"hardback": 35.0, "paperback": 9.0},
    "honour guard":          {"hardback": 28.0, "paperback": 7.0},
    "the guns of tanith":    {"hardback": 28.0, "paperback": 7.0},
    "straight silver":       {"hardback": 28.0, "paperback": 7.0},
    "sabbat martyr":         {"hardback": 35.0, "paperback": 9.0},
    "traitor general":       {"hardback": 30.0, "paperback": 8.0},
    "his last command":      {"hardback": 30.0, "paperback": 8.0},
    "the armour of contempt":{"hardback": 30.0, "paperback": 8.0},
    "only in death":         {"hardback": 30.0, "paperback": 8.0},
    "blood pact":            {"hardback": 35.0, "paperback": 9.0},
    "salvation's reach":     {"hardback": 35.0, "paperback": 9.0},
    "salvations reach":      {"hardback": 35.0, "paperback": 9.0},
    "the warmaster":         {"hardback": 40.0, "paperback": 10.0},
    "anarch":                {"hardback": 40.0, "paperback": 10.0},
    "the lost":              {"paperback": 25.0},
    "the saint":              {"paperback": 25.0},
    "the vincula insurgency": 40.0,

    # -------------------------------------------------------------------------
    # Night Lords Trilogy
    # -------------------------------------------------------------------------
    "soul hunter":        {"hardback": 45.0, "paperback": 15.0},
    "blood reaver":       {"hardback": 40.0, "paperback": 12.0},
    "void stalker":       {"hardback": 40.0, "paperback": 12.0},
    "night lords trilogy": 100.0,
    "night lords omnibus": {"paperback": 12.0},

    # -------------------------------------------------------------------------
    # Black Legion / Talon of Horus
    # -------------------------------------------------------------------------
    "talon of horus": {"hardback": 20.0, "paperback": 15.0},
    "black legion":   {"hardback": 20.0, "paperback": 12.0},

    # -------------------------------------------------------------------------
    # Ahriman Series
    # -------------------------------------------------------------------------
    "ahriman: exile":     {"hardback": 40.0, "paperback": 12.0},
    "ahriman: sorcerer":  {"hardback": 38.0, "paperback": 10.0},
    "ahriman: unchanged": {"hardback": 38.0, "paperback": 10.0},
    "ahriman: hand of dust": 35.0,

    # -------------------------------------------------------------------------
    # Space Wolves
    # -------------------------------------------------------------------------
    "space wolf":     {"hardback": 30.0, "paperback": 8.0},
    "ragnar blackmane":{"hardback": 28.0, "paperback": 7.0},
    "wolfblade":      {"hardback": 28.0, "paperback": 7.0},
    "sons of fenris": {"hardback": 28.0, "paperback": 7.0},
    "wolf's honour":  {"hardback": 28.0, "paperback": 7.0},
    "space wolf omnibus": {"paperback": 18.0},
    "space wolf omnibus 2": {"paperback": 28.0},

    # -------------------------------------------------------------------------
    # Ciaphas Cain — omnibus PBs are popular
    # -------------------------------------------------------------------------
    "hero of the imperium":    {"hardback": 35.0, "paperback": 10.0},
    "defender of the imperium":{"hardback": 35.0, "paperback": 45.0},
    "saviour of the imperium": {"hardback": 35.0, "paperback": 50.0},
    "ciaphas cain":            {"hardback": 30.0, "paperback": 15.0},

    # -------------------------------------------------------------------------
    # Ultramarines / Uriel Ventris
    # -------------------------------------------------------------------------
    "nightbringer":          {"hardback": 30.0, "paperback": 8.0},
    "warriors of ultramar":  {"hardback": 28.0, "paperback": 7.0},
    "dead sky black sun":    {"hardback": 28.0, "paperback": 7.0},
    "the killing ground":    {"hardback": 28.0, "paperback": 7.0},
    "courage and honour":    {"hardback": 28.0, "paperback": 7.0},
    "the chapter's due":     {"hardback": 30.0, "paperback": 8.0},
    "the unforgiving minute": 30.0,
    "ultramarine omnibus 2": {"paperback": 36.0},
    "deathwatch omnibus": {"paperback": 50.0},

    # -------------------------------------------------------------------------
    # Dark Imperium Series
    # -------------------------------------------------------------------------
    "dark imperium": {"hardback": 35.0, "paperback": 10.0},
    "plague war":    {"hardback": 35.0, "paperback": 10.0},
    "godblight":     {"hardback": 35.0, "paperback": 10.0},
    "indomitus novel": 15.0,
    "dark imperium trilogy complete": {"paperback": 20.0},

    # -------------------------------------------------------------------------
    # Path of the Eldar / Ynnari
    # -------------------------------------------------------------------------
    "path of the warrior": {"hardback": 35.0, "paperback": 12.0},
    "path of the seer":    {"hardback": 35.0, "paperback": 12.0},
    "path of the outcast": {"hardback": 35.0, "paperback": 12.0},
    "rise of the ynnari":  {"hardback": 35.0, "paperback": 12.0},
    "ghost warrior":       {"hardback": 35.0, "paperback": 10.0},

    # -------------------------------------------------------------------------
    # Blood Angels
    # -------------------------------------------------------------------------
    "deus encarmine":    {"hardback": 30.0, "paperback": 8.0},
    "deus sanguinius":   {"hardback": 30.0, "paperback": 8.0},
    "devastation of baal": 40.0,
    "lost emperor":      35.0,
    "blood angels omnibus 2" : {"paperback": 15.0},

    # -------------------------------------------------------------------------
    # Iron Warriors / Storm of Iron
    # -------------------------------------------------------------------------
    "storm of iron":  {"hardback": 45.0, "paperback": 15.0},
    "iron warrior":   35.0,
    "iron warrior omnibus": {"paperback": 20.0},

    # -------------------------------------------------------------------------
    # Other Popular 40K
    # -------------------------------------------------------------------------
    "titanicus":                  {"hardback": 35.0, "paperback": 10.0},
    "double eagle":               {"hardback": 35.0, "paperback": 10.0},
    "brothers of the snake":      {"hardback": 30.0, "paperback": 10.0},
    "xenos":                      {"hardback": 25.0, "paperback": 8.0},
    "malleus":                    {"hardback": 25.0, "paperback": 8.0},
    "hereticus":                  {"hardback": 25.0, "paperback": 8.0},
    "daemon world":               30.0,
    "helsreach":                  {"hardback": 40.0, "paperback": 12.0},
    "the emperor's gift":         {"hardback": 20.0, "paperback": 12.0},
    "priests of mars":            35.0,
    "lords of mars":              35.0,
    "gods of mars":               35.0,
    "mechanicus":                 30.0,
    "belisarius cawl":            {"hardback": 35.0, "paperback": 10.0},
    "ashes of prospero":          35.0,
    "lukas the trickster":        30.0,
    "valdor: birth of the imperium": 45.0,
    "the regent's shadow":        35.0,
    "the buried dagger":          35.0,
    "watchers of the throne":     40.0,
    "hand of darkness":           35.0,
    "eye of night":               35.0,
    "assassinorum":               {"hardback": 40.0, "paperback": 9.0},
    "kingsblade":                 30.0,
    "knightsblade":               30.0,
    "imperial knight":            30.0,
    "the macharian crusade omnibus": {"paperback": 35.0},
    "astra militarum legends": 20.0,
    "hammer of the emperor": {"paperback": 22.0},
    "lord of the night":          {"paperback": 20.0},
    "wrath of iron":              {"hardback": 28.0, "paperback": 18.0},
    "the magos":                  {"hardback": 30.0, "paperback": 22.0},
    "praetorian of dorn":         {"hardback": 25.0, "paperback": 8.0},
    "master of sanctity":         {"hardback": 25.0, "paperback": 12.0},
    "cadia stands":               {"paperback": 10.0},
    "the silent king":            {"paperback": 10.0},
    "bastion wars":               {"paperback": 22.0},
    "cassius":                    {"paperback": 22.0},
    "beast arises":               {"paperback": 8.0},
    "word bearers omnibus":       {"paperback": 18.0},

    # -------------------------------------------------------------------------
    # Omnibus Collections — 40K
    # -------------------------------------------------------------------------
    "enforcer omnibus":           {"paperback": 22.0},
    "salamander omnibus":         {"paperback": 30.0},
    "tome of fire":               {"paperback": 25.0},
    "blood angels omnibus 1":     {"paperback": 40.0},
    "soul drinkers omnibus":      {"paperback": 12.0},
    "grey knights omnibus":       {"paperback": 10.0},
    "ahriman omnibus":            {"paperback": 15.0},
    "blood ravens omnibus":       {"paperback": 12.0},
    "black tide":                 {"paperback": 12.0},
    "red fury":                   {"paperback": 12.0},
    "daemon hunter omnibus":      {"paperback": 12.0},
    "adeptus mechanicus omnibus": {"paperback": 28.0},
    "witch finder omnibus":       {"paperback": 32.0},

    # -------------------------------------------------------------------------
    # Dark Angels — Caliban Series
    # -------------------------------------------------------------------------
    "knights of caliban":         {"hardback": 35.0, "paperback": 22.0},
    "legacy of caliban":          {"hardback": 35.0, "paperback": 22.0},

    # -------------------------------------------------------------------------
    # Fanius bile
    # -------------------------------------------------------------------------
    "primogenitor": {"paperback":15.0},
    "clonelord":    {"paperback": 55.0},
    "manflayer": {"paperback":30.0},
    # -------------------------------------------------------------------------
    # Age of Sigmar
    # -------------------------------------------------------------------------
    "hamilcar: champion of the gods": 30.0,
    "plague garden":          30.0,
    "spear of shadows":       30.0,
    "eight lamentations":     30.0,
    "hallowed knights":       30.0,
    "blacktalon":             {"hardback": 30.0, "paperback": 10.0},
    "gotrek: realmslayer":    35.0,
    "gloomspite":             30.0,
    "thunderstrike":          28.0,
    "archaon":                {"hardback": 25.0, "paperback": 15.0},
    "the red path":           {"paperback": 40.0},
    "soul wars":              {"hardback": 25.0, "paperback": 15.0},
    "rise of nagash":         {"paperback": 18.0},
    "sigmar omnibus":         {"paperback": 12.0},

    # -------------------------------------------------------------------------
    # Warhammer Fantasy / Old World
    # -------------------------------------------------------------------------
    "gotrek and felix":   {"hardback": 30.0, "paperback": 12.0},
    "trollslayer":        {"hardback": 28.0, "paperback": 8.0},
    "skavenslayer":       {"hardback": 28.0, "paperback": 8.0},
    "daemonslayer":       {"hardback": 28.0, "paperback": 8.0},
    "dragonslayer":       {"hardback": 28.0, "paperback": 8.0},
    "beastslayer":        {"hardback": 28.0, "paperback": 8.0},
    "vampireslayer":      {"hardback": 28.0, "paperback": 8.0},
    "giantslayer":        {"hardback": 28.0, "paperback": 8.0},
    "orcslayer":          {"hardback": 28.0, "paperback": 8.0},
    "manslayer":          {"hardback": 28.0, "paperback": 8.0},
    "elfslayer":          {"hardback": 28.0, "paperback": 8.0},
    "shamanslayer":       {"hardback": 28.0, "paperback": 8.0},
    "zombieslayer":       {"hardback": 28.0, "paperback": 8.0},
    "road of skulls":     28.0,
    "the serpent queen":  28.0,
    "curse of the necrarch": 28.0,
    "sword of justice":   28.0,
    "sword of vengeance": 28.0,
    "palace of the plague lord": 28.0,
    "gotrek and felix first omnibus": {"paperback": 8.0},
    "gotrek and felix second omnibus": {"paperback": 28.0},
    "gotrek and felix third omnibus": {"paperback": 25.0},
    "warhammer chronicles: the war of vengeance omnibus": {"paperback": 45.0},
    "vampire genevieve":      {"paperback": 18.0},
    "thunder and steel":      {"paperback": 12.0},
    "elves omnibus":          {"paperback": 20.0},
    "drakenfels":             {"paperback": 10.0},
    "malus darkblade":        {"hardback": 35.0, "paperback": 25.0},
    "malus darkblade omnibus 2": {"paperback": 35.0},

    # -------------------------------------------------------------------------
    # Add your own entries below
    # -------------------------------------------------------------------------
    "lords of silence": {"paperback": 40.0},
    "broken city": {"paperback": 22.0},
    "grotsnik: do mad doc": 15.0,
}