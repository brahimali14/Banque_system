from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen.canvas import Canvas

from app import config
from app.functional.lettres import montant_en_lettres
from app.functional.stats import formater_montant

BLEU = colors.HexColor("#1f4e9e")
GRIS = colors.HexColor("#5b6475")
LARGEUR, HAUTEUR = A4
MARGE = 2 * cm


def _nouveau_document(titre: str) -> tuple[Canvas, BytesIO]:
    tampon = BytesIO()
    pdf = Canvas(tampon, pagesize=A4)
    pdf.setTitle(titre)
    pdf.setAuthor(config.NOM_BANQUE)
    _en_tete(pdf, titre)
    return pdf, tampon


def _en_tete(pdf: Canvas, titre: str) -> None:
    pdf.setFillColor(BLEU)
    pdf.rect(0, HAUTEUR - 3 * cm, LARGEUR, 3 * cm, stroke=0, fill=1)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawString(MARGE, HAUTEUR - 1.8 * cm, config.NOM_BANQUE)
    pdf.setFont("Helvetica", 12)
    pdf.drawRightString(LARGEUR - MARGE, HAUTEUR - 1.8 * cm, titre)


def _pied(pdf: Canvas) -> None:
    pdf.setFillColor(GRIS)
    pdf.setFont("Helvetica-Oblique", 9)
    pdf.drawCentredString(LARGEUR / 2, 1.2 * cm, "Simulateur pédagogique — données fictives")


def _terminer(pdf: Canvas, tampon: BytesIO) -> bytes:
    _pied(pdf)
    pdf.showPage()
    pdf.save()
    return tampon.getvalue()


def _lignes(pdf: Canvas, y: float, lignes: list[tuple[str, str]]) -> float:
    for etiquette, valeur in lignes:
        pdf.setFillColor(GRIS)
        pdf.setFont("Helvetica", 11)
        pdf.drawString(MARGE, y, etiquette)
        pdf.setFillColor(colors.black)
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(MARGE + 5 * cm, y, valeur)
        y -= 0.75 * cm
    return y


def _cadre_numero(pdf: Canvas, y: float, etiquette: str, numero: str) -> float:
    hauteur = 2.6 * cm
    pdf.setStrokeColor(BLEU)
    pdf.setLineWidth(2)
    pdf.roundRect(MARGE, y - hauteur, LARGEUR - 2 * MARGE, hauteur, 8, stroke=1, fill=0)
    pdf.setFillColor(GRIS)
    pdf.setFont("Helvetica", 11)
    pdf.drawCentredString(LARGEUR / 2, y - 0.8 * cm, etiquette)
    pdf.setFillColor(BLEU)
    pdf.setFont("Courier-Bold", 30)
    pdf.drawCentredString(LARGEUR / 2, y - 2 * cm, numero)
    return y - hauteur - 1 * cm


def _date(instant) -> str:
    return instant.strftime("%d/%m/%Y à %H:%M")


def bordereau(demande, compte, client) -> bytes:
    nature = "dépôt" if demande.type == "DEPOT" else "retrait"
    pdf, tampon = _nouveau_document(f"Bordereau de {nature}")
    y = HAUTEUR - 4.5 * cm
    pdf.setFont("Helvetica-Bold", 16)
    pdf.setFillColor(colors.black)
    pdf.drawString(MARGE, y, f"Demande de {nature}")
    y = _cadre_numero(pdf, y - 0.6 * cm, "Numéro du bordereau — à communiquer à l'agent", demande.numero_bordereau)
    y = _lignes(
        pdf,
        y,
        [
            ("Créé le", _date(demande.date_creation)),
            ("Valable jusqu'au", _date(demande.date_expiration)),
            ("Client", client.nom_complet),
            ("N° d'identité", client.identiteMasquee()),
            ("Compte", f"{compte.numero} — {compte.LIBELLE} ({compte.devise})"),
            ("Montant", formater_montant(demande.montant, compte.devise)),
        ],
    )
    pdf.setFont("Helvetica-Oblique", 10)
    pdf.setFillColor(GRIS)
    pdf.drawString(MARGE, y, f"Soit : {montant_en_lettres(demande.montant, compte.devise)}")
    y -= 1.5 * cm
    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 11)
    for ligne in (
        "Présentez ce bordereau au guichet avec votre pièce d'identité avant la date d'expiration.",
        "Communiquez le numéro ci-dessus à l'agent : il le saisira pour retrouver votre demande.",
        "Ce bordereau ne peut être utilisé qu'une seule fois.",
    ):
        pdf.drawString(MARGE, y, "• " + ligne)
        y -= 0.6 * cm
    return _terminer(pdf, tampon)


