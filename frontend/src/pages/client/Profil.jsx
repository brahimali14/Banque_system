import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api/client.js'
import { Alerte, Carte, Chargement } from '../../components/Interface.jsx'
import { useDonnees } from '../../hooks/useDonnees.js'
import { useLangue } from '../../i18n/Langue.jsx'

export default function Profil() {
  const { t, erreur } = useLangue()
  const profil = useDonnees('/api/moi/profil')
  const [coordonnees, setCoordonnees] = useState({ telephone: '', email: '', adresse: '' })
  const [message, setMessage] = useState(null)

  useEffect(() => {
    if (profil.donnees) {
      const { telephone, email, adresse } = profil.donnees
      setCoordonnees({ telephone, email: email ?? '', adresse: adresse ?? '' })
    }
  }, [profil.donnees])

  if (profil.chargement) return <Chargement />
  if (!profil.donnees) return <Alerte type="erreur">{erreur(profil.erreur)}</Alerte>
  const p = profil.donnees

  const changer = (e) => setCoordonnees((c) => ({ ...c, [e.target.name]: e.target.value }))
  const enregistrer = async (evenement) => {
    evenement.preventDefault()
    try {
      await api('/api/moi/profil', { methode: 'PUT', corps: coordonnees })
      setMessage({ type: 'succes', texte: t('Coordonnées enregistrées.') })
    } catch (e) {
      setMessage({ type: 'erreur', texte: erreur(e) })
    }
  }

  return (
    <>
      <h1>{t('Mon profil')}</h1>
      <p className="sous-titre">{p.nom_complet} · {t("Nom d'utilisateur")} <span className="code">{p.login}</span></p>
      <Alerte type={message?.type} onFermer={() => setMessage(null)}>{message?.texte}</Alerte>
      <div className="grille-2">
        <Carte titre={t('Mes coordonnées')}>
          <form className="formulaire" onSubmit={enregistrer}>
            <div className="champ"><label htmlFor="telephone">{t('Téléphone')}</label><input id="telephone" dir="ltr" name="telephone" value={coordonnees.telephone} onChange={changer} required /></div>
            <div className="champ"><label htmlFor="email">{t('E-mail')}</label><input id="email" dir="ltr" name="email" type="email" value={coordonnees.email} onChange={changer} /></div>
            <div className="champ"><label htmlFor="adresse">{t('Adresse')}</label><input id="adresse" name="adresse" value={coordonnees.adresse} onChange={changer} /></div>
            <button className="bouton">{t('Enregistrer')}</button>
          </form>
        </Carte>
        <Carte titre={t('Sécurité')}>
          <p>{t("Nom, prénom et n° d'identité ne peuvent être modifiés que par votre agence.")}</p>
          <Link className="bouton bouton-secondaire" to="/changer-mot-de-passe">{t('Changer mon mot de passe')}</Link>
        </Carte>
      </div>
    </>
  )
}
