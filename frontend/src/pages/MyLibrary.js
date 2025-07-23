import React, { useState, useEffect } from 'react'
import PageTitle from '../components/Typography/PageTitle'
import SectionTitle from '../components/Typography/SectionTitle'
import {
  Table,
  TableHeader,
  TableCell,
  TableBody,
  TableRow,
  TableFooter,
  TableContainer,
  Badge,
  Button,
  Pagination,
  Select,
  Modal,
  ModalHeader,
  ModalBody,
  ModalFooter,
} from '@windmill/react-ui'
import { TrashIcon } from '../icons'
import InfoCard from '../components/Cards/InfoCard'
import RoundIcon from '../components/RoundIcon'
import { GamesIcon, TrophyIcon, PlayIcon, StarIcon } from '../icons'
import { getUserLibrary, getUserPlatformStats, syncPlatform, removeGameFromLibrary, checkSyncStatus, getConsoleNames } from '../services/api'


function MyLibrary() {
  // Stati per i giochi
  const [games, setGames] = useState([])
  const [page, setPage] = useState(1)
  const [totalResults, setTotalResults] = useState(0)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  
  // Stati per i filtri
  const [selectedPlatform, setSelectedPlatform] = useState('')
  const [sortBy, setSortBy] = useState('name')
  const [sortOrder, setSortOrder] = useState('asc')
  
  // Stati per le modal
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false)
  const [selectedGame, setSelectedGame] = useState(null)
  // Nuovi stati per la selezione console
  const [selectedConsoleToRemove, setSelectedConsoleToRemove] = useState(null)
  const [showConsoleSelectionModal, setShowConsoleSelectionModal] = useState(false)
  
  // Stati per loading e sincronizzazione
  const [isSyncing, setIsSyncing] = useState(false)
  const [syncStatus, setSyncStatus] = useState('')
  const [syncJobId, setSyncJobId] = useState(null)
  
  // Statistiche
  const [stats, setStats] = useState({
    totalGames: 0,
    totalTrophies: 0,
    totalPlayTime: 0,
    completedGames: 0
  })

  const resultsPerPage = 10

  // Cache per i nomi delle console
  const [consoleNamesCache, setConsoleNamesCache] = useState({})

  // Funzione generica per ottenere il nome della console
  const getConsoleName = async (consoleCode) => {
    // Se consoleCode è già una stringa (nome console), restituiscilo direttamente
    if (typeof consoleCode === 'string') {
      return consoleCode
    }
    
    // Se è un numero (ID console), controlla la cache
    if (consoleNamesCache[consoleCode]) {
      return consoleNamesCache[consoleCode]
    }
    
    // Se non è in cache, recupera dal database
    try {
      const response = await getConsoleNames([consoleCode])
      const consoleName = response.console_names[consoleCode] || `Console ${consoleCode}`
      
      // Aggiorna la cache
      setConsoleNamesCache(prev => ({
        ...prev,
        [consoleCode]: consoleName
      }))
      
      return consoleName
    } catch (error) {
      console.error('Error getting console name:', error)
      return `Console ${consoleCode}`
    }
  }

  // Versione sincrona per il rendering (usa solo la cache)
  const getConsoleNameSync = (consoleCode) => {
    // Se consoleCode è già una stringa (nome console), restituiscilo direttamente
    if (typeof consoleCode === 'string') {
      return consoleCode
    }
    
    // Se è un numero (ID console), controlla la cache
    if (consoleNamesCache[consoleCode]) {
      return consoleNamesCache[consoleCode]
    }
    
    // Se non è in cache, restituisci un placeholder
    return `Console ${consoleCode}`
  }

  // Funzione per renderizzare le console come array (versione sincrona per la cache)
  const renderConsoles = (game) => {
    const consoles = game.consoles || []
    
    if (consoles.length === 0) {
      return <span className="text-gray-400">Nessuna console</span>
    }
    
    return (
      <div className="flex flex-wrap gap-1">
        {consoles.map((console, idx) => (
          <Badge key={idx} type="success">
            {getConsoleNameSync(console)}
          </Badge>
        ))}
      </div>
    )
  }

  // Funzione per caricare i nomi delle console
  const loadConsoleNames = async (games) => {
    const consoleIds = []
    
    // Raccogli tutti gli ID delle console dai giochi
    games.forEach(game => {
      if (game.consoles && Array.isArray(game.consoles)) {
        game.consoles.forEach(consoleId => {
          if (typeof consoleId === 'number' && !consoleNamesCache[consoleId]) {
            consoleIds.push(consoleId)
          }
        })
      }
    })
    
    // Se ci sono nuovi ID, recuperali dal database
    if (consoleIds.length > 0) {
      try {
        const uniqueIds = [...new Set(consoleIds)]
        const response = await getConsoleNames(uniqueIds)
        
        setConsoleNamesCache(prev => ({
          ...prev,
          ...response.console_names
        }))
      } catch (error) {
        console.error('Error loading console names:', error)
      }
    }
  }

  // Funzione per caricare i giochi
  const fetchGames = async () => {
    setIsLoading(true)
    setError('')
    try {
      // Usa la funzione API per ottenere la libreria utente
      const data = await getUserLibrary({
        page,
        limit: resultsPerPage,
        sort_by: sortBy,
        sort_order: sortOrder,
        platform: selectedPlatform || undefined
      })
      
      // Assicurati che library sia sempre un array
      const gamesArray = Array.isArray(data.library) ? data.library : []
      setGames(gamesArray)
      setTotalResults(data.pagination?.total_count || 0)
      
      // Carica i nomi delle console
      await loadConsoleNames(gamesArray)
      
      // Aggiorna le statistiche
      try {
        const platformStats = await getUserPlatformStats()
        
        // Usa la struttura corretta delle statistiche
        const totalStats = platformStats.total_stats || {}
        
        setStats({
          totalGames: totalStats.total_games || 0,
          totalTrophies: totalStats.total_trophies || 0,
          totalPlayTime: totalStats.total_play_time || 0,
          completedGames: totalStats.completed_games || 0
        })
      } catch (statsError) {
        console.error('Errore nel caricamento delle statistiche:', statsError)
        // Mantieni le statistiche di default in caso di errore
      }
    } catch (err) {
      setError('Errore durante il caricamento dei giochi: ' + err.message)
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }

  // Carica i giochi quando cambiano i filtri
  useEffect(() => {
    fetchGames()
  }, [page, selectedPlatform, sortBy, sortOrder])

  // Ascolta gli eventi di modifica della libreria
  useEffect(() => {
    const handleLibraryChange = () => {
      // Aggiorna le statistiche
      const updateStats = async () => {
        try {
          const platformStats = await getUserPlatformStats()
          const totalStats = platformStats.total_stats || {}
          setStats({
            totalGames: totalStats.total_games || 0,
            totalTrophies: totalStats.total_trophies || 0,
            totalPlayTime: totalStats.total_play_time || 0,
            completedGames: totalStats.completed_games || 0
          })
        } catch (statsError) {
          console.error('Errore nel caricamento delle statistiche:', statsError)
        }
      }
      updateStats()
    }

    // Aggiungi l'event listener
    window.addEventListener('gameLibraryChanged', handleLibraryChange)

    // Rimuovi l'event listener quando il componente viene smontato
    return () => {
      window.removeEventListener('gameLibraryChanged', handleLibraryChange)
    }
  }, [])

  // Gestione cambio pagina
  const onPageChange = (p) => {
    setPage(p)
  }

  // Funzione per controllare lo stato della sincronizzazione
  const checkSyncStatusLocal = async (jobId) => {
    try {
      const data = await checkSyncStatus(jobId)
      return data.status
    } catch (error) {
      console.error('Errore nel controllo dello stato di sincronizzazione:', error)
      return 'error'
    }
  }

  // Funzione per monitorare la sincronizzazione
  const monitorSync = async (jobId) => {
    const maxAttempts = 60 // 5 minuti (5 secondi * 60)
    let attempts = 0
    
    const checkStatus = async () => {
      attempts++
      const status = await checkSyncStatusLocal(jobId)
      
      if (status === 'completed' || status === 'success') {
        setSyncStatus('Sincronizzazione completata! Nota: Se non vedi achievement/trofei, verifica che il tuo profilo Steam sia pubblico.')
        setIsSyncing(false)
        setSyncJobId(null)
        // Ricarica i dati
        await fetchGames()
        setTimeout(() => setSyncStatus(''), 5000) // Nascondi messaggio dopo 5 secondi
        return
      } else if (status === 'failed' || status === 'error') {
        setSyncStatus('Errore durante la sincronizzazione')
        setIsSyncing(false)
        setSyncJobId(null)
        setTimeout(() => setSyncStatus(''), 5000) // Nascondi messaggio dopo 5 secondi
        return
      } else if (attempts >= maxAttempts) {
        setSyncStatus('Timeout: la sincronizzazione sta impiegando troppo tempo')
        setIsSyncing(false)
        setSyncJobId(null)
        setTimeout(() => setSyncStatus(''), 5000)
        return
      }
      
      // Continua a controllare ogni 5 secondi
      setTimeout(checkStatus, 5000)
    }
    
    checkStatus()
  }

  // Sincronizza con una piattaforma
  const handleSyncPlatform = async (platform) => {
    try {
      setIsSyncing(true)
      setSyncStatus(`Avvio sincronizzazione con ${platform}...`)
      
      const data = await syncPlatform(platform)
      setSyncJobId(data.job_id)
      setSyncStatus(`Sincronizzazione avviata! Job ID: ${data.job_id}`)
      
      // Inizia il monitoraggio
      monitorSync(data.job_id)
      
    } catch (err) {
      setError(`Errore durante la sincronizzazione con ${platform}: ${err.message}`)
      setIsSyncing(false)
      setSyncStatus('')
    }
  }

  // Gestione eliminazione gioco
  const handleDeleteGame = (game) => {
    setSelectedGame(game)
    
    // Se il gioco ha più console, mostra il modal di selezione console
    if (game.consoles && game.consoles.length > 1) {
      setShowConsoleSelectionModal(true)
    } else {
      // Se ha una sola console o nessuna, mostra direttamente il modal di conferma
      setIsDeleteModalOpen(true)
    }
  }

  // Gestione conferma eliminazione
  const handleConfirmDelete = async () => {
    if (!selectedGame) return

    try {
      // Se è stata selezionata una console specifica, rimuovi solo quella console
      if (selectedConsoleToRemove) {
        await removeGameFromLibrary(selectedGame.game_id, selectedConsoleToRemove)
      } else {
        // Altrimenti rimuovi l'intero gioco (comportamento legacy)
        await removeGameFromLibrary(selectedGame.game_id, null)
      }
      
      // Ricarica i giochi per mostrare le modifiche
      await fetchGames()
      
      setIsDeleteModalOpen(false)
      setShowConsoleSelectionModal(false)
      setSelectedGame(null)
      setSelectedConsoleToRemove(null)
    } catch (err) {
      setError('Errore durante la rimozione del gioco: ' + err.message)
    }
  }

  const handleConsoleSelection = (consoleId) => {
    setSelectedConsoleToRemove(consoleId)
    setShowConsoleSelectionModal(false)
    setIsDeleteModalOpen(true)
  }

  const handleRemoveAllConsoles = () => {
    setSelectedConsoleToRemove(null)
    setShowConsoleSelectionModal(false)
    setIsDeleteModalOpen(true)
  }

  return (
    <>
      <PageTitle>La Mia Libreria</PageTitle>

      {/* Messaggio di stato sincronizzazione */}
      {syncStatus && (
        <div className={`mb-4 p-4 rounded-lg ${
          syncStatus.includes('completata') 
            ? 'bg-green-100 border border-green-400 text-green-700' 
            : syncStatus.includes('Errore') || syncStatus.includes('Timeout')
            ? 'bg-red-100 border border-red-400 text-red-700'
            : 'bg-blue-100 border border-blue-400 text-blue-700'
        }`}>
          <div className="flex items-center">
            {isSyncing && (
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current mr-2"></div>
            )}
            <span>{syncStatus}</span>
          </div>
        </div>
      )}

      {/* Cards statistiche */}
      <div className="grid gap-6 mb-8 md:grid-cols-2 xl:grid-cols-4">
        <InfoCard title="Giochi Totali" value={stats.totalGames}>
          <RoundIcon
            icon={GamesIcon}
            iconColorClass="text-orange-500 dark:text-orange-100"
            bgColorClass="bg-orange-100 dark:bg-orange-500"
            className="mr-4"
          />
        </InfoCard>

        <InfoCard title="Trofei/Achievement" value={stats.totalTrophies}>
          <RoundIcon
            icon={TrophyIcon}
            iconColorClass="text-green-500 dark:text-green-100"
            bgColorClass="bg-green-100 dark:bg-green-500"
            className="mr-4"
          />
        </InfoCard>

        <InfoCard title="Ore Giocate" value={stats.totalPlayTime}>
          <RoundIcon
            icon={PlayIcon}
            iconColorClass="text-blue-500 dark:text-blue-100"
            bgColorClass="bg-blue-100 dark:bg-blue-500"
            className="mr-4"
          />
        </InfoCard>

        <InfoCard title="Giochi Completati" value={stats.completedGames}>
          <RoundIcon
            icon={StarIcon}
            iconColorClass="text-purple-500 dark:text-purple-100"
            bgColorClass="bg-purple-100 dark:bg-purple-500"
            className="mr-4"
          />
        </InfoCard>
      </div>

      {/* Controlli */}
      <div className="flex flex-col md:flex-row justify-between mb-8">
        <div className="flex flex-col md:flex-row md:w-2/3 gap-4">
          <Select
            className="mt-1"
            onChange={(e) => setSelectedPlatform(e.target.value)}
            value={selectedPlatform}
          >
            <option value="">Tutte le piattaforme</option>
            <option value="steam">Steam</option>
            <option value="psn">PlayStation Network</option>
          </Select>

          <Select
            className="mt-1"
            onChange={(e) => setSortBy(e.target.value)}
            value={sortBy}
          >
            <option value="name">Nome</option>
            <option value="total_play_count">Ore giocate</option>
            <option value="total_num_trophies">Trofei/Achievement</option>
          </Select>

          <Select
            className="mt-1"
            onChange={(e) => setSortOrder(e.target.value)}
            value={sortOrder}
          >
            <option value="asc">Crescente</option>
            <option value="desc">Decrescente</option>
          </Select>
        </div>

        <div className="flex gap-4 mt-4 md:mt-0">
          <Button 
            onClick={() => handleSyncPlatform('steam')}
            disabled={isSyncing}
            className={isSyncing ? 'opacity-50 cursor-not-allowed' : ''}
          >
            {isSyncing && syncJobId ? (
              <div className="flex items-center">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Sincronizzando...
              </div>
            ) : (
              'Sincronizza Steam'
            )}
          </Button>
          <Button 
            onClick={() => handleSyncPlatform('psn')}
            disabled={isSyncing}
            className={isSyncing ? 'opacity-50 cursor-not-allowed' : ''}
          >
            {isSyncing && syncJobId ? (
              <div className="flex items-center">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Sincronizzando...
              </div>
            ) : (
              'Sincronizza PSN'
            )}
          </Button>
        </div>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4" role="alert">
          <span className="block sm:inline">{error}</span>
        </div>
      )}

      {/* Tabella giochi */}
      <TableContainer className="mb-8">
        <Table>
          <TableHeader>
            <TableRow>
              <TableCell>Gioco</TableCell>
              <TableCell>Console</TableCell>
              <TableCell>Piattaforme</TableCell>
              <TableCell>Tempo di Gioco</TableCell>
              <TableCell>Trofei</TableCell>
              <TableCell>Azioni</TableCell>
            </TableRow>
          </TableHeader>
          <TableBody>
            {games.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8">
                  <div className="text-gray-500 dark:text-gray-400">
                    {isLoading ? (
                      <p>Caricamento giochi...</p>
                    ) : (
                      <div>
                        <p className="mb-2">Nessun gioco trovato nella tua libreria</p>
                        <p className="text-sm">Prova a sincronizzare con Steam o PSN per aggiungere i tuoi giochi</p>
                      </div>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              games.map((game, i) => (
                <TableRow key={i}>
                  <TableCell>
                    <div className="flex items-center text-sm">
                      <img
                        className="hidden w-12 h-12 rounded mr-3 md:block"
                        src={game.cover_image || '/default_cover.png'}
                        alt={game.name}
                        onError={(e) => {
                          e.target.onerror = null // Previene loop infiniti
                          e.target.src = '/default_cover.png' // Percorso immagine di fallback
                        }}
                      />
                      <div>
                        <p className="font-semibold">{game.name}</p>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    {renderConsoles(game)}
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {game.own_platforms && game.own_platforms.map((platform, idx) => (
                        <Badge key={idx} type="neutral">
                          {platform}
                        </Badge>
                      ))}
                    </div>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm">
                      {game.total_play_count || 0}h
                    </span>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm">
                      {game.total_num_trophies || 0}
                    </span>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center space-x-4">
                      <Button 
                        layout="link" 
                        size="icon" 
                        aria-label="Delete"
                        onClick={() => handleDeleteGame(game)}
                      >
                        <TrashIcon className="w-5 h-5" aria-hidden="true" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
        <TableFooter>
          <Pagination
            totalResults={totalResults}
            resultsPerPage={resultsPerPage}
            onChange={onPageChange}
            label="Table navigation"
          />
        </TableFooter>
      </TableContainer>

      {/* Console Selection Modal */}
      <Modal isOpen={showConsoleSelectionModal} onClose={() => setShowConsoleSelectionModal(false)}>
        <ModalHeader className="text-center">
          Rimuovi console specifica
        </ModalHeader>
        <ModalBody>
          {selectedGame && (
            <div>
              <p className="mb-4 text-gray-600 dark:text-gray-400 text-center">
                Seleziona la console da rimuovere per <strong>{selectedGame.name}</strong>:
              </p>
              <div className="flex flex-col space-y-2 mb-6">
                {selectedGame.consoles && selectedGame.consoles.length > 0 && (
                  selectedGame.consoles.map((console, index) => (
                    <Button
                      key={index}
                      onClick={() => handleConsoleSelection(console)}
                      layout="outline"
                      className="w-full text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
                    >
                      {getConsoleNameSync(console)}
                    </Button>
                  ))
                )}
              </div>
            </div>
          )}
        </ModalBody>
        <ModalFooter className="flex justify-center">
          <Button
            onClick={() => handleRemoveAllConsoles()}
            layout="outline"
            className="text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300"
          >
            Rimuovi tutte le console
          </Button>
        </ModalFooter>
      </Modal>

      {/* Modal per confermare eliminazione */}
      <Modal isOpen={isDeleteModalOpen} onClose={() => setIsDeleteModalOpen(false)}>
        <ModalHeader className="text-center justify-center">
          Conferma Eliminazione
        </ModalHeader>
        <ModalBody>
          {selectedGame && (
            <p className="text-center">
              {selectedConsoleToRemove ? 
                `Sei sicuro di voler rimuovere "${selectedGame.name}" dalla libreria per ${getConsoleNameSync(selectedConsoleToRemove)}?` :
                `Sei sicuro di voler rimuovere "${selectedGame.name}" dalla tua libreria?`
              }
              <br />
              <span className="text-sm text-gray-500 dark:text-gray-400 mt-2 block">
                Questa azione non può essere annullata.
              </span>
            </p>
          )}
        </ModalBody>
        <ModalFooter className="flex justify-center">
          <div className="hidden sm:block">
            <Button onClick={handleConfirmDelete} className="bg-red-600 hover:bg-red-700">
              Elimina
            </Button>
          </div>
          <div className="block w-full sm:hidden">
            <Button block size="large" onClick={handleConfirmDelete} className="bg-red-600 hover:bg-red-700">
              Elimina
            </Button>
          </div>
        </ModalFooter>
      </Modal>
    </>
  )
}

export default MyLibrary 