def recu(transaction, compte, client, nom_agent: str | None = None) -> bytes:
    pdf, tampon = _nouveau_document("Reçu d'opération")
    y = HAUTEUR - 4.5 * cm
    pdf.setFont("Helvetica-Bold", 16)
    pdf.setFillColor(colors.HexColor("#1b7f3b"))
    pdf.drawString(MARGE, y, "OPÉRATION VALIDÉE")
    y = _cadre_numero(pdf, y - 0.6 * cm, "Numéro de reçu (vérifiable auprès de la banque)", transaction.reference)
    lignes = [
        ("Date", _date(transaction.date)),
        ("Opération", transaction.libelle),
        ("Client", client.nom_complet),
        ("Compte", f"{compte.numero} — {compte.LIBELLE} ({compte.devise})"),
        ("Montant", formater_montant(transaction.montant, transaction.devise)),
        ("Solde après opération", formater_montant(transaction.solde_apres, transaction.devise)),
    ]
    if nom_agent:
        lignes.append(("Agent", nom_agent))
    _lignes(pdf, y, lignes)
    return _terminer(pdf, tampon)


def fiche_identifiants(client, login: str, mot_de_passe: str, expiration) -> bytes:
    pdf, tampon = _nouveau_document("Vos identifiants")
    y = HAUTEUR - 4.5 * cm
    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(MARGE, y, f"Bienvenue {client.nom_complet}")
    y -= 1.2 * cm
    y = _cadre_numero(pdf, y, "Nom d'utilisateur", login)
    y = _cadre_numero(pdf, y, "Mot de passe temporaire", mot_de_passe)
    pdf.setFont("Helvetica", 11)
    for ligne in (
        f"Ce mot de passe temporaire est valable jusqu'au {_date(expiration)}.",
        "À votre première connexion, vous devrez choisir votre propre mot de passe",
        "(8 caractères minimum, avec une majuscule, une minuscule et un chiffre).",
        "Ne communiquez jamais vos identifiants, même à un employé de la banque.",
    ):
        pdf.drawString(MARGE, y, "• " + ligne)
        y -= 0.6 * cm
    return _terminer(pdf, tampon)


def releve(compte, client, transactions, debut, fin) -> bytes:
    pdf, tampon = _nouveau_document("Relevé de compte")
    y = HAUTEUR - 4.5 * cm
    y = _lignes(
        pdf,
        y,
        [
            ("Client", client.nom_complet),
            ("Compte", f"{compte.numero} — {compte.LIBELLE} ({compte.devise})"),
            ("Période", f"du {debut:%d/%m/%Y} au {fin:%d/%m/%Y}"),
            ("Solde actuel", formater_montant(compte.solde, compte.devise)),
        ],
    )
    y -= 0.4 * cm
    colonnes = (MARGE, MARGE + 3.2 * cm, MARGE + 10.5 * cm, LARGEUR - MARGE)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.setFillColor(BLEU)
    for x, titre in zip(colonnes[:3], ("Date", "Libellé", "Montant")):
        pdf.drawString(x, y, titre)
    pdf.drawRightString(colonnes[3], y, "Solde")
    y -= 0.6 * cm
    pdf.setFont("Helvetica", 9)
    pdf.setFillColor(colors.black)
    for transaction in transactions:
        if y < 2.5 * cm:
            _pied(pdf)
            pdf.showPage()
            y = HAUTEUR - 2 * cm
            pdf.setFont("Helvetica", 9)
        signe = "-" if transaction.type in ("RETRAIT", "VIREMENT_EMIS", "FRAIS") else "+"
        pdf.drawString(colonnes[0], y, transaction.date.strftime("%d/%m/%Y"))
        pdf.drawString(colonnes[1], y, transaction.libelle[:45])
        pdf.drawString(colonnes[2], y, signe + formater_montant(transaction.montant, transaction.devise))
        pdf.drawRightString(colonnes[3], y, formater_montant(transaction.solde_apres, transaction.devise))
        y -= 0.5 * cm
    return _terminer(pdf, tampon)
