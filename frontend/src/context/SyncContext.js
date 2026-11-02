import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react'
import { syncPlatform, checkSyncStatus, getWishlistPrices } from '../services/api'
import { useToast } from './ToastContext'

const SyncContext = createContext()

/**
 * Stato globale delle sincronizzazioni: un solo sync attivo alla volta,
 * condiviso da tutte le pagine (MyLibrary, SyncJobs, ...), con polling
 * automatico dello stato e statistiche per i badge del sidebar.
 */
export function SyncProvider({ children }) {
  const { notify } = useToast()
  const [activeSync, setActiveSync] = useState(null) // { platform, jobId, status }
  const [startingPlatform, setStartingPlatform] = useState(null)
  const [stats, setStats] = useState({ wishlistCount: 0, priceAlerts: 0 })
  const timerRef = useRef(null)

  const loadStats = useCallback(async () => {
    // Su /login (o senza token) non serve interrogare l'API: evita 401 → redirect → loop
    if (!localStorage.getItem('token')) return
    try {
      const data = await getWishlistPrices()
      const items = data.items || []
      setStats({
        wishlistCount: items.length,
        priceAlerts: items.filter(i => i.alert_triggered).length,
      })
    } catch (err) {
      // Silenzioso: i badge del sidebar non sono critici
    }
  }, [])

  useEffect(() => {
    loadStats()
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [loadStats])

  const isSyncing = activeSync !== null || startingPlatform !== null

  const startSync = useCallback(
    async platform => {
      if (isSyncing) return
      setStartingPlatform(platform)
      try {
        const data = await syncPlatform(platform)
        setActiveSync({ platform, jobId: data.job_id, status: 'queued' })
        notify(`Sincronizzazione ${platform} avviata`, 'info')
        if (timerRef.current) clearInterval(timerRef.current)
        timerRef.current = setInterval(async () => {
          try {
            const statusData = await checkSyncStatus(data.job_id)
            const status = statusData.status
            setActiveSync(prev => (prev ? { ...prev, status } : prev))
            if (status === 'success' || status === 'fail') {
              clearInterval(timerRef.current)
              timerRef.current = null
              setActiveSync(null)
              if (status === 'success') {
                notify(`Sincronizzazione ${platform} completata`, 'success')
              } else {
                notify(`Sincronizzazione ${platform} fallita`, 'error')
              }
              loadStats()
            }
          } catch (err) {
            clearInterval(timerRef.current)
            timerRef.current = null
            setActiveSync(null)
          }
        }, 3000)
      } catch (err) {
        notify(err.message || `Errore nell'avvio della sync ${platform}`, 'error')
      } finally {
        setStartingPlatform(null)
      }
    },
    [isSyncing, notify, loadStats]
  )

  return (
    <SyncContext.Provider
      value={{ activeSync, isSyncing, startingPlatform, startSync, stats, loadStats }}
    >
      {children}
    </SyncContext.Provider>
  )
}

export function useSync() {
  return useContext(SyncContext)
}
