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
} from '@windmill/react-ui'
import { HeartIcon, GamesIcon } from '../icons'
import { searchIGDBGames, addGameToWishlist, addGameToLibrary, getPlatformMapping } from '../services/api'

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

  // Effettua la ricerca quando cambiano i parametri
  useEffect(() => {
    const searchGames = async () => {
      if (!searchTerm) return;
      
      setIsLoading(true)
      setError('')
      try {
        const response = await searchIGDBGames(searchTerm, platform, company, page, resultsPerPage)
        setGames(response.games || [])
        setTotalResults(response.pagination?.total_returned || 0)
      } catch (err) {
        setError('Errore durante la ricerca dei giochi: ' + (err.message || 'Errore sconosciuto'))
        console.error(err)
      } finally {
        setIsLoading(false)
      }
    }

    const timeoutId = setTimeout(() => {
      searchGames()
    }, 500) // Debounce della ricerca

    return () => clearTimeout(timeoutId)
  }, [searchTerm, platform, company, page])

  // Gestione cambio pagina
  const onPageChange = (p) => {
    setPage(p)
  }

  // Funzione per aggiungere un gioco alla wishlist
  const handleAddToWishlist = async (game) => {
    try {
      setWishlistLoading(prev => ({ ...prev, [game.igdb_id]: true }))
      
      // Determina la console/piattaforma principale del gioco usando il mapping dinamico
      let console = 6 // Default a PC
      if (game.platforms && game.platforms.length > 0) {
        // Se platforms è un array di ID numerici
        if (typeof game.platforms[0] === 'number') {
          console = game.platforms[0]
        } else if (game.platforms[0] && typeof game.platforms[0] === 'object') {
          // Se platforms è un array di oggetti
          const platformInfo = game.platforms[0]
          const platformId = platformInfo.igdb_id || platformInfo.id || platformInfo.name
          
          // Usa il mapping dinamico invece della logica hardcoded
          if (platformMapping[platformId] !== undefined) {
            console = platformMapping[platformId]
          } else {
            console = 6 // Default a PC se non trovato nel mapping
          }
        }
      }
      
      await addGameToWishlist(game.igdb_id, console)
      alert(`${game.name} aggiunto alla wishlist!`)
    } catch (err) {
      console.error('Error adding to wishlist:', err)
      alert('Gioco già presente nella wishlist')
    } finally {
      setWishlistLoading(prev => ({ ...prev, [game.igdb_id]: false }))
    }
  }

  // Funzione per aggiungere un gioco alla libreria
  const handleAddToLibrary = async (game) => {
    try {
      setLibraryLoading(prev => ({ ...prev, [game.igdb_id]: true }))
      
      // Determina la console/piattaforma principale del gioco usando il mapping dinamico
      let console = 6 // Default a PC
      if (game.platforms && game.platforms.length > 0) {
        // Se platforms è un array di ID numerici
        if (typeof game.platforms[0] === 'number') {
          console = game.platforms[0]
        } else if (game.platforms[0] && typeof game.platforms[0] === 'object') {
          // Se platforms è un array di oggetti
          const platformInfo = game.platforms[0]
          const platformId = platformInfo.igdb_id || platformInfo.id || platformInfo.name
          
          // Usa il mapping dinamico invece della logica hardcoded
          if (platformMapping[platformId] !== undefined) {
            console = platformMapping[platformId]
          } else {
            console = 6 // Default a PC se non trovato nel mapping
          }
        }
      }
      
      await addGameToLibrary(game.igdb_id, console)
      alert(`${game.name} aggiunto alla libreria!`)
    } catch (err) {
      console.error('Error adding to library:', err)
      alert('Gioco già presente nella libreria')
    } finally {
      setLibraryLoading(prev => ({ ...prev, [game.igdb_id]: false }))
    }
  }

  return (
    <>
      <PageTitle>Ricerca Giochi</PageTitle>

      {/* Sezione Ricerca */}
      <div className="px-4 py-3 mb-8 bg-white rounded-lg shadow-md dark:bg-gray-800">
        <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
          <div className="col-span-2">
            <Input
              className="mt-1"
              placeholder="Cerca un gioco su IGDB..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
            <span className="text-sm text-gray-600 dark:text-gray-400">
              Cerca tra milioni di giochi nel database IGDB
            </span>
          </div>
          <Select
            className="mt-1"
            value={platform}
            onChange={(e) => setPlatform(e.target.value)}
          >
            <option value="">Tutte le piattaforme</option>
            <option value="6">PC (Microsoft Windows)</option>
            <option value="48">PlayStation 4</option>
            <option value="167">PlayStation 5</option>
            <option value="49">Xbox One</option>
            <option value="169">Xbox Series X|S</option>
            <option value="130">Nintendo Switch</option>
          </Select>
        </div>
      </div>

      {/* Messaggi di stato */}
      {isLoading && <p className="text-gray-600 dark:text-gray-400">Ricerca su IGDB in corso...</p>}
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
              <TableCell>Piattaforme</TableCell>
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
                    <img
                      className="hidden w-12 h-12 mr-3 md:block object-cover rounded"
                      src={
                        game.cover?.url
                          ? (game.cover.url.startsWith('http') ? game.cover.url : `https:${game.cover.url}`)
                          : 'https://via.placeholder.com/48x48?text=No+Image'
                      }
                      alt={game.name}
                    />
                    <div>
                      <p className="font-semibold">{game.name}</p>
                      <p className="text-xs text-gray-600 dark:text-gray-400">
                        {game.companies?.developers?.join(', ')}
                      </p>
                    </div>
                  </div>
                </TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-1">
                    {game.platforms?.map((platform, idx) => (
                      <Badge key={idx} type="success">
                        {platform.abbreviation || platform.name}
                      </Badge>
                    ))}
                  </div>
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
    </>
  )
}

export default GameSearch 