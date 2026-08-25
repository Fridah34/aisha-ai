import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

import { AuthProvider } from './hooks/useAuth'
import { WebSocketProvider } from './context/WebSocketContext'
import { ToastProvider } from './context/ToastContext'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <AuthProvider>
      <WebSocketProvider>
        <ToastProvider>
          <App />
        </ToastProvider>
      </WebSocketProvider>
    </AuthProvider>
  </StrictMode>,
)
