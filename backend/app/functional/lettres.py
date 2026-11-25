# fonctionnel
from decimal import Decimal

UNITES = (
    "zéro", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf",
    "dix", "onze", "douze", "treize", "quatorze", "quinze", "seize",
)
DIZAINES = {2: "vingt", 3: "trente", 4: "quarante", 5: "cinquante", 6: "soixante", 8: "quatre-vingt"}

NOMS_DEVISES = {
    "DZD": ("dinar algérien", "dinars algériens", "centime", "centimes"),
    "EUR": ("euro", "euros", "centime", "centimes"),
    "USD": ("dollar américain", "dollars américains", "cent", "cents"),
}


def _moins_de_cent(n: int) -> str:
    if n < 17:
        return UNITES[n]
    if n < 20:
        return "dix-" + UNITES[n - 10]
    dizaine, unite = divmod(n, 10)
    if dizaine in (7, 9):
        base = DIZAINES[dizaine - 1]
        reste = 10 + unite
        liaison = " et " if dizaine == 7 and unite == 1 else "-"
        return base + liaison + _moins_de_cent(reste)
    base = DIZAINES[dizaine]
    if unite == 0:
        return base + ("s" if dizaine == 8 else "")
    if unite == 1 and dizaine != 8:
        return base + " et un"
    return base + "-" + UNITES[unite]


def _moins_de_mille(n: int, pluriel: bool = True) -> str:
    centaines, reste = divmod(n, 100)
    morceaux = []
    if centaines:
        mot = "cent" if centaines == 1 else UNITES[centaines] + " cent"
        if centaines > 1 and reste == 0 and pluriel:
            mot += "s"
        morceaux.append(mot)
    if reste or not centaines:
        texte = _moins_de_cent(reste)
        if not pluriel and texte.endswith("quatre-vingts"):
            texte = texte[:-1]
        morceaux.append(texte)
    return " ".join(morceaux)


def nombre_en_lettres(n: int) -> str:
    if n == 0:
        return "zéro"
    milliards, n = divmod(n, 1_000_000_000)
    millions, n = divmod(n, 1_000_000)
    milliers, reste = divmod(n, 1000)
    morceaux = []
    for valeur, singulier, pluriel in ((milliards, "milliard", "milliards"), (millions, "million", "millions")):
        if valeur:
            morceaux.append(f"{_moins_de_mille(valeur)} {singulier if valeur == 1 else pluriel}")
    if milliers:
        morceaux.append("mille" if milliers == 1 else _moins_de_mille(milliers, pluriel=False) + " mille")
    if reste:
        morceaux.append(_moins_de_mille(reste))
    return " ".join(morceaux)


def montant_en_lettres(montant: Decimal, devise: str = "DZD") -> str:
    unite_s, unite_p, centime_s, centime_p = NOMS_DEVISES[devise]
    entier = int(montant)
    centimes = int((Decimal(montant) - entier) * 100)
    nom_unite = unite_p if entier >= 2 else unite_s
    if entier >= 1_000_000 and entier % 1_000_000 == 0:
        liaison = "d'" if nom_unite[0] in "aeiouy" else "de "
        texte = f"{nombre_en_lettres(entier)} {liaison}{nom_unite}"
    else:
        texte = f"{nombre_en_lettres(entier)} {nom_unite}"
    if centimes:
        texte += f" et {nombre_en_lettres(centimes)} {centime_p if centimes >= 2 else centime_s}"
    return texte
