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
import { searchIGDBGames, addGameToWishlist, addGameToLibrary, getPlatformMapping, getLibraryConsolesForGame, getWishlistConsolesForGame } from '../services/api'

function GameSearch() {
  // Stati per la ricerca
  const [searchTerm, setSearchTerm] = useState('')
  const [platform, setPlatform] = useState('')
  const [company, setCompany] = useState('')
  
  // Stati per i risultati
  const [games, setGames] = useState([])
  const [page, setPage] = useState(1)
  const [totalResults, setTotalResults] = useState(0)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [wishlistLoading, setWishlistLoading] = useState({})
  const [libraryLoading, setLibraryLoading] = useState({})
  const [platformMapping, setPlatformMapping] = useState({})
  
  // Stati per la modal di selezione console
  const [isConsoleModalOpen, setIsConsoleModalOpen] = useState(false)
  const [selectedGame, setSelectedGame] = useState(null)
  const [selectedAction, setSelectedAction] = useState('') // 'wishlist' o 'library'
  const [selectedConsoles, setSelectedConsoles] = useState([]) // Array di console selezionate
  const [alreadyAddedConsoles, setAlreadyAddedConsoles] = useState([])
  
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

  // Funzione per ottenere il nome della console
  const getConsoleName = (consoleId) => {
    // Se consoleId è già una stringa (nome console), restituiscilo direttamente
    if (typeof consoleId === 'string') {
      return consoleId
    }
    
    // Se è un numero (ID console), convertilo
    switch (consoleId) {
      case 6:
        return 'PC (Microsoft Windows)'
      case 48:
        return 'PlayStation 4'
      case 167:
        return 'PlayStation 5'
      case 130:
        return 'Nintendo Switch'
      case 49:
        return 'Xbox One'
      case 169:
        return 'Xbox Series X|S'
      case 3:
        return 'Linux'
      case 14:
        return 'Mac'
      case 7:
        return 'Nintendo 3DS'
      case 9:
        return 'Nintendo DS'
      case 11:
        return 'Xbox'
      case 12:
        return 'Xbox 360'
      case 13:
        return 'PlayStation'
      case 15:
        return 'PlayStation 2'
      case 16:
        return 'PlayStation 3'
      case 17:
        return 'Nintendo 64'
      case 18:
        return 'GameCube'
      case 19:
        return 'Wii'
      case 20:
        return 'Wii U'
      case 21:
        return 'Game Boy'
      case 22:
        return 'Game Boy Color'
      case 23:
        return 'Game Boy Advance'
      case 24:
        return 'Sega Genesis'
      case 25:
        return 'Sega Saturn'
      case 26:
        return 'Sega Dreamcast'
      case 27:
        return 'Sega Game Gear'
      case 28:
        return 'Sega Master System'
      case 29:
        return 'Sega Mega Drive'
      case 30:
        return 'Sega CD'
      case 31:
        return 'Sega 32X'
      case 50:
        return 'Xbox Series X'
      case 51:
        return 'Xbox Series S'
      default:
        // Cerca nel mapping inverso come fallback
        for (const [name, id] of Object.entries(platformMapping)) {
          if (id === consoleId) {
            return name
          }
        }
        return `Console ${consoleId}`
    }
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
          name: platform.name || platform.abbreviation || getConsoleName(platform.id)
        })
      } else if (typeof platform === 'number') {
        availableConsoles.push({
          id: platform,
          name: getConsoleName(platform)
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
      const data = await searchIGDBGames(searchTerm, platform, company, page, resultsPerPage)
      setGames(data.games || [])
      setTotalResults(data.pagination?.total_returned || 0)
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

  return (
    <>
      <PageTitle>Cerca Giochi</PageTitle>

      {/* Form di ricerca */}
      <div className="px-4 py-3 mb-8 bg-white rounded-lg shadow-md dark:bg-gray-800">
        <div className="grid gap-4 md:grid-cols-3">
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
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
            >
              <option value="">Tutte le piattaforme</option>
              <option value="6">PC (Microsoft Windows)</option>
              <option value="48">PlayStation 4</option>
              <option value="167">PlayStation 5</option>
              <option value="130">Nintendo Switch</option>
              <option value="3">Linux</option>
              <option value="14">Mac</option>
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
              <TableCell>Piattaforme Disponibili</TableCell>
              <TableCell>Generi</TableCell>
              <TableCell>Sviluppatore</TableCell>
              <TableCell>Publisher</TableCell>
              <TableCell>Data di Uscita</TableCell>
              <TableCell>Valutazione</TableCell>
              <TableCell>Azioni</TableCell>
            </tr>
          </TableHeader>
          <TableBody>
            {games.map((game, i) => (
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
                        {platform.name || platform.abbreviation || `Platform ${platform.id}`}
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
        <ModalFooter className="flex justify-center">
          <Button 
            onClick={confirmAddGame}
            disabled={selectedConsoles.length === 0 || getAvailableConsoles(selectedGame).length === 0}
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