"""Génère les PDF de la documentation : ETUDE_SYSTEME.pdf, RAPPORT_PARADIGMES.pdf
et RAPPORT_PARADIGMES_AR.pdf.

1. régénère les pages HTML (build_html.py) ;
2. les sert sur http://127.0.0.1 (port libre choisi au hasard) ;
3. les ouvre dans Microsoft Edge ou Google Chrome sans fenêtre (« headless »), attend que
   tous les diagrammes Mermaid soient dessinés, puis les imprime en PDF (format A4).

Le navigateur est piloté par le protocole DevTools, avec la seule bibliothèque standard.
Une connexion Internet est nécessaire (Markdown et Mermaid sont chargés depuis un CDN).

Usage :  python docs/build_pdf.py
"""
import base64
import functools
import http.server
import json
import os
import shutil
import socket
import struct
import subprocess
import tempfile
import threading
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from build_html import DOCS, DOCUMENTS, generer

NAVIGATEURS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "msedge", "google-chrome", "chromium", "chromium-browser",
]
DELAI_DIAGRAMMES = 180  # secondes au plus pour dessiner les diagrammes d'une page


def trouver_navigateur() -> str:
    for candidat in NAVIGATEURS:
        chemin = shutil.which(candidat) or (candidat if Path(candidat).is_file() else None)
        if chemin:
            return chemin
    raise SystemExit("Edge ou Chrome est introuvable : impossible d'imprimer les PDF.")


# --- Serveur des pages HTML ------------------------------------------------------------

class GestionnaireSilencieux(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args) -> None:  # pas de journal des requêtes
        pass


def demarrer_serveur() -> http.server.ThreadingHTTPServer:
    gestionnaire = functools.partial(GestionnaireSilencieux, directory=str(DOCS))
    serveur = http.server.ThreadingHTTPServer(("127.0.0.1", 0), gestionnaire)
    serveur.handle_error = lambda *args: None  # connexions coupées par le navigateur : sans effet
    threading.Thread(target=serveur.serve_forever, daemon=True).start()
    return serveur


# --- Client WebSocket minimal pour le protocole DevTools --------------------------------

class DevTools:
    def __init__(self, url_ws: str) -> None:
        adresse = urlparse(url_ws)
        self.sock = socket.create_connection((adresse.hostname, adresse.port), timeout=60)
        cle = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((
            f"GET {adresse.path} HTTP/1.1\r\nHost: {adresse.hostname}:{adresse.port}\r\n"
            f"Upgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {cle}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n").encode())
        reponse = b""
        while b"\r\n\r\n" not in reponse:
            reponse += self.sock.recv(1)
        if b" 101 " not in reponse.split(b"\r\n")[0]:
            raise ConnectionError(f"Connexion DevTools refusée : {reponse[:80]!r}")
        self.compteur = 0

    def _lire(self, n: int) -> bytes:
        donnees = b""
        while len(donnees) < n:
            morceau = self.sock.recv(n - len(donnees))
            if not morceau:
                raise ConnectionError("Connexion DevTools fermée.")
            donnees += morceau
        return donnees

    def _recevoir(self) -> dict:
        message = b""
        while True:
            octet1, octet2 = self._lire(2)
            taille = octet2 & 0x7F
            if taille == 126:
                taille = struct.unpack(">H", self._lire(2))[0]
            elif taille == 127:
                taille = struct.unpack(">Q", self._lire(8))[0]
            message += self._lire(taille)
            if octet1 & 0x80:  # dernier fragment
                return json.loads(message)

    def appeler(self, methode: str, **params) -> dict:
        self.compteur += 1
        corps = json.dumps({"id": self.compteur, "method": methode, "params": params}).encode()
        masque = os.urandom(4)
        entete = bytes([0x81])
        if len(corps) < 126:
            entete += bytes([0x80 | len(corps)])
        elif len(corps) < 65536:
            entete += bytes([0x80 | 126]) + struct.pack(">H", len(corps))
        else:
            entete += bytes([0x80 | 127]) + struct.pack(">Q", len(corps))
        self.sock.sendall(entete + masque + bytes(b ^ masque[i % 4] for i, b in enumerate(corps)))
        while True:  # on ignore les événements jusqu'à la réponse attendue
            message = self._recevoir()
            if message.get("id") == self.compteur:
                if "error" in message:
                    raise RuntimeError(f"{methode} : {message['error']}")
                return message["result"]

    def evaluer(self, expression: str):
        return self.appeler("Runtime.evaluate", expression=expression,
                            returnByValue=True, awaitPromise=True)["result"].get("value")


def ouvrir_navigateur(navigateur: str, profil: str) -> tuple[subprocess.Popen, DevTools]:
    processus = subprocess.Popen([
        navigateur, "--headless=new", "--disable-gpu", "--no-first-run",
        "--no-default-browser-check", "--remote-debugging-port=0",
        f"--user-data-dir={profil}", "about:blank",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    fichier_port = Path(profil) / "DevToolsActivePort"
    for _ in range(300):
        if fichier_port.is_file() and fichier_port.read_text().strip():
            break
        time.sleep(0.1)
    else:
        processus.kill()
        raise SystemExit("Le navigateur n'a pas ouvert son port DevTools.")
    port = fichier_port.read_text().splitlines()[0]
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list") as reponse:
        pages = [c for c in json.load(reponse) if c["type"] == "page"]
    return processus, DevTools(pages[0]["webSocketDebuggerUrl"])


def imprimer(devtools: DevTools, url: str, cible: Path) -> None:
    devtools.appeler("Page.navigate", url=url)
    limite = time.monotonic() + DELAI_DIAGRAMMES
    while not devtools.evaluer("window.__diagrammesPrets === true"):
        if time.monotonic() > limite:
            raise SystemExit(f"{url} : les diagrammes ne sont pas prêts après {DELAI_DIAGRAMMES} s "
                             "(connexion Internet ?).")
        time.sleep(0.5)
    erreur = devtools.evaluer("window.__erreurDiagrammes || ''")
    if erreur:
        raise SystemExit(f"{url} : erreur Mermaid — {erreur}")
    devtools.evaluer("document.fonts.ready.then(() => true)")
    pdf = devtools.appeler("Page.printToPDF", printBackground=True, preferCSSPageSize=True,
                           displayHeaderFooter=False)
    cible.write_bytes(base64.b64decode(pdf["data"]))


def main() -> None:
    navigateur = trouver_navigateur()
    serveur = demarrer_serveur()
    port = serveur.server_address[1]
    profil = tempfile.mkdtemp(prefix="bankservices-pdf-")
    processus, devtools = ouvrir_navigateur(navigateur, profil)
    try:
        for nom, titre, langue, sens in DOCUMENTS:
            generer(nom, titre, langue, sens)
            cible = DOCS / f"{nom}.pdf"
            imprimer(devtools, f"http://127.0.0.1:{port}/{nom}.html", cible)
            print(f"Généré : {cible}  ({cible.stat().st_size // 1024} Ko)")
    finally:
        processus.terminate()
        processus.wait(timeout=30)
        serveur.shutdown()
        shutil.rmtree(profil, ignore_errors=True)


if __name__ == "__main__":
    main()
