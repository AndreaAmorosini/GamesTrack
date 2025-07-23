import React, { useState, useEffect } from 'react'
import CTA from '../components/CTA'
import InfoCard from '../components/Cards/InfoCard'
import ChartCard from '../components/Chart/ChartCard'
import { Doughnut, Line } from 'react-chartjs-2'
import ChartLegend from '../components/Chart/ChartLegend'
import PageTitle from '../components/Typography/PageTitle'
import RoundIcon from '../components/RoundIcon'
import { getUserDashboard, searchIGDBGames, addGameToWishlist, addGameToLibrary, getLibraryConsolesForGame, getWishlistConsolesForGame, getConsoleNames } from '../services/api'
import { 
  GamesIcon, 
  HeartIcon, 
  TrophyIcon, 
  ClockIcon,
  CartIcon,
  MoneyIcon,
  PeopleIcon,
  ChatIcon,
  SearchIcon,
  FilterIcon
} from '../icons'
import {
  TableBody,
  TableContainer,
  Table,
  TableHeader,
  TableCell,
  TableRow,
  TableFooter,
  Badge,
  Input,
  Select,
  Button,
  Modal,
  ModalHeader,
  ModalBody,
  ModalFooter,
} from '@windmill/react-ui'

function Dashboard() {
  const [dashboardData, setDashboardData] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  // Stati per la ricerca giochi
  const [searchTerm, setSearchTerm] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [isSearching, setIsSearching] = useState(false)
  const [searchError, setSearchError] = useState('')
  const [page, setPage] = useState(1)
  const [resultsPerPage] = useState(10)
  
  // Stati per la modal di selezione console
  const [isConsoleModalOpen, setIsConsoleModalOpen] = useState(false)
  const [selectedGame, setSelectedGame] = useState(null)
  const [selectedAction, setSelectedAction] = useState('') // 'wishlist' o 'library'
  const [selectedConsole, setSelectedConsole] = useState(null)
  const [alreadyAddedConsoles, setAlreadyAddedConsoles] = useState([])
  const [wishlistLoading, setWishlistLoading] = useState({})
  const [libraryLoading, setLibraryLoading] = useState({})

  // Cache per i nomi delle console
  const [consoleNamesCache, setConsoleNamesCache] = useState({})

  // Funzione per costruire l'URL dell'immagine
  const getImageUrl = (cover) => {
    if (!cover) {
      return '/default_cover.png'
    }
    
    // Usa cover.url e aggiungi https: davanti
    const imageUrl = cover.url
    
    if (!imageUrl) {
      return '/default_cover.png'
    }
    
    // Aggiungi https: davanti all'URL relativo
    return `https:${imageUrl}`
  }

  // Funzione per cercare i giochi
  const handleSearch = async () => {
    if (!searchTerm.trim()) return

    setIsSearching(true)
    setSearchError('')
    try {
      const response = await searchIGDBGames(searchTerm, null, null, page, resultsPerPage)
      setSearchResults(response.games || [])
      // Carica i nomi delle console per i risultati
      loadConsoleNames(response.games || [])
    } catch (err) {
      setSearchError('Errore durante la ricerca: ' + err.message)
      console.error('Search error:', err)
    } finally {
      setIsSearching(false)
    }
  }

  // Funzione per aprire la modal di selezione console
  const openConsoleModal = async (game, action) => {
    setSelectedGame(game)
    setSelectedAction(action)
    setSelectedConsole(null)
    setIsConsoleModalOpen(true)
    
    try {
      if (action === 'library') {
        const libraryData = await getLibraryConsolesForGame(game.igdb_id || game._id)
        setAlreadyAddedConsoles(libraryData.consoles || [])
      } else if (action === 'wishlist') {
        const wishlistData = await getWishlistConsolesForGame(game.igdb_id || game._id)
        setAlreadyAddedConsoles(wishlistData.consoles || [])
      }
    } catch (err) {
      console.error('Error loading already added consoles:', err)
      setAlreadyAddedConsoles([])
    }
  }

  // Funzione per chiudere la modal
  const closeConsoleModal = () => {
    setIsConsoleModalOpen(false)
    setSelectedGame(null)
    setSelectedAction('')
    setSelectedConsole(null)
  }

  // Funzione per confermare l'aggiunta del gioco
  const confirmAddGame = async () => {
    if (!selectedGame || !selectedConsole) return

    try {
      if (selectedAction === 'wishlist') {
        setWishlistLoading(prev => ({ ...prev, [selectedGame._id]: true }))
        await addGameToWishlist(selectedGame.igdb_id || selectedGame._id, selectedConsole)
        alert(`${selectedGame.name} aggiunto alla wishlist per ${getConsoleNameSync(selectedConsole)}!`)
      } else if (selectedAction === 'library') {
        setLibraryLoading(prev => ({ ...prev, [selectedGame._id]: true }))
        await addGameToLibrary(selectedGame.igdb_id || selectedGame._id, selectedConsole)
        alert(`${selectedGame.name} aggiunto alla libreria per ${getConsoleNameSync(selectedConsole)}!`)
      }
      closeConsoleModal()
      // Ricarica i dati della dashboard
      fetchDashboardData()
    } catch (err) {
      console.error(`Error adding to ${selectedAction}:`, err)
      alert(err.message || `Errore nell'aggiunta alla ${selectedAction}`)
    } finally {
      if (selectedAction === 'wishlist') {
        setWishlistLoading(prev => ({ ...prev, [selectedGame._id]: false }))
      } else if (selectedAction === 'library') {
        setLibraryLoading(prev => ({ ...prev, [selectedGame._id]: false }))
      }
    }
  }

  // Funzione per caricare i nomi delle console
  const loadConsoleNames = async (games) => {
    const consoleIds = []
    
    // Raccogli tutti gli ID delle console dai giochi
    games.forEach(game => {
      if (game.platforms && Array.isArray(game.platforms)) {
        game.platforms.forEach(platform => {
          const platformId = typeof platform === 'object' ? platform.id : platform
          if (typeof platformId === 'number' && !consoleNamesCache[platformId]) {
            consoleIds.push(platformId)
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

  // Funzione per ottenere il nome della console (versione sincrona per il rendering)
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

  // Funzione per ottenere le console disponibili per un gioco
  const getAvailableConsoles = (game) => {
    if (!game || !game.platforms || game.platforms.length === 0) {
      return []
    }

    const availableConsoles = []
    for (const platform of game.platforms) {
      if (typeof platform === 'object' && platform.id) {
        availableConsoles.push({
          id: platform.id,
          name: platform.name || platform.abbreviation || getConsoleNameSync(platform.id)
        })
      } else if (typeof platform === 'number') {
        availableConsoles.push({
          id: platform,
          name: getConsoleNameSync(platform)
        })
      }
    }
    return availableConsoles
  }

  // Carica i dati della dashboard
  const fetchDashboardData = async () => {
    try {
      setIsLoading(true)
      const data = await getUserDashboard()
      setDashboardData(data)
    } catch (err) {
      setError('Errore nel caricamento della dashboard: ' + err.message)
      console.error('Dashboard error:', err)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchDashboardData()
  }, [])

  // Dati per il grafico a ciambella della distribuzione piattaforme
  const doughnutOptions = {
    data: {
      datasets: [
        {
          data: dashboardData?.platform_distribution 
            ? [dashboardData.platform_distribution.steam, dashboardData.platform_distribution.psn, dashboardData.platform_distribution.other]
            : [0, 0, 0],
          backgroundColor: ['#0694a2', '#1c64f2', '#7e3af2'],
          label: 'Giochi',
        },
      ],
      labels: ['Steam', 'PlayStation Network', 'Altri'],
    },
    options: {
      responsive: true,
      cutoutPercentage: 80,
    },
    legend: {
      display: false,
    },
  }

  // Dati per il grafico a linee delle statistiche nel tempo
  const lineOptions = {
    data: {
      labels: dashboardData?.platform_stats_summary?.map(p => p.platform === 'steam' ? 'Steam' : p.platform === 'psn' ? 'PSN' : p.platform) || [],
      datasets: [
        {
          label: 'Giochi',
          data: dashboardData?.platform_stats_summary?.map(p => p.game_count) || [],
          fill: false,
          borderColor: '#0694a2',
          tension: 0.4,
        },
        {
          label: 'Trophy/Achievement',
          data: dashboardData?.platform_stats_summary?.map(p => p.earned_achievements) || [],
          fill: false,
          borderColor: '#7e3af2',
          tension: 0.4,
        },
      ],
    },
    options: {
      responsive: true,
      scales: {
        y: {
          beginAtZero: true,
        }
      },
    },
  }

  if (isLoading) {
    return (
      <>
        <PageTitle>Dashboard</PageTitle>
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto"></div>
            <p className="mt-4 text-gray-600 dark:text-gray-400">Caricamento dashboard...</p>
          </div>
        </div>
      </>
    )
  }

  if (error) {
    return (
      <>
        <PageTitle>Dashboard</PageTitle>
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
          <p>{error}</p>
        </div>
      </>
    )
  }

  return (
    <>
      <PageTitle>Dashboard</PageTitle>

      {/* <CTA /> */}

      {/* Cards con statistiche principali */}
      <div className="grid gap-6 mb-8 md:grid-cols-2 xl:grid-cols-4">
        <InfoCard title="Giochi nella Libreria" value={dashboardData?.library_stats?.total_owned_games || 0}>
          <RoundIcon
            icon={GamesIcon}
            iconColorClass="text-orange-500 dark:text-orange-100"
            bgColorClass="bg-orange-100 dark:bg-orange-500"
            className="mr-4"
          />
        </InfoCard>

        <InfoCard title="Giochi nella Wishlist" value={dashboardData?.wishlist_stats?.total_games_in_wishlist || 0}>
          <RoundIcon
            icon={HeartIcon}
            iconColorClass="text-red-500 dark:text-red-100"
            bgColorClass="bg-red-100 dark:bg-red-500"
            className="mr-4"
          />
        </InfoCard>

        <InfoCard title="Trophy/Achievement" value={dashboardData?.library_stats?.total_achievements || 0}>
          <RoundIcon
            icon={TrophyIcon}
            iconColorClass="text-green-500 dark:text-green-100"
            bgColorClass="bg-green-100 dark:bg-green-500"
            className="mr-4"
          />
        </InfoCard>

        <InfoCard title="Ore di Gioco" value={`${dashboardData?.library_stats?.total_playcount_hours || 0}h`}>
          <RoundIcon
            icon={ClockIcon}
            iconColorClass="text-blue-500 dark:text-blue-100"
            bgColorClass="bg-blue-100 dark:bg-blue-500"
            className="mr-4"
          />
        </InfoCard>
      </div>

      {/* Grafici */}
      <div className="grid gap-6 mb-8 md:grid-cols-2">
        <ChartCard title="Distribuzione Piattaforme">
          <Doughnut {...doughnutOptions} />
          <ChartLegend legends={[
            { title: 'Steam', color: 'bg-teal-500' },
            { title: 'PlayStation Network', color: 'bg-blue-500' },
            { title: 'Altri', color: 'bg-purple-500' },
          ]} />
        </ChartCard>

        <ChartCard title="Statistiche per Piattaforma">
          <Line {...lineOptions} />
          <ChartLegend legends={[
            { title: 'Giochi', color: 'bg-teal-500' },
            { title: 'Trophy/Achievement', color: 'bg-purple-500' },
          ]} />
        </ChartCard>
      </div>

      {/* Dettagli Piattaforme */}
      <TableContainer className="mb-8">
        <Table>
          <TableHeader>
            <tr>
              <TableCell>Piattaforma</TableCell>
              <TableCell>Giochi</TableCell>
              <TableCell>Trophy/Achievement</TableCell>
              <TableCell>Ore di Gioco</TableCell>
              <TableCell>Trophy Completi</TableCell>
            </tr>
          </TableHeader>
          <TableBody>
            {dashboardData?.platform_stats_summary?.map((platform, i) => (
              <TableRow key={i}>
                <TableCell>
                  <span className="font-semibold">
                    {platform.platform === 'steam' ? 'Steam' : 
                     platform.platform === 'psn' ? 'PlayStation Network' : 
                     platform.platform}
                  </span>
                </TableCell>
                <TableCell>
                  <span className="text-sm">{platform.game_count}</span>
                </TableCell>
                <TableCell>
                  <span className="text-sm">{platform.earned_achievements}</span>
                </TableCell>
                <TableCell>
                  <span className="text-sm">{platform.play_count}h</span>
                </TableCell>
                <TableCell>
                  <span className="text-sm">{platform.full_trophies_count || 0}</span>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Ultima Sincronizzazione */}
      {dashboardData?.last_sync_job && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-8">
          <h3 className="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-4">
            Ultima Sincronizzazione
          </h3>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Piattaforma</p>
              <p className="text-lg font-semibold text-gray-700 dark:text-gray-300 capitalize">
                {dashboardData.last_sync_job.platform}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Status</p>
              <Badge type={
                dashboardData.last_sync_job.status === 'success' ? 'success' :
                dashboardData.last_sync_job.status === 'fail' ? 'danger' :
                dashboardData.last_sync_job.status === 'in_progress' ? 'warning' :
                'primary'
              }>
                {dashboardData.last_sync_job.status === 'success' ? 'Completato' :
                 dashboardData.last_sync_job.status === 'fail' ? 'Fallito' :
                 dashboardData.last_sync_job.status === 'in_progress' ? 'In Corso' :
                 'In Attesa'}
              </Badge>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Giochi Aggiunti</p>
              <p className="text-lg font-semibold text-gray-700 dark:text-gray-300">
                {dashboardData.last_sync_job.games_inserted || 0}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Giochi Aggiornati</p>
              <p className="text-lg font-semibold text-gray-700 dark:text-gray-300">
                {dashboardData.last_sync_job.games_updated || 0}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Sezione Ricerca Giochi */}
      <div className="px-4 py-3 mb-8 bg-white rounded-lg shadow-md dark:bg-gray-800">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-700 dark:text-gray-300">
            Cerca e Aggiungi Giochi
          </h3>
        </div>
        
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <div className="col-span-2">
            <Input
              className="mt-1"
              placeholder="Cerca giochi..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              icon={SearchIcon}
            />
          </div>
          
          <div>
            <Button onClick={handleSearch} disabled={isSearching}>
              {isSearching ? 'Ricerca in corso...' : 'Cerca'}
            </Button>
          </div>
        </div>

        {searchError && (
          <div className="mt-4 p-3 bg-red-100 text-red-700 rounded-lg">
            {searchError}
          </div>
        )}

        {searchResults.length > 0 && (
          <TableContainer className="mt-4">
            <Table>
              <TableHeader>
                <tr>
                  <TableCell>Gioco</TableCell>
                  <TableCell>Piattaforme</TableCell>
                  <TableCell>Generi</TableCell>
                  <TableCell>Valutazione</TableCell>
                  <TableCell>Azioni</TableCell>
                </tr>
              </TableHeader>
              <TableBody>
                {searchResults.map((game, i) => (
                  <TableRow key={i}>
                    <TableCell>
                      <div className="flex items-center text-sm">
                        <img
                          className="hidden w-12 h-12 mr-3 md:block object-cover rounded"
                          src={getImageUrl(game.cover)}
                          alt={game.name}
                          onError={(e) => {
                            e.target.onerror = null // Previene loop infiniti
                            e.target.src = '/default_cover.png'
                          }}
                        />
                        <div>
                          <p className="font-semibold">{game.name}</p>
                          {game.original_name && game.original_name !== game.name && (
                            <p className="text-xs text-gray-500 dark:text-gray-400">
                              {game.original_name}
                            </p>
                          )}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {game.platform_names?.map((platform, idx) => (
                          <Badge key={idx} type="success">
                            {platform}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {game.genre_names?.map((genre, idx) => (
                          <Badge key={idx} type="info">
                            {genre}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="text-sm">
                        {game.total_rating ? (
                          <div>
                            <span className="font-semibold">{Math.round(game.total_rating)}%</span>
                            {game.total_rating_count && (
                              <div className="text-xs text-gray-500">
                                {game.total_rating_count} recensioni
                              </div>
                            )}
                          </div>
                        ) : (
                          'N/A'
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex space-x-2">
                        <Button
                          layout="link"
                          size="small"
                          onClick={() => openConsoleModal(game, 'library')}
                          disabled={libraryLoading[game._id]}
                        >
                          {libraryLoading[game._id] ? 'Aggiunta...' : 'Libreria'}
                        </Button>
                        <Button
                          layout="link"
                          size="small"
                          onClick={() => openConsoleModal(game, 'wishlist')}
                          disabled={wishlistLoading[game._id]}
                        >
                          {wishlistLoading[game._id] ? 'Aggiunta...' : 'Wishlist'}
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </div>

      {/* Modal per la selezione della console */}
      <Modal isOpen={isConsoleModalOpen} onClose={closeConsoleModal}>
        <ModalHeader>
          Seleziona Console per {selectedGame?.name}
        </ModalHeader>
        <ModalBody>
          {selectedGame ? (
            <div>
              <p className="mb-4 text-gray-600 dark:text-gray-400">
                Seleziona la console per cui vuoi aggiungere questo gioco alla {selectedAction === 'wishlist' ? 'wishlist' : 'libreria'}:
              </p>
              
              <div className="space-y-2">
                {getAvailableConsoles(selectedGame).map((console) => {
                  const isAlreadyAdded = alreadyAddedConsoles.includes(console.id)
                  return (
                    <label 
                      key={console.id} 
                      className={`flex items-center p-3 border rounded-lg cursor-pointer ${
                        isAlreadyAdded 
                          ? 'bg-gray-100 dark:bg-gray-700 opacity-50 cursor-not-allowed' 
                          : 'hover:bg-gray-50 dark:hover:bg-gray-700'
                      }`}
                    >
                      <input
                        type="radio"
                        name="console"
                        value={console.id}
                        checked={selectedConsole === console.id}
                        onChange={(e) => setSelectedConsole(parseInt(e.target.value))}
                        disabled={isAlreadyAdded}
                        className="mr-3"
                      />
                      <span className="text-sm font-medium">
                        {console.name}
                        {isAlreadyAdded && (
                          <span className="ml-2 text-xs text-green-600 dark:text-green-400">
                            ✓ Già aggiunto
                          </span>
                        )}
                      </span>
                    </label>
                  )
                })}
              </div>
              
              {getAvailableConsoles(selectedGame).length === 0 && (
                <p className="text-yellow-400 text-sm">
                  Nessuna console disponibile per questo gioco.
                </p>
              )}
            </div>
          ) : (
            <p className="text-gray-600 dark:text-gray-400">
              Caricamento informazioni gioco...
            </p>
          )}
        </ModalBody>
        <ModalFooter>
          <Button layout="outline" onClick={closeConsoleModal}>
            Annulla
          </Button>
          <Button 
            onClick={confirmAddGame}
            disabled={!selectedConsole || getAvailableConsoles(selectedGame).length === 0 || alreadyAddedConsoles.includes(selectedConsole)}
          >
            {selectedAction === 'wishlist' ? 'Aggiungi alla Wishlist' : 'Aggiungi alla Libreria'}
          </Button>
        </ModalFooter>
      </Modal>
    </>
  )
}

export default Dashboard
