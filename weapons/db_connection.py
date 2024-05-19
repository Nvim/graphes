import sqlite3

ignore_craftable = False
suffix = ""
if ignore_craftable:
    suffix = " - 'Craftables' ignorés"
else:
    suffix = " - 'Craftables' inclus"
conn = sqlite3.connect("../mhw.db")
MAX_RANK = 16
output_dir = "./output"
weapon_names = {
    "great-sword",
    "long-sword",
    "sword-and-shield",
    "dual-blades",
    "hammer",
    "hunting-horn",
    "lance",
    "gunlance",
    "switch-axe",
    "charge-blade",
    "insect-glaive",
    "light-bowgun",
    "heavy-bowgun",
    "bow",
}

armor_types = {
    "head",
    "chest",
    "arms",
    "waist",
    "legs",
}
