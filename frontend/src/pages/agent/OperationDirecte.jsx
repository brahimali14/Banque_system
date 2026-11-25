import { useState } from 'react'
import { api, ouvrirPdf } from '../../api/client.js'
import { Alerte, Carte, Montant } from '../../components/Interface.jsx'
import { useLangue } from '../../i18n/Langue.jsx'
import { erreurMontant } from '../../utils/montants.js'

export default function OperationDirecte() {
  const { t, erreur: traduireErreur, montant: formater } = useLangue()
  const [numero, setNumero] = useState('')
  const [compte, setCompte] = useState(null)
  const [type, setType] = useState('DEPOT')
  const [montant, setMontant] = useState('')
  const [message, setMessage] = useState(null)
  const [transaction, setTransaction] = useState(null)

  const chercherCompte = async () => {
    setCompte(null)
    if (!numero.trim()) return
    try {
      setCompte(await api(`/api/comptes/${numero.trim().toUpperCase()}`))
    } catch (e) {
      setMessage({ type: 'erreur', texte: traduireErreur(e) })
    }
  }

  const valider = async (evenement) => {
    evenement.preventDefault()
    setMessage(null)
    setTransaction(null)
    const probleme = erreurMontant(montant)
    if (probleme) return setMessage({ type: 'erreur', texte: t(probleme) })
    try {
      const resultat = await api('/api/agent/operations', {
        methode: 'POST',
        corps: { numero_compte: compte.numero, type, montant },
      })
      setTransaction(resultat)
      setMessage({ type: 'succes', texte: t('Opération enregistrée. Nouveau solde : {solde}', { solde: formater(resultat.solde_apres, resultat.devise) }) })
      setMontant('')
      chercherCompte()
    } catch (e) {
      setMessage({ type: 'erreur', texte: traduireErreur(e) })
    }
  }

  return (
    <>
      <h1>{t('Opération directe')}</h1>
      <p className="sous-titre">{t('Dépôt ou retrait pour un client venu sans bordereau.')}</p>
      <Alerte type={message?.type} onFermer={() => setMessage(null)}>{message?.texte}</Alerte>
      {transaction && (
        <p>
          <button className="bouton bouton-secondaire" onClick={() => ouvrirPdf(`/api/transactions/${transaction.reference}/recu.pdf`)}>
            {t('Imprimer le reçu')}
          </button>
        </p>
      )}
      <Carte>
        <form className="formulaire" onSubmit={valider}>
          <div className="champ">
            <label htmlFor="numero">{t('Numéro de compte')}</label>
            <input id="numero" className="code" placeholder="BS-CC-000001" value={numero}
              onChange={(e) => setNumero(e.target.value)} onBlur={chercherCompte} />
            {compte && (
              <small>
                {compte.titulaire} · {t(compte.libelle)} · {t('Disponible')} : <Montant valeur={compte.solde_disponible} devise={compte.devise} />
              </small>
            )}
          </div>
          <div className="choix" role="radiogroup" aria-label={t("Type d'opération")}>
            <label><input type="radio" name="type" value="DEPOT" checked={type === 'DEPOT'} onChange={(e) => setType(e.target.value)} /> {t('Dépôt')}</label>
            <label><input type="radio" name="type" value="RETRAIT" checked={type === 'RETRAIT'} onChange={(e) => setType(e.target.value)} /> {t('Retrait')}</label>
          </div>
          <div className="champ">
            <label htmlFor="montant">{t('Montant')} {compte ? `(${compte.devise})` : ''}</label>
            <input id="montant" inputMode="decimal" value={montant} onChange={(e) => setMontant(e.target.value)} />
          </div>
          <button className="bouton bouton-grand" disabled={!compte}>{t('Valider')}</button>
        </form>
      </Carte>
    </>
  )
}
