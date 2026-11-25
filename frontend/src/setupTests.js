import '@testing-library/jest-dom/vitest'

// Node 25 expose son propre localStorage (sans fichier, donc inutilisable) qui masque
// celui de jsdom : on le remplace par un stockage en mémoire pour les tests.
class StockageMemoire {
  #donnees = new Map()
  get length() { return this.#donnees.size }
  key(i) { return [...this.#donnees.keys()][i] ?? null }
  getItem(cle) { return this.#donnees.has(cle) ? this.#donnees.get(cle) : null }
  setItem(cle, valeur) { this.#donnees.set(cle, String(valeur)) }
  removeItem(cle) { this.#donnees.delete(cle) }
  clear() { this.#donnees.clear() }
}

for (const nom of ['localStorage', 'sessionStorage']) {
  if (typeof globalThis[nom]?.setItem !== 'function') {
    Object.defineProperty(globalThis, nom, { value: new StockageMemoire(), configurable: true })
  }
}
