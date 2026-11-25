# fonctionnel

ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
POIDS = (1, 3, 5, 7, 9, 11, 13)
LONGUEUR_CORPS = len(POIDS)
PREFIXES = ("DEP", "RET", "TRX")


def cle_controle(corps: str) -> str:
    total = sum(poids * ALPHABET.index(car) for poids, car in zip(POIDS, corps, strict=True))
    return ALPHABET[total % len(ALPHABET)]


def composer_numero(prefixe: str, corps: str) -> str:
    complet = corps + cle_controle(corps)
    return f"{prefixe}-{complet[:4]}-{complet[4:]}"


def normaliser(saisie: str) -> str | None:
    brut = "".join(car for car in saisie.upper() if car.isalnum())
    prefixe, reste = brut[:3], brut[3:]
    if prefixe not in PREFIXES or len(reste) != LONGUEUR_CORPS + 1:
        return None
    return f"{prefixe}-{reste[:4]}-{reste[4:]}"


def est_numero_valide(saisie: str) -> bool:
    numero = normaliser(saisie)
    if numero is None:
        return False
    caracteres = numero[4:].replace("-", "")
    if any(car not in ALPHABET for car in caracteres):
        return False
    corps, cle = caracteres[:-1], caracteres[-1]
    return cle_controle(corps) == cle
