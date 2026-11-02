import React, { createContext, useContext, useState, useCallback, useRef } from 'react'

const ToastContext = createContext()

/**
 * Sistema di notifiche toast (Windmill 0.3.1 non li espone).
 * Uso: const { notify } = useToast(); notify('Salvato', 'success')
 */
export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const idRef = useRef(0)

  const notify = useCallback((message, type = 'info', duration = 4000) => {
    const id = ++idRef.current
    setToasts(prev => [...prev, { id, message, type }])
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id))
    }, duration)
  }, [])

  return (
    <ToastContext.Provider value={{ notify }}>
      {children}
      {/* Toast center: fisso in alto a destra, sopra ogni contenuto */}
      <div
        className="fixed top-4 right-4 z-50 flex flex-col items-end space-y-2 w-72 max-w-[calc(100vw-2rem)]"
        aria-live="polite"
        aria-atomic="false"
      >
        {toasts.map(t => (
          <div
            key={t.id}
            role="status"
            className={`w-full px-4 py-3 rounded-lg shadow-lg text-sm text-white break-words ${
              t.type === 'success'
                ? 'bg-green-600'
                : t.type === 'error'
                ? 'bg-red-600'
                : 'bg-purple-600'
            }`}
          >
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  return useContext(ToastContext)
}
