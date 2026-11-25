import { useState } from 'react'
import { Carte, Chargement, Tableau } from '../../components/Interface.jsx'
import { useDonnees } from '../../hooks/useDonnees.js'
import { useLangue } from '../../i18n/Langue.jsx'

export default function Audit() {
  const { t, date } = useLangue()
  const journal = useDonnees('/api/admin/audit?limite=500')
  const [filtre, setFiltre] = useState('')

  const motif = filtre.trim().toLowerCase()
  const lignes = (journal.donnees ?? []).filter((l) =>
    !motif || [l.action, l.utilisateur, l.cible, l.details].some((champ) => champ?.toLowerCase().includes(motif)),
  )

  return (
    <>
      <div className="entete-page">
        <div>
          <h1>{t("Journal d'audit")}</h1>
          <p className="sous-titre">{t('Qui a fait quoi, et quand.')}</p>
        </div>
        <button className="bouton bouton-secondaire" onClick={journal.recharger}>{t('Actualiser')}</button>
      </div>
      <Carte>
        <div className="filtres">
          <div className="champ champ-large">
            <label htmlFor="filtre">{t('Rechercher')}</label>
            <input id="filtre" placeholder={t('Action, utilisateur, numéro…')} value={filtre} onChange={(e) => setFiltre(e.target.value)} />
          </div>
        </div>
        {journal.chargement ? <Chargement /> : (
          <Tableau
            lignes={lignes}
            colonnes={[
              { cle: 'date', titre: t('Date'), rendu: (l) => date(l.date) },
              { cle: 'utilisateur', titre: t('Utilisateur'), rendu: (l) => <span className="code">{l.utilisateur ?? t('Système')}</span> },
              { cle: 'action', titre: t('Action'), rendu: (l) => <span className="code">{l.action}</span> },
              { cle: 'cible', titre: t('Cible'), rendu: (l) => <span className="code">{l.cible ?? ''}</span> },
              { cle: 'details', titre: t('Détails') },
            ]}
          />
        )}
      </Carte>
    </>
  )
}
