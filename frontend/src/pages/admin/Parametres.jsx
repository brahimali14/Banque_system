import { useEffect, useState } from 'react'
import { api } from '../../api/client.js'
import { Alerte, Carte, Chargement } from '../../components/Interface.jsx'
import { useDonnees } from '../../hooks/useDonnees.js'
import { useLangue } from '../../i18n/Langue.jsx'

const LIBELLES = {
  seuil_superviseur_dzd: ['Seuil de double validation (DA)', 'Au-dessus, un superviseur doit approuver.'],
  validite_bordereau_heures: ['Validité des bordereaux (heures)', 'Après ce délai, le bordereau expire.'],
  validite_mdp_temporaire_jours: ['Validité du mot de passe temporaire (jours)', ''],
  tentatives_max_connexion: ['Tentatives de connexion avant verrouillage', ''],
}

const TACHES = [
  ['expirer-bordereaux', 'Expirer les bordereaux dépassés'],
  ['verser-interets', 'Verser les intérêts mensuels (épargne)'],
  ['frais-tenue-compte', 'Prélever les frais de tenue de compte'],
]

export default function Parametres() {
  const { t, erreur } = useLangue()
  const parametres = useDonnees('/api/admin/parametres')
  const taux = useDonnees('/api/admin/taux-change')
  const [valeurs, setValeurs] = useState({})
  const [valeursTaux, setValeursTaux] = useState({})
  const [message, setMessage] = useState(null)

  useEffect(() => { if (parametres.donnees) setValeurs(parametres.donnees) }, [parametres.donnees])
  useEffect(() => { if (taux.donnees) setValeursTaux(taux.donnees) }, [taux.donnees])

  const executer = async (action, succes) => {
    setMessage(null)
    try {
      const resultat = await action()
      setMessage({ type: 'succes', texte: typeof succes === 'function' ? succes(resultat) : succes })
    } catch (e) {
      setMessage({ type: 'erreur', texte: erreur(e) })
    }
  }

  if (parametres.chargement || taux.chargement) return <Chargement />

  return (
    <>
      <h1>{t('Paramètres')}</h1>
      <p className="sous-titre">{t('Valeurs fictives utilisées par le simulateur.')}</p>
      <Alerte type={message?.type} onFermer={() => setMessage(null)}>{message?.texte}</Alerte>
      <div className="grille-2">
        <Carte titre={t('Règles')}>
          <div className="formulaire">
            {Object.entries(LIBELLES).map(([cle, [libelle, aide]]) => (
              <div className="champ" key={cle}>
                <label htmlFor={cle}>{t(libelle)}</label>
                <div className="ligne-saisie">
                  <input id={cle} value={valeurs[cle] ?? ''} onChange={(e) => setValeurs((v) => ({ ...v, [cle]: e.target.value }))} />
                  <button className="bouton bouton-secondaire" onClick={() => executer(
                    () => api(`/api/admin/parametres/${cle}`, { methode: 'PUT', corps: { valeur: valeurs[cle] } }),
                    t('Paramètre enregistré.'),
                  )}>{t('Enregistrer')}</button>
                </div>
                {aide && <small>{t(aide)}</small>}
              </div>
            ))}
          </div>
        </Carte>
        <div>
          <Carte titre={t('Taux de change (1 unité = X DA)')}>
            <div className="formulaire">
              {['EUR', 'USD'].map((devise) => (
                <div className="champ" key={devise}>
                  <label htmlFor={devise}>{devise}</label>
                  <div className="ligne-saisie">
                    <input id={devise} value={valeursTaux[devise] ?? ''} onChange={(e) => setValeursTaux((v) => ({ ...v, [devise]: e.target.value }))} />
                    <button className="bouton bouton-secondaire" onClick={() => executer(
                      () => api(`/api/admin/taux-change/${devise}`, { methode: 'PUT', corps: { taux_vers_dzd: valeursTaux[devise] } }),
                      t('Taux enregistré.'),
                    )}>{t('Enregistrer')}</button>
                  </div>
                </div>
              ))}
            </div>
          </Carte>
          <Carte titre={t('Tâches du système')}>
            <p className="sous-titre">{t('Normalement automatiques, lancées ici à la main pour la démonstration.')}</p>
            <div className="formulaire">
              {TACHES.map(([nom, libelle]) => (
                <button key={nom} className="bouton bouton-secondaire" onClick={() => executer(
                  () => api(`/api/admin/taches/${nom}`, { methode: 'POST' }),
                  (r) => t('{tache} : {nombre} élément(s) traité(s).', { tache: t(libelle), nombre: r.elements_traites }),
                )}>{t(libelle)}</button>
              ))}
            </div>
          </Carte>
        </div>
      </div>
    </>
  )
}
