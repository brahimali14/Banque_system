// fonctionnel
import { enCentimes, formaterMontant } from './montants.js'

export const CREDITS = ['DEPOT', 'VIREMENT_RECU', 'INTERETS']
export const DEBITS = ['RETRAIT', 'VIREMENT_EMIS', 'FRAIS']

export const LIBELLES_TYPES = {
  DEPOT: 'Dépôt',
  RETRAIT: 'Retrait',
  VIREMENT_EMIS: 'Virement émis',
  VIREMENT_RECU: 'Virement reçu',
  FRAIS: 'Frais',
  INTERETS: 'Intérêts',
}

export const estCredit = (operation) => CREDITS.includes(operation.type)

export const filtrerParType = (operations, type) =>
  type ? operations.filter((op) => op.type === type) : operations

export const filtrerParPeriode = (operations, debut, fin) =>
  operations.filter((op) => {
    const jour = op.date.slice(0, 10)
    return (!debut || jour >= debut) && (!fin || jour <= fin)
  })

export const rechercher = (operations, texte) => {
  const motif = texte.trim().toLowerCase()
  if (!motif) return operations
  return operations.filter((op) =>
    [op.reference, op.libelle, op.compte_contrepartie ?? ''].some((champ) => champ.toLowerCase().includes(motif)),
  )
}

export const versLignes = (operations, langue = 'fr', locale = 'fr-FR') =>
  operations.map((op) => ({
    ...op,
    typeLibelle: LIBELLES_TYPES[op.type] ?? op.type,
    sens: estCredit(op) ? 'credit' : 'debit',
    montantAffiche: (estCredit(op) ? '+' : '-') + formaterMontant(op.montant, op.devise, langue),
    dateAffichee: new Date(op.date).toLocaleString(locale, { dateStyle: 'short', timeStyle: 'short' }),
  }))

export const totalCentimes = (operations) => operations.reduce((acc, op) => acc + enCentimes(op.montant), 0)

export const totauxParType = (operations) =>
  operations.reduce((acc, op) => ({ ...acc, [op.type]: (acc[op.type] ?? 0) + enCentimes(op.montant) }), {})

export const resume = (operations) => {
  const credits = totalCentimes(operations.filter(estCredit))
  const debits = totalCentimes(operations.filter((op) => !estCredit(op)))
  return {
    nombre: operations.length,
    depots: totalCentimes(filtrerParType(operations, 'DEPOT')),
    retraits: totalCentimes(filtrerParType(operations, 'RETRAIT')),
    credits,
    debits,
    variation: credits - debits,
  }
}

export const parMois = (operations) => {
  const mois = operations.reduce((acc, op) => {
    const cle = op.date.slice(0, 7)
    const courant = acc[cle] ?? { mois: cle, credits: 0, debits: 0 }
    const centimes = enCentimes(op.montant)
    return {
      ...acc,
      [cle]: estCredit(op)
        ? { ...courant, credits: courant.credits + centimes }
        : { ...courant, debits: courant.debits + centimes },
    }
  }, {})
  return Object.values(mois)
    .sort((a, b) => a.mois.localeCompare(b.mois))
    .map((m) => ({ ...m, credits: m.credits / 100, debits: m.debits / 100 }))
}
