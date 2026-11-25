"""Génère les pages HTML de la documentation à partir des fichiers Markdown de docs/ :
ETUDE_SYSTEME, RAPPORT_PARADIGMES (français) et RAPPORT_PARADIGMES_AR (arabe, de droite à gauche).

Le HTML affiche le Markdown et dessine les diagrammes Mermaid dans le navigateur
(bibliothèques chargées depuis un CDN, une connexion Internet est donc nécessaire).

Usage :  python docs/build_html.py   (régénère les trois pages)
"""
from pathlib import Path

DOCS = Path(__file__).resolve().parent

# (fichier Markdown, titre de l'onglet, langue, sens de lecture)
DOCUMENTS = [
    ("ETUDE_SYSTEME", "BankServices — Étude et conception", "fr", "ltr"),
    ("RAPPORT_PARADIGMES", "BankServices — Rapport : paradigmes de programmation", "fr", "ltr"),
    ("RAPPORT_PARADIGMES_AR", "BankServices — تقرير شرح أنماط البرمجة", "ar", "rtl"),
]

TEMPLATE = """<!DOCTYPE html>
<html lang="__LANG__" dir="__DIR__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITRE__</title>
<style>
  :root { --bleu: #1f4e9e; --gris: #f4f6fa; --bord: #d5dbe5; }
  * { box-sizing: border-box; }
  body { margin: 0; font-family: "Segoe UI", Roboto, Arial, sans-serif; color: #1d2433;
         background: #fff; line-height: 1.55; }
  main { max-width: 1180px; margin: 0 auto; padding: 32px 28px 80px; }
  h1 { color: var(--bleu); border-bottom: 3px solid var(--bleu); padding-bottom: 8px; }
  h2 { color: var(--bleu); margin-top: 48px; border-bottom: 1px solid var(--bord); padding-bottom: 6px; }
  h3 { margin-top: 30px; }
  a { color: var(--bleu); }
  blockquote { margin: 12px 0; padding: 8px 16px; background: var(--gris);
               border-left: 4px solid var(--bleu); color: #3b4456; }
  table { border-collapse: collapse; width: 100%; margin: 14px 0; font-size: 14px; }
  th, td { border: 1px solid var(--bord); padding: 7px 10px; text-align: left; vertical-align: top; }
  th { background: var(--bleu); color: #fff; }
  tr:nth-child(even) td { background: var(--gris); }
  code { background: #eef1f6; padding: 1px 5px; border-radius: 4px; font-size: 13px; }
  pre { background: #1e2433; color: #e6e9ef; padding: 14px; border-radius: 8px; overflow-x: auto; }
  pre code { background: none; color: inherit; padding: 0; }
  .mermaid { background: #fff; border: 1px solid var(--bord); border-radius: 10px;
             padding: 16px; margin: 16px 0; overflow-x: auto; text-align: center; }
  @page { size: A4; margin: 16mm 14mm; }
  @media print {
    html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    main { max-width: none; padding: 0; }
    body { font-size: 13px; }
    h2 { margin-top: 28px; }
    h2, h3 { break-after: avoid; }
    .mermaid, tr, blockquote { break-inside: avoid; }
    .mermaid svg { max-width: 100% !important; max-height: 225mm; height: auto; }
    pre { font-size: 9.5px; white-space: pre-wrap; word-break: break-word; overflow: visible; }
    pre code { font-size: inherit; }
    table { font-size: 12px; }
  }
  /* arabe : lecture de droite à gauche, le code et les diagrammes restent de gauche à droite */
  [dir="rtl"] body { font-family: "Segoe UI", Tahoma, "Noto Naskh Arabic", Arial, sans-serif; line-height: 1.8; }
  [dir="rtl"] th, [dir="rtl"] td { text-align: right; }
  [dir="rtl"] blockquote { border-left: 0; border-right: 4px solid var(--bleu); }
  [dir="rtl"] pre, [dir="rtl"] .mermaid { direction: ltr; text-align: left; }
  [dir="rtl"] code { unicode-bidi: isolate; }
</style>
</head>
<body>
<main id="contenu">Chargement…</main>
<script id="source" type="text/markdown">__MARKDOWN__</script>
<script src="https://cdn.jsdelivr.net/npm/marked@15/marked.min.js"></script>
<script type="module">
  import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";

  const md = document.getElementById("source").textContent;
  const main = document.getElementById("contenu");
  main.innerHTML = marked.parse(md);

  // Ancres des titres (même format que GitHub) pour que le sommaire fonctionne.
  main.querySelectorAll("h1, h2, h3").forEach((h) => {
    h.id = h.textContent.trim().toLowerCase()
      .replace(/[^\\p{L}\\p{N}\\s-]/gu, "").replace(/\\s/g, "-");
  });

  // Les blocs ```mermaid deviennent des diagrammes.
  main.querySelectorAll("pre > code.language-mermaid").forEach((code) => {
    const div = document.createElement("div");
    div.className = "mermaid";
    div.textContent = code.textContent;
    code.parentElement.replaceWith(div);
  });

  mermaid.initialize({ startOnLoad: false, theme: "default",
                       flowchart: { useMaxWidth: true, htmlLabels: true },
                       gantt: { useWidth: 1100 } });
  try {
    await mermaid.run({ querySelector: ".mermaid" });
  } catch (erreur) {
    window.__erreurDiagrammes = String(erreur);
  } finally {
    window.__diagrammesPrets = true;  // attendu par build_pdf.py avant l'impression
  }
</script>
</body>
</html>
"""


def generer(nom: str, titre: str, langue: str, sens: str) -> Path:
    source, cible = DOCS / f"{nom}.md", DOCS / f"{nom}.html"
    markdown = source.read_text(encoding="utf-8")
    if "</script" in markdown.lower():
        raise ValueError(f"{source.name} ne doit pas contenir de balise </script>.")
    page = (TEMPLATE.replace("__TITRE__", titre).replace("__LANG__", langue)
            .replace("__DIR__", sens).replace("__MARKDOWN__", markdown))
    cible.write_text(page, encoding="utf-8")
    return cible


def main() -> None:
    for document in DOCUMENTS:
        print(f"Généré : {generer(*document)}")


if __name__ == "__main__":
    main()
