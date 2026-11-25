import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App.jsx'
import { FournisseurSession } from './auth/Session.jsx'
import { FournisseurLangue } from './i18n/Langue.jsx'
import './index.css'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <FournisseurLangue>
        <FournisseurSession>
          <App />
        </FournisseurSession>
      </FournisseurLangue>
    </BrowserRouter>
  </StrictMode>,
)
