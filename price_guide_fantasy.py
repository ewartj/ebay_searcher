"""
Fantasy & Sci-Fi Price Guide — UK secondary market values (GBP).

Keys are lowercase substrings matched against listing titles (case-insensitive).
See price_guide.py for format documentation.
"""
from price_guide import Entry, PriceEntry  # noqa: F401 — re-exported

FANTASY_PRICE_GUIDE: dict[str, Entry] = {

    # -------------------------------------------------------------------------
    # Joe Abercrombie — First Law World
    # -------------------------------------------------------------------------
    "the blade itself":             {"hardback": 28.0, "paperback": 8.0},
    "before they are hanged":       {"hardback": 25.0, "paperback": 8.0},
    "last argument of kings":       {"hardback": 28.0, "paperback": 8.0},
    "best served cold":             {"hardback": 25.0, "paperback": 8.0},
    "abercrombie the heroes":       {"hardback": 25.0, "paperback": 8.0},
    "red country":                  {"hardback": 25.0, "paperback": 8.0},
    "sharp ends":                   {"hardback": 30.0, "paperback": 10.0},
    "a little hatred":              {"hardback": 28.0, "paperback": 8.0},
    "the trouble with peace":       {"hardback": 28.0, "paperback": 8.0},
    "the wisdom of crowds":         {"hardback": 28.0, "paperback": 8.0},
    # Signed/limited Abercrombie fetch premium
    "abercrombie signed":           55.0,
    "first law signed":             50.0,

    # -------------------------------------------------------------------------
    # Brandon Sanderson — Stormlight Archive
    # -------------------------------------------------------------------------
    "the way of kings":             {"hardback": 35.0, "paperback": 10.0},
    "words of radiance":            {"hardback": 35.0, "paperback": 10.0},
    "oathbringer":                  {"hardback": 35.0, "paperback": 10.0},
    "rhythm of war":                {"hardback": 35.0, "paperback": 10.0},
    "wind and truth":               {"hardback": 35.0, "paperback": 10.0},
    "stormlight archive":           35.0,

    # Brandon Sanderson — Mistborn
    "the final empire":             {"hardback": 30.0, "paperback": 9.0},
    "the well of ascension":        {"hardback": 28.0, "paperback": 9.0},
    "the hero of ages":             {"hardback": 28.0, "paperback": 9.0},
    "the alloy of law":             {"hardback": 25.0, "paperback": 8.0},
    "shadows of self":              {"hardback": 25.0, "paperback": 8.0},
    "the bands of mourning":        {"hardback": 25.0, "paperback": 8.0},
    "mistborn":                     {"hardback": 28.0, "paperback": 9.0},

    # Brandon Sanderson — Other
    "elantris":                     {"hardback": 25.0, "paperback": 8.0},
    "warbreaker":                   {"hardback": 25.0, "paperback": 8.0},
    "the emperor's soul":           20.0,
    "sanderson signed":             70.0,

    # -------------------------------------------------------------------------
    # Dragonlance Chronicles — Weis & Hickman
    # -------------------------------------------------------------------------
    "dragons of autumn twilight":   {"hardback": 25.0, "paperback": 8.0},
    "dragons of winter night":      {"hardback": 22.0, "paperback": 7.0},
    "dragons of spring dawning":    {"hardback": 22.0, "paperback": 7.0},
    "dragonlance chronicles":       {"hardback": 30.0, "paperback": 10.0},
    "dragonlance legends":          {"hardback": 28.0, "paperback": 9.0},
    "time of the twins":            {"hardback": 22.0, "paperback": 7.0},
    "war of the twins":             {"hardback": 22.0, "paperback": 7.0},
    "test of the twins":            {"hardback": 22.0, "paperback": 7.0},
    "dragons of the dwarven depths":{"hardback": 20.0, "paperback": 7.0},

    # -------------------------------------------------------------------------
    # Patrick Rothfuss — Kingkiller Chronicle
    # -------------------------------------------------------------------------
    "the name of the wind":         {"hardback": 35.0, "paperback": 10.0},
    "the wise man's fear":          {"hardback": 32.0, "paperback": 10.0},
    "the slow regard of silent things": {"hardback": 22.0, "paperback": 7.0},
    "kingkiller chronicle":         35.0,
    "rothfuss signed":              80.0,

    # -------------------------------------------------------------------------
    # Robin Hobb — Realm of the Elderlings
    # -------------------------------------------------------------------------
    # Farseer Trilogy
    "assassin's apprentice":        {"hardback": 28.0, "paperback": 8.0},
    "royal assassin":               {"hardback": 25.0, "paperback": 8.0},
    "assassin's quest":             {"hardback": 25.0, "paperback": 8.0},
    # Liveship Traders
    "ship of magic":                {"hardback": 25.0, "paperback": 8.0},
    "the mad ship":                 {"hardback": 22.0, "paperback": 7.0},
    "ship of destiny":              {"hardback": 22.0, "paperback": 7.0},
    # Tawny Man
    "fool's errand":                {"hardback": 25.0, "paperback": 8.0},
    "the golden fool":              {"hardback": 22.0, "paperback": 7.0},
    "fool's fate":                  {"hardback": 22.0, "paperback": 7.0},
    # Fitz and the Fool
    "fool's assassin":              {"hardback": 25.0, "paperback": 8.0},
    "fool's quest":                 {"hardback": 25.0, "paperback": 8.0},
    "assassin's fate":              {"hardback": 28.0, "paperback": 8.0},
    "robin hobb signed":            55.0,

    # -------------------------------------------------------------------------
    # Steven Erikson — Malazan Book of the Fallen
    # -------------------------------------------------------------------------
    "gardens of the moon":          {"hardback": 30.0, "paperback": 9.0},
    "deadhouse gates":              {"hardback": 28.0, "paperback": 9.0},
    "memories of ice":              {"hardback": 28.0, "paperback": 9.0},
    "house of chains":              {"hardback": 25.0, "paperback": 8.0},
    "midnight tides":               {"hardback": 25.0, "paperback": 8.0},
    "the bonehunters":              {"hardback": 25.0, "paperback": 8.0},
    "reaper's gale":                {"hardback": 25.0, "paperback": 8.0},
    "toll the hounds":              {"hardback": 25.0, "paperback": 8.0},
    "dust of dreams":               {"hardback": 25.0, "paperback": 8.0},
    "the crippled god":             {"hardback": 25.0, "paperback": 8.0},
    "malazan book of the fallen":   28.0,
    "erikson signed":               55.0,

    # -------------------------------------------------------------------------
    # Iain M. Banks — Culture Series
    # -------------------------------------------------------------------------
    "consider phlebas":             {"hardback": 30.0, "paperback": 9.0},
    "the player of games":          {"hardback": 30.0, "paperback": 9.0},
    "use of weapons":               {"hardback": 32.0, "paperback": 9.0},
    "the state of the art":         {"hardback": 25.0, "paperback": 8.0},
    "excession":                    {"hardback": 25.0, "paperback": 8.0},
    "iain banks inversions":        {"hardback": 25.0, "paperback": 8.0},
    "look to windward":             {"hardback": 28.0, "paperback": 9.0},
    "iain banks matter":            {"hardback": 22.0, "paperback": 8.0},
    "surface detail":               {"hardback": 22.0, "paperback": 8.0},
    "the hydrogen sonata":          {"hardback": 22.0, "paperback": 8.0},
    "iain m banks signed":          60.0,
    "iain banks signed":            60.0,

    # -------------------------------------------------------------------------
    # Peter F. Hamilton — Commonwealth / Night's Dawn
    # -------------------------------------------------------------------------
    "pandora's star":               {"hardback": 22.0, "paperback": 8.0},
    "judas unchained":              {"hardback": 22.0, "paperback": 8.0},
    "the dreaming void":            {"hardback": 22.0, "paperback": 8.0},
    "the temporal void":            {"hardback": 22.0, "paperback": 8.0},
    "the evolutionary void":        {"hardback": 22.0, "paperback": 8.0},
    "great north road":             {"hardback": 22.0, "paperback": 8.0},
    "hamilton signed":              50.0,

    # -------------------------------------------------------------------------
    # Alastair Reynolds — Revelation Space
    # -------------------------------------------------------------------------
    "revelation space":             {"hardback": 28.0, "paperback": 9.0},
    "chasm city":                   {"hardback": 25.0, "paperback": 8.0},
    "redemption ark":               {"hardback": 25.0, "paperback": 8.0},
    "absolution gap":               {"hardback": 22.0, "paperback": 8.0},
    "house of suns":                {"hardback": 22.0, "paperback": 8.0},
    "terminal world":               {"hardback": 22.0, "paperback": 8.0},
    "poseidon's wake":              {"hardback": 22.0, "paperback": 8.0},
    "reynolds signed":              50.0,

    # -------------------------------------------------------------------------
    # Mark Lawrence — Broken Empire / Red Queen's War / Book of the Ancestor
    # -------------------------------------------------------------------------
    "prince of thorns":             {"hardback": 25.0, "paperback": 8.0},
    "king of thorns":               {"hardback": 22.0, "paperback": 8.0},
    "emperor of thorns":            {"hardback": 22.0, "paperback": 8.0},
    "prince of fools":              {"hardback": 22.0, "paperback": 7.0},
    "the liar's key":               {"hardback": 22.0, "paperback": 7.0},
    "the wheel of osheim":          {"hardback": 22.0, "paperback": 7.0},
    "red sister":                   {"hardback": 22.0, "paperback": 7.0},
    "grey sister":                  {"hardback": 22.0, "paperback": 7.0},
    "holy sister":                  {"hardback": 22.0, "paperback": 7.0},
    "lawrence signed":              45.0,

    # -------------------------------------------------------------------------
    # Michael J. Sullivan — Riyria Chronicles
    # -------------------------------------------------------------------------
    "theft of swords":              {"hardback": 22.0, "paperback": 7.0},
    "rise of empire":               {"hardback": 22.0, "paperback": 7.0},
    "heir of novron":               {"hardback": 22.0, "paperback": 7.0},
    "riyria chronicles":            22.0,
    "sullivan signed":              45.0,

    # -------------------------------------------------------------------------
    # Terry Pratchett — Discworld (signed/early printings are high value)
    # -------------------------------------------------------------------------
    "discworld":                    {"hardback": 22.0, "paperback": 7.0},
    "terry pratchett signed":       80.0,
    "pratchett signed":             80.0,
    "the colour of magic":          {"hardback": 35.0, "paperback": 10.0},
    "guards! guards!":              {"hardback": 30.0, "paperback": 9.0},
    "small gods":                   {"hardback": 28.0, "paperback": 8.0},
    "pratchett going postal":       {"hardback": 25.0, "paperback": 8.0},
    "pratchett night watch":        {"hardback": 28.0, "paperback": 8.0},
    "thud!":                        {"hardback": 22.0, "paperback": 7.0},
    "raising steam":                {"hardback": 22.0, "paperback": 7.0},

    # -------------------------------------------------------------------------
    # Neil Gaiman
    # -------------------------------------------------------------------------
    "american gods":                {"hardback": 28.0, "paperback": 9.0},
    "neverwhere":                   {"hardback": 25.0, "paperback": 8.0},
    "good omens":                   {"hardback": 25.0, "paperback": 8.0},
    "stardust":                     {"hardback": 25.0, "paperback": 8.0},
    "anansi boys":                  {"hardback": 22.0, "paperback": 7.0},
    "the ocean at the end of the lane": {"hardback": 22.0, "paperback": 7.0},
    "norse mythology":              {"hardback": 20.0, "paperback": 7.0},
    "neil gaiman signed":           70.0,
    "gaiman signed":                70.0,

    # -------------------------------------------------------------------------
    # Gene Wolfe — New Sun / Long Sun
    # -------------------------------------------------------------------------
    "the shadow of the torturer":   {"hardback": 35.0, "paperback": 10.0},
    "the claw of the conciliator":  {"hardback": 30.0, "paperback": 9.0},
    "the sword of the lictor":      {"hardback": 30.0, "paperback": 9.0},
    "the citadel of the autarch":   {"hardback": 28.0, "paperback": 9.0},
    "book of the new sun":          35.0,
    "wolfe signed":                 60.0,

    # -------------------------------------------------------------------------
    # Ursula K. Le Guin — Earthsea / Hainish
    # -------------------------------------------------------------------------
    "a wizard of earthsea":         {"hardback": 28.0, "paperback": 9.0},
    "the tombs of atuan":           {"hardback": 25.0, "paperback": 8.0},
    "the farthest shore":           {"hardback": 25.0, "paperback": 8.0},
    "tehanu":                       {"hardback": 25.0, "paperback": 8.0},
    "the left hand of darkness":    {"hardback": 28.0, "paperback": 9.0},
    "the dispossessed":             {"hardback": 28.0, "paperback": 9.0},
    "le guin signed":               60.0,

    # -------------------------------------------------------------------------
    # Richard Morgan — Takeshi Kovacs
    # -------------------------------------------------------------------------
    "altered carbon":               {"hardback": 28.0, "paperback": 9.0},
    "broken angels":                {"hardback": 22.0, "paperback": 8.0},
    "woken furies":                 {"hardback": 22.0, "paperback": 8.0},
    "market forces":                {"hardback": 20.0, "paperback": 7.0},
    "morgan signed":                45.0,

    # -------------------------------------------------------------------------
    # Subscription box special editions
    # Illumicrate / OwlCrate / FairyLoot editions carry a premium over
    # standard printings. More specific author+box keys below override these.
    # -------------------------------------------------------------------------
    "illumicrate signed":           75.0,
    "illumicrate":                  35.0,
    "owlcrate signed":              60.0,
    "owlcrate":                     30.0,
    "fairyloot signed":             60.0,
    "fairyloot":                    30.0,

    # -------------------------------------------------------------------------
    # V.E. Schwab — Shades of Magic / Villains / standalone
    # -------------------------------------------------------------------------
    "a darker shade of magic":      {"hardback": 30.0, "paperback": 9.0},
    "a gathering of shadows":       {"hardback": 25.0, "paperback": 8.0},
    "a conjuring of light":         {"hardback": 25.0, "paperback": 8.0},
    "shades of magic":              28.0,
    "vicious schwab":               {"hardback": 28.0, "paperback": 9.0},
    "vengeful schwab":              {"hardback": 25.0, "paperback": 8.0},
    "the invisible life of addie":  {"hardback": 32.0, "paperback": 9.0},
    "the archived":                 {"hardback": 22.0, "paperback": 7.0},
    "schwab signed":                65.0,
    "v e schwab signed":            65.0,

    # -------------------------------------------------------------------------
    # Leigh Bardugo — Grishaverse
    # -------------------------------------------------------------------------
    "shadow and bone":              {"hardback": 25.0, "paperback": 8.0},
    "siege and storm":              {"hardback": 22.0, "paperback": 7.0},
    "ruin and rising":              {"hardback": 22.0, "paperback": 7.0},
    "six of crows":                 {"hardback": 35.0, "paperback": 10.0},
    "crooked kingdom":              {"hardback": 28.0, "paperback": 9.0},
    "king of scars":                {"hardback": 22.0, "paperback": 7.0},
    "rule of wolves":               {"hardback": 22.0, "paperback": 7.0},
    "ninth house bardugo":          {"hardback": 28.0, "paperback": 9.0},
    "hell bent bardugo":            {"hardback": 22.0, "paperback": 7.0},
    "bardugo signed":               60.0,

    # -------------------------------------------------------------------------
    # Sarah J. Maas — ACOTAR / Throne of Glass / Crescent City
    # -------------------------------------------------------------------------
    "a court of thorns and roses":  {"hardback": 28.0, "paperback": 9.0},
    "a court of mist and fury":     {"hardback": 28.0, "paperback": 9.0},
    "a court of wings and ruin":    {"hardback": 25.0, "paperback": 8.0},
    "a court of frost and starlight":{"hardback": 22.0, "paperback": 7.0},
    "a court of silver flames":     {"hardback": 25.0, "paperback": 8.0},
    "throne of glass":              {"hardback": 25.0, "paperback": 8.0},
    "crown of midnight":            {"hardback": 22.0, "paperback": 7.0},
    "heir of fire":                 {"hardback": 22.0, "paperback": 7.0},
    "queen of shadows":             {"hardback": 22.0, "paperback": 7.0},
    "empire of storms":             {"hardback": 22.0, "paperback": 7.0},
    "tower of dawn":                {"hardback": 22.0, "paperback": 7.0},
    "kingdom of the wicked":        {"hardback": 22.0, "paperback": 7.0},
    "house of earth and blood":     {"hardback": 25.0, "paperback": 8.0},
    "house of sky and breath":      {"hardback": 22.0, "paperback": 7.0},
    "maas signed":                  65.0,
    "sarah j maas signed":          65.0,

    # -------------------------------------------------------------------------
    # R.F. Kuang
    # -------------------------------------------------------------------------
    "babel kuang":                  {"hardback": 30.0, "paperback": 9.0},
    "the poppy war":                {"hardback": 28.0, "paperback": 9.0},
    "the dragon republic":          {"hardback": 25.0, "paperback": 8.0},
    "the burning god":              {"hardback": 25.0, "paperback": 8.0},
    "yellowface kuang":             {"hardback": 22.0, "paperback": 7.0},
    "kuang signed":                 55.0,
    "r f kuang signed":             55.0,

    # -------------------------------------------------------------------------
    # Samantha Shannon — The Bone Season / Priory
    # -------------------------------------------------------------------------
    "the priory of the orange tree": {"hardback": 40.0, "paperback": 10.0},
    "the bone season":              {"hardback": 22.0, "paperback": 7.0},
    "the mime order":               {"hardback": 22.0, "paperback": 7.0},
    "the song rising":              {"hardback": 22.0, "paperback": 7.0},
    "a day of fallen night":        {"hardback": 28.0, "paperback": 8.0},
    "shannon signed":               55.0,
    "samantha shannon signed":      55.0,

    # -------------------------------------------------------------------------
    # Naomi Novik — Temeraire / standalone
    # -------------------------------------------------------------------------
    "his majesty's dragon":         {"hardback": 25.0, "paperback": 8.0},
    "throne of jade":               {"hardback": 22.0, "paperback": 7.0},
    "black powder war":             {"hardback": 22.0, "paperback": 7.0},
    "uprooted novik":               {"hardback": 28.0, "paperback": 9.0},
    "spinning silver":              {"hardback": 25.0, "paperback": 8.0},
    "a deadly education":           {"hardback": 22.0, "paperback": 7.0},
    "the last graduate":            {"hardback": 22.0, "paperback": 7.0},
    "the golden enclaves":          {"hardback": 22.0, "paperback": 7.0},
    "novik signed":                 50.0,

    # -------------------------------------------------------------------------
    # Holly Black — Folk of the Air / standalone
    # -------------------------------------------------------------------------
    "the cruel prince":             {"hardback": 25.0, "paperback": 8.0},
    "the wicked king":              {"hardback": 22.0, "paperback": 7.0},
    "the queen of nothing":         {"hardback": 22.0, "paperback": 7.0},
    "the book of night":            {"hardback": 22.0, "paperback": 7.0},
    "holly black signed":           50.0,

}
