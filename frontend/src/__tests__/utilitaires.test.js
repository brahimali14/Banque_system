import { describe, expect, it } from 'vitest'
import { estRobuste, verifierRegles } from '../utils/motDePasse.js'
import { apercuFrais, depuisCentimes, enCentimes, erreurMontant, formaterMontant } from '../utils/montants.js'
import { ALPHABET, cleControle, etatSaisie, normaliser } from '../utils/numeros.js'
import { filtrerParPeriode, filtrerParType, parMois, rechercher, resume, totauxParType, versLignes } from '../utils/stats.js'

const OPERATIONS = Object.freeze([
  { reference: 'TRX-1', type: 'DEPOT', montant: '1000.10', devise: 'DZD', date: '2026-09-01T10:00:00', libelle: 'Dépôt' },
  { reference: 'TRX-2', type: 'RETRAIT', montant: '200.20', devise: 'DZD', date: '2026-10-01T10:00:00', libelle: 'Retrait' },
  { reference: 'TRX-3', type: 'DEPOT', montant: '300.30', devise: 'DZD', date: '2026-11-01T10:00:00', libelle: 'Virement de BS-CC-000002' },
  { reference: 'TRX-4', type: 'FRAIS', montant: '50.00', devise: 'DZD', date: '2026-11-02T10:00:00', libelle: 'Frais' },
])

describe('montants exacts', () => {
  it('convertit en centimes sans erreur de virgule flottante', () => {
    expect(enCentimes('0.1') + enCentimes('0.2')).toBe(enCentimes('0.3'))
    expect(enCentimes('12000.5')).toBe(1200050)
    expect(enCentimes('12 000,50')).toBe(1200050)
    expect(enCentimes('abc')).toBeNull()
    expect(enCentimes('1.234')).toBeNull()
    expect(depuisCentimes(-1205)).toBe('-12.05')
  })

  it('formate selon la langue', () => {
    expect(formaterMontant('12000.5', 'DZD')).toBe('12 000,50 DA')
    expect(formaterMontant('12000.5', 'DZD', 'en')).toBe('12,000.50 DZD')
    expect(formaterMontant('12000.5', 'DZD', 'ar')).toBe('12,000.50 د.ج')
    expect(formaterMontant(-45, 'EUR')).toBe('-45,00 €')
  })

  it('valide la saisie', () => {
    expect(erreurMontant('')).toBe('Saisissez un montant.')
    expect(erreurMontant('-5')).toBe('Le montant doit être strictement positif.')
    expect(erreurMontant('10.555')).toBe('Montant invalide (2 décimales au maximum).')
    expect(erreurMontant('10.55')).toBeNull()
  })

  it('estime les frais comme le serveur', () => {
    expect(apercuFrais('COURANT', enCentimes('1000'))).toBe(5000) // minimum 50 DA
    expect(apercuFrais('COURANT', enCentimes('40000'))).toBe(20000) // 0,5 %
    expect(apercuFrais('COURANT', enCentimes('1000000'))).toBe(100000) // maximum 1 000 DA
    expect(apercuFrais('DEVISE', enCentimes('300'))).toBe(300) // 1 %
    expect(apercuFrais('EPARGNE', enCentimes('300'))).toBe(0)
  })
})

describe('statistiques : filter, map, reduce', () => {
  it('filtre par type, période et texte', () => {
    expect(filtrerParType(OPERATIONS, 'DEPOT').map((o) => o.reference)).toEqual(['TRX-1', 'TRX-3'])
    expect(filtrerParType(OPERATIONS, '')).toHaveLength(4)
    expect(filtrerParPeriode(OPERATIONS, '2026-10-01', '2026-11-01').map((o) => o.reference)).toEqual(['TRX-2', 'TRX-3'])
    expect(rechercher(OPERATIONS, 'bs-cc').map((o) => o.reference)).toEqual(['TRX-3'])
  })

  it('cumule en centimes exacts', () => {
    expect(totauxParType(OPERATIONS)).toEqual({ DEPOT: 130040, RETRAIT: 20020, FRAIS: 5000 })
    expect(resume(OPERATIONS)).toMatchObject({ nombre: 4, depots: 130040, retraits: 20020, variation: 105020 })
  })

  it('prépare les lignes et les mois du graphique', () => {
    const lignes = versLignes(OPERATIONS.slice(0, 2))
    expect(lignes[0]).toMatchObject({ typeLibelle: 'Dépôt', sens: 'credit', montantAffiche: '+1 000,10 DA' })
    expect(lignes[1].montantAffiche).toBe('-200,20 DA')
    expect(parMois(OPERATIONS)).toEqual([
      { mois: '2026-09', credits: 1000.1, debits: 0 },
      { mois: '2026-10', credits: 0, debits: 200.2 },
      { mois: '2026-11', credits: 300.3, debits: 50 },
    ])
  })

  it('ne modifie jamais les données reçues', () => {
    const copie = structuredClone(OPERATIONS)
    resume(OPERATIONS)
    versLignes(OPERATIONS)
    parMois(OPERATIONS)
    expect(OPERATIONS).toEqual(copie)
  })
})

describe('numéro de bordereau', () => {
  it('calcule la même clé que le serveur Python', () => {
    expect(cleControle('K7M29QX')).toBe('B') // RET-K7M2-9QXB côté backend
    expect(cleControle('H4TW82N')).toBe('J') // DEP-H4TW-82NJ côté backend
  })

  it('suit la saisie caractère par caractère', () => {
    expect(etatSaisie('')).toBe('vide')
    expect(etatSaisie('RET-K7M')).toBe('incomplet')
    expect(etatSaisie('ret k7m2 9qxb')).toBe('valide')
    expect(etatSaisie('RET-K7M2-9QXA')).toBe('invalide')
    expect(normaliser(' ret-k7m29qxb ')).toBe('RET-K7M2-9QXB')
  })

  it('détecte toute faute de frappe sur un caractère', () => {
    const corps = 'K7M29QXB'
    for (let i = 0; i < corps.length; i++) {
      for (const remplacant of ALPHABET) {
        if (remplacant === corps[i]) continue
        const faux = corps.slice(0, i) + remplacant + corps.slice(i + 1)
        expect(etatSaisie(`RET${faux}`)).toBe('invalide')
      }
    }
  })
})

describe('mot de passe', () => {
  it('vérifie chaque règle', () => {
    expect(verifierRegles('abc').filter((r) => r.ok).map((r) => r.id)).toEqual(['minuscule'])
    expect(estRobuste('Solide2026')).toBe(true)
    expect(estRobuste('solide2026')).toBe(false)
  })
})
