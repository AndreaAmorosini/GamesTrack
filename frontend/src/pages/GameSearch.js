import React, { useState, useEffect } from 'react'
import PageTitle from '../components/Typography/PageTitle'
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
  Input,
  Select,
  Modal,
  ModalHeader,
  ModalBody,
  ModalFooter,
} from '@windmill/react-ui'
import { HeartIcon, GamesIcon } from '../icons'
import { searchIGDBGames, addGameToWishlist, addGameToLibrary, getPlatformMapping, getLibraryConsolesForGame, getWishlistConsolesForGame, getConsoleNames } from '../services/api'

function GameSearch() {
  // Stati per la ricerca
  const [searchTerm, setSearchTerm] = useState('')
  const [platform, setPlatform] = useState('')
  const [company, setCompany] = useState('')
  const [selectedGenre, setSelectedGenre] = useState('')
  const [selectedConsole, setSelectedConsole] = useState('')
  
  // Stati per i risultati
  const [games, setGames] = useState([])
  const [page, setPage] = useState(1)
  const [totalResults, setTotalResults] = useState(0)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [wishlistLoading, setWishlistLoading] = useState({})
  const [libraryLoading, setLibraryLoading] = useState({})
  const [platformMapping, setPlatformMapping] = useState({})
  
  // Stati per l'ordinamento
  const [sortField, setSortField] = useState('')
  const [sortDirection, setSortDirection] = useState('asc')
  
  // Stati per la modal di selezione console
  const [isConsoleModalOpen, setIsConsoleModalOpen] = useState(false)
  const [selectedGame, setSelectedGame] = useState(null)
  const [selectedAction, setSelectedAction] = useState('') // 'wishlist' o 'library'
  const [selectedConsoles, setSelectedConsoles] = useState([]) // Array di console selezionate
  const [alreadyAddedConsoles, setAlreadyAddedConsoles] = useState([])
  
  // Cache per i nomi delle console
  const [consoleNamesCache, setConsoleNamesCache] = useState({})
  
  const resultsPerPage = 10

  // Carica il mapping delle piattaforme all'avvio
  useEffect(() => {
    const loadPlatformMapping = async () => {
      try {
        const data = await getPlatformMapping()
        setPlatformMapping(data.mapping || {})
      } catch (err) {
        console.error('Error loading platform mapping:', err)
      }
    }
    
    loadPlatformMapping()
  }, [])

  // Funzione per gestire l'ordinamento
  const handleSort = (field) => {
    if (sortField === field) {
      // Se clicchi sullo stesso campo, inverte la direzione
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      // Se clicchi su un nuovo campo, imposta la direzione di default
      setSortField(field)
      setSortDirection('asc')
    }
  }

  // Funzione per ordinare i giochi
  const sortGames = (gamesToSort) => {
    if (!sortField) return gamesToSort

    return [...gamesToSort].sort((a, b) => {
      let aValue, bValue

      switch (sortField) {
        case 'release_date':
          aValue = a.release_date ? new Date(a.release_date).getTime() : 0
          bValue = b.release_date ? new Date(b.release_date).getTime() : 0
          break
        case 'total_rating':
          aValue = a.total_rating || 0
          bValue = b.total_rating || 0
          break
        default:
          return 0
      }

      if (sortDirection === 'asc') {
        return aValue > bValue ? 1 : -1
      } else {
        return aValue < bValue ? 1 : -1
      }
    })
  }

  // Funzione per ottenere l'icona di ordinamento
  const getSortIcon = (field) => {
    if (sortField !== field) {
      return '↕️'
    }
    return sortDirection === 'asc' ? '↑' : '↓'
  }

  // Funzione per estrarre tutti i generi disponibili dai risultati
  const getAvailableGenres = () => {
    const allGenres = new Set()
    games.forEach(game => {
      if (game.genres && Array.isArray(game.genres)) {
        game.genres.forEach(genre => {
          if (genre) allGenres.add(genre)
        })
      }
    })
    return Array.from(allGenres).sort()
  }

  // Funzione per estrarre tutte le console disponibili dai risultati
  const getAvailableConsoles = () => {
    const allConsoles = new Set()
    games.forEach(game => {
      if (game.platforms && Array.isArray(game.platforms)) {
        game.platforms.forEach(platform => {
          if (platform && platform.name) {
            allConsoles.add(platform.name)
          }
        })
      }
    })
    return Array.from(allConsoles).sort()
  }

  // Funzione per filtrare i giochi per genere
  const filterGamesByGenre = (gamesToFilter) => {
    if (!selectedGenre) return gamesToFilter
    return gamesToFilter.filter(game => 
      game.genres && game.genres.includes(selectedGenre)
    )
  }

  // Funzione per filtrare i giochi per console
  const filterGamesByConsole = (gamesToFilter) => {
    if (!selectedConsole) return gamesToFilter
    return gamesToFilter.filter(game => 
      game.platforms && game.platforms.some(platform => 
        platform.name === selectedConsole
      )
    )
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

  // Funzione per aprire la modal di selezione console
  const openConsoleModal = async (game, action) => {
    setSelectedGame(game)
    setSelectedAction(action)
    setSelectedConsoles([]) // Reset delle console selezionate
    setIsConsoleModalOpen(true)
    
    // Carica le console già aggiunte per questo gioco
    try {
      if (action === 'library') {
        const libraryData = await getLibraryConsolesForGame(game.igdb_id)
        setAlreadyAddedConsoles(libraryData.console || [])
      } else if (action === 'wishlist') {
        const wishlistData = await getWishlistConsolesForGame(game.igdb_id)
        setAlreadyAddedConsoles(wishlistData.console || [])
      }
    } catch (err) {
      console.error('Error loading already added consoles:', err)
      setAlreadyAddedConsoles([])
    }
  }

  // Funzione per gestire la selezione/deselezione di una console
  const handleConsoleToggle = (consoleId) => {
    setSelectedConsoles(prev => {
      if (prev.includes(consoleId)) {
        return prev.filter(id => id !== consoleId)
      } else {
        return [...prev, consoleId]
      }
    })
  }

  // Funzione per chiudere la modal
  const closeConsoleModal = () => {
    setIsConsoleModalOpen(false)
    setSelectedGame(null)
    setSelectedAction('')
    setSelectedConsoles([])
  }

  // Funzione per confermare l'aggiunta del gioco
  const confirmAddGame = async () => {
    if (!selectedGame || selectedConsoles.length === 0) return

    try {
      // Aggiungi il gioco per ogni console selezionata
      for (const consoleId of selectedConsoles) {
        if (selectedAction === 'wishlist') {
          setWishlistLoading(prev => ({ ...prev, [selectedGame.igdb_id]: true }))
          await addGameToWishlist(selectedGame.igdb_id, consoleId)
        } else if (selectedAction === 'library') {
          setLibraryLoading(prev => ({ ...prev, [selectedGame.igdb_id]: true }))
          await addGameToLibrary(selectedGame.igdb_id, consoleId)
        }
      }
      
      // Emetti un evento custom per notificare l'aggiunta del gioco
      const event = new CustomEvent('gameLibraryChanged', {
        detail: {
          action: selectedAction,
          gameId: selectedGame.igdb_id,
          consoles: selectedConsoles
        }
      });
      window.dispatchEvent(event);
      
      closeConsoleModal()
    } catch (err) {
      console.error(`Error adding to ${selectedAction}:`, err)
      alert(err.message || `Errore nell'aggiunta alla ${selectedAction}`)
    } finally {
      if (selectedAction === 'wishlist') {
        setWishlistLoading(prev => ({ ...prev, [selectedGame.igdb_id]: false }))
      } else if (selectedAction === 'library') {
        setLibraryLoading(prev => ({ ...prev, [selectedGame.igdb_id]: false }))
      }
    }
  }

  // Funzione per costruire l'URL dell'immagine
  const getImageUrl = (cover) => {
    if (!cover) {
      return null
    }
    
    // Usa cover.url e aggiungi https: davanti
    const imageUrl = cover.url
    
    if (!imageUrl) {
      return null
    }
    
    // Aggiungi https: davanti all'URL relativo
    return `https:${imageUrl}`
  }

  // Funzione per ottenere le console disponibili per un gioco
  const getAvailableConsolesForGame = (game) => {
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

  // Funzione per aggiungere un gioco alla wishlist (ora apre la modal)
  const handleAddToWishlist = async (game) => {
    openConsoleModal(game, 'wishlist')
  }

  // Funzione per aggiungere un gioco alla libreria (ora apre la modal)
  const handleAddToLibrary = async (game) => {
    openConsoleModal(game, 'library')
  }

  // Funzione per effettuare la ricerca
  const performSearch = async () => {
    if (!searchTerm.trim()) return

    // Verifica se il token è presente
    const token = localStorage.getItem('token')
    if (!token) {
      window.location.replace('/login')
      return
    }

    setIsLoading(true)
    setError('')
    try {
      // Correggo la chiamata API per passare i parametri correttamente
      const data = await searchIGDBGames(searchTerm, {
        platform: platform || undefined,
        company: company || undefined,
        page: page,
        limit: resultsPerPage
      })
      setGames(data.games || [])
      setTotalResults(data.pagination?.total_returned || 0)
      // Reset dei filtri quando si fa una nuova ricerca
      setSelectedGenre('')
      setSelectedConsole('')
      
      // Carica i nomi delle console per i risultati
      loadConsoleNames(data.games || [])
    } catch (err) {
      // Non mostrare errori se è un errore di autenticazione
      if (err.message !== 'Sessione scaduta') {
        setError('Errore durante la ricerca: ' + err.message)
      }
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }

  // Gestione cambio pagina
  const onPageChange = (p) => {
    setPage(p)
  }

  // Effettua la ricerca quando cambiano i parametri
  useEffect(() => {
    if (searchTerm.trim()) {
      // Verifica se il token è presente
      const token = localStorage.getItem('token')
      if (!token) {
        window.location.replace('/login')
        return
      }
      performSearch()
    }
  }, [page])

  // Filtra e ordina i giochi
  const filteredByGenre = filterGamesByGenre(games)
  const filteredByConsole = filterGamesByConsole(filteredByGenre)
  const sortedGames = sortGames(filteredByConsole)
  const availableGenres = getAvailableGenres()
  const availableConsoles = getAvailableConsoles()

  return (
    <>
      <PageTitle>Cerca Giochi</PageTitle>

      {/* Form di ricerca */}
      <div className="px-4 py-3 mb-8 bg-white rounded-lg shadow-md dark:bg-gray-800">
        <div className="grid gap-4 md:grid-cols-5">
          <div>
            <Input
              className="mt-1"
              placeholder="Cerca giochi..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && performSearch()}
            />
          </div>

          <div>
            <Select
              className="mt-1"
              value={selectedGenre}
              onChange={(e) => setSelectedGenre(e.target.value)}
              disabled={games.length === 0}
            >
              <option value="">Tutti i generi</option>
              {availableGenres.map((genre) => (
                <option key={genre} value={genre}>
                  {genre}
                </option>
              ))}
            </Select>
          </div>

          <div>
            <Select
              className="mt-1"
              value={selectedConsole}
              onChange={(e) => setSelectedConsole(e.target.value)}
              disabled={games.length === 0}
            >
              <option value="">Tutte le console</option>
              {availableConsoles.map((console) => (
                <option key={console} value={console}>
                  {console}
                </option>
              ))}
            </Select>
          </div>
          
          <div>
            <Button onClick={performSearch} disabled={isLoading}>
              {isLoading ? 'Ricerca...' : 'Cerca'}
            </Button>
          </div>
        </div>
      </div>

      {/* Messaggi di stato */}
      {isLoading && <p className="text-gray-600 dark:text-gray-400">Ricerca in corso...</p>}
      {error && <p className="text-red-600 dark:text-red-400">{error}</p>}

      {/* Tabella Risultati */}
      <TableContainer className="mb-8">
        <div className="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <p className="text-sm text-blue-700 dark:text-blue-300">
            <strong>💡 Suggerimento:</strong> Usa il pulsante <GamesIcon className="w-4 h-4 inline text-blue-500" /> per aggiungere alla libreria (giochi che possiedi) 
            e il pulsante <HeartIcon className="w-4 h-4 inline text-red-500" /> per aggiungere alla wishlist (giochi che desideri).
          </p>
        </div>
        <Table>
          <TableHeader>
            <tr>
              <TableCell>Gioco</TableCell>
              <TableCell>Console</TableCell>
              <TableCell>Generi</TableCell>
              <TableCell>Sviluppatore</TableCell>
              <TableCell>Publisher</TableCell>
              <TableCell>
                <Button
                  layout="link"
                  onClick={() => handleSort('release_date')}
                  className="flex items-center space-x-1 text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white"
                >
                  <span>Data di Uscita</span>
                  <span className="text-xs">{getSortIcon('release_date')}</span>
                </Button>
              </TableCell>
              <TableCell>
                <Button
                  layout="link"
                  onClick={() => handleSort('total_rating')}
                  className="flex items-center space-x-1 text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white"
                >
                  <span>Valutazione</span>
                  <span className="text-xs">{getSortIcon('total_rating')}</span>
                </Button>
              </TableCell>
              <TableCell>Azioni</TableCell>
            </tr>
          </TableHeader>
          <TableBody>
            {sortedGames.map((game, i) => (
              <TableRow key={i}>
                <TableCell>
                  <div className="flex items-center text-sm">
                    {game.cover ? (
                      <img
                        className="hidden w-12 h-12 mr-3 md:block object-cover rounded"
                        src={getImageUrl(game.cover)}
                        alt={game.name}
                        onError={(e) => {
                          e.target.style.display = 'none'
                          // Mostra un'icona di fallback
                          const fallbackIcon = document.createElement('div')
                          fallbackIcon.className = 'hidden w-12 h-12 mr-3 md:flex items-center justify-center bg-gray-200 dark:bg-gray-700 rounded'
                          fallbackIcon.innerHTML = '<svg class="w-6 h-6 text-gray-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd"></path></svg>'
                          e.target.parentNode.insertBefore(fallbackIcon, e.target)
                        }}
                      />
                    ) : (
                      <div className="hidden w-12 h-12 mr-3 md:flex items-center justify-center bg-gray-200 dark:bg-gray-700 rounded">
                        <svg className="w-6 h-6 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clipRule="evenodd"></path>
                        </svg>
                      </div>
                    )}
                    <div>
                      <p className="font-semibold">{game.name}</p>
                      {game.summary && (
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                          {game.summary.substring(0, 100)}...
                        </p>
                      )}
                    </div>
                  </div>
                </TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-1">
                    {game.platforms?.map((platform, idx) => (
                      <Badge key={idx} type="success">
                        {platform.name || platform.abbreviation || getConsoleNameSync(platform.id)}
                      </Badge>
                    ))}
                  </div>
                </TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-1">
                    {game.genres?.map((genre, idx) => (
                      <Badge key={idx} type="info">
                        {genre}
                      </Badge>
                    ))}
                  </div>
                </TableCell>
                <TableCell>
                  <span className="text-sm">
                    {game.companies?.developers?.join(', ') || 'N/A'}
                  </span>
                </TableCell>
                <TableCell>
                  <span className="text-sm">
                    {game.companies?.publishers?.join(', ') || 'N/A'}
                  </span>
                </TableCell>
                <TableCell>
                  <span className="text-sm">
                    {game.release_date ? new Date(game.release_date).toLocaleDateString() : 'TBA'}
                  </span>
                </TableCell>
                <TableCell>
                  <span className="text-sm">
                    {game.total_rating ? `${Math.round(game.total_rating)}%` : 'N/A'}
                  </span>
                </TableCell>
                <TableCell>
                  <div className="flex items-center space-x-2">
                    <Button 
                      layout="link" 
                      size="icon" 
                      aria-label="Add to Library"
                      disabled={libraryLoading[game.igdb_id]}
                      onClick={() => handleAddToLibrary(game)}
                      className={`${libraryLoading[game.igdb_id] ? 'text-gray-400' : 'text-blue-500 hover:text-blue-700'} transition-colors`}
                      title="Aggiungi alla libreria"
                    >
                      {libraryLoading[game.igdb_id] ? (
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
                      ) : (
                        <GamesIcon className="w-5 h-5" aria-hidden="true" />
                      )}
                    </Button>
                    
                    <Button 
                      layout="link" 
                      size="icon" 
                      aria-label="Add to Wishlist"
                      disabled={wishlistLoading[game.igdb_id]}
                      onClick={() => handleAddToWishlist(game)}
                      className={`${wishlistLoading[game.igdb_id] ? 'text-gray-400' : 'text-red-500 hover:text-red-700'} transition-colors`}
                      title="Aggiungi alla wishlist"
                    >
                      {wishlistLoading[game.igdb_id] ? (
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-red-500"></div>
                      ) : (
                        <HeartIcon className="w-5 h-5" aria-hidden="true" />
                      )}
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
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

      {/* Modal per la selezione della console */}
      <Modal isOpen={isConsoleModalOpen} onClose={closeConsoleModal}>
        <ModalHeader className="text-center">
          Seleziona Console per {selectedGame?.name}
        </ModalHeader>
        <ModalBody>
          {selectedGame ? (
            <div>
              <p className="mb-4 text-gray-600 dark:text-gray-400 text-center">
                Seleziona le console per cui vuoi aggiungere questo gioco alla {selectedAction === 'wishlist' ? 'wishlist' : 'libreria'}:
              </p>
              
              <div className="space-y-2">
                {getAvailableConsolesForGame(selectedGame).map((console) => {
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
                        type="checkbox"
                        checked={selectedConsoles.includes(console.id)}
                        onChange={() => handleConsoleToggle(console.id)}
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
              
              {getAvailableConsolesForGame(selectedGame).length === 0 && (
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
        <ModalFooter className="flex justify-center">
          <Button 
            onClick={confirmAddGame}
            disabled={selectedConsoles.length === 0 || getAvailableConsolesForGame(selectedGame).length === 0}
            className="bg-blue-600 hover:bg-blue-700"
          >
            {selectedAction === 'wishlist' ? 'Aggiungi alla Wishlist' : 'Aggiungi alla Libreria'}
          </Button>
        </ModalFooter>
      </Modal>
    </>
  )
}

export default GameSearch 