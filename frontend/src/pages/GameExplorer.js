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
import { HeartIcon, GamesIcon, SearchIcon, FilterIcon, RefreshIcon } from '../icons'
import { getAllGames, getGenres, getCompanies, getGameModes, getConsoles, addGameToWishlist, addGameToLibrary, getLibraryConsolesForGame, getWishlistConsolesForGame, updateGameMetadata, searchIGDBGames } from '../services/api'

function GameExplorer() {
  // Stati per i filtri
  const [filters, setFilters] = useState({
    name: '',
    genres: [],
    platforms: [],
    developer: [],
    publisher: '',
    game_mode: []
  })
  
  // Stati per i risultati
  const [games, setGames] = useState([])
  const [page, setPage] = useState(1)
  const [totalResults, setTotalResults] = useState(0)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [wishlistLoading, setWishlistLoading] = useState({})
  const [libraryLoading, setLibraryLoading] = useState({})
  
  // Stati per i dati di riferimento
  const [genres, setGenres] = useState([])
  const [companies, setCompanies] = useState([])
  const [gameModes, setGameModes] = useState([])
  const [consoles, setConsoles] = useState([])
  
  // Stati per l'ordinamento
  const [sortBy, setSortBy] = useState('name')
  const [sortOrder, setSortOrder] = useState('asc')
  
  // Stati per la modal dei filtri
  const [isFilterModalOpen, setIsFilterModalOpen] = useState(false)
  
  // Stati per la modal delle immagini
  const [isImageModalOpen, setIsImageModalOpen] = useState(false)
  const [selectedGameImages, setSelectedGameImages] = useState([])
  const [currentImageIndex, setCurrentImageIndex] = useState(0)
  
  // Stati per la modal di selezione console
  const [isConsoleModalOpen, setIsConsoleModalOpen] = useState(false)
  const [selectedGame, setSelectedGame] = useState(null)
  const [selectedAction, setSelectedAction] = useState('') // 'wishlist' o 'library'
  const [selectedConsole, setSelectedConsole] = useState(null)
  const [alreadyAddedConsoles, setAlreadyAddedConsoles] = useState([])
  
  // Stati per la modal di aggiornamento metadati
  const [isMetadataModalOpen, setIsMetadataModalOpen] = useState(false)
  const [selectedGameForMetadata, setSelectedGameForMetadata] = useState(null)
  const [searchResults, setSearchResults] = useState([])
  const [searchQuery, setSearchQuery] = useState('')
  const [isSearching, setIsSearching] = useState(false)
  const [searchError, setSearchError] = useState('')

  const resultsPerPage = 20

  // Carica i dati di riferimento
  useEffect(() => {
    const loadReferenceData = async () => {
      try {
        const [genresData, companiesData, gameModesData, consolesData] = await Promise.all([
          getGenres(),
          getCompanies(),
          getGameModes(),
          getConsoles()
        ])
        
        setGenres(genresData?.genres || genresData || [])
        setCompanies(companiesData?.companies || companiesData || [])
        setGameModes(gameModesData?.game_modes || gameModesData || [])
        setConsoles(consolesData || [])
      } catch (err) {
        console.error('Errore nel caricamento dei dati di riferimento:', err)
      }
    }
    
    loadReferenceData()
  }, [])

  // Funzione per cercare i giochi
  const searchGames = async () => {
    setIsLoading(true)
    setError('')
    try {
      // Prepara i parametri di ricerca, escludendo quelli vuoti
      const searchParams = {
        page,
        limit: resultsPerPage,
        sort_by: sortBy,
        sort_order: sortOrder
      }
      
      // Aggiungi solo i filtri non vuoti
      if (filters.name && filters.name.trim()) {
        searchParams.name = filters.name
      }
      if (filters.genres && filters.genres.length > 0) {
        searchParams.genres = filters.genres
      }
      if (filters.platforms && filters.platforms.length > 0) {
        searchParams.platforms = filters.platforms
      }
      if (filters.developer && filters.developer.length > 0) {
        searchParams.developer = filters.developer
      }
      if (filters.publisher && filters.publisher.trim()) {
        searchParams.publisher = filters.publisher
      }
      if (filters.game_mode && filters.game_mode.length > 0) {
        searchParams.game_mode = filters.game_mode
      }
      
      const response = await getAllGames(searchParams)
      setGames(response.games || [])
      setTotalResults(response.pagination?.total_count || 0)
    } catch (err) {
      setError('Errore durante la ricerca dei giochi: ' + (err.message || 'Errore sconosciuto'))
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }

  // Effettua la ricerca quando cambiano i parametri
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      searchGames()
    }, 500) // Debounce della ricerca

    return () => clearTimeout(timeoutId)
  }, [filters, sortBy, sortOrder, page])

  // Gestione cambio pagina
  const onPageChange = (p) => {
    setPage(p)
  }

  // Gestione filtri
  const handleFilterChange = (key, value) => {
    setFilters(prev => ({
      ...prev,
      [key]: value
    }))
    setPage(1) // Reset alla prima pagina quando cambiano i filtri
  }

  // Gestione ordinamento
  const handleSortChange = (field) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(field)
      setSortOrder('asc')
    }
    setPage(1)
  }

  // Funzione per aprire la modal di selezione console
  const openConsoleModal = async (game, action) => {
    setSelectedGame(game)
    setSelectedAction(action)
    setSelectedConsole(null)
    setIsConsoleModalOpen(true)
    
    // Carica le console già aggiunte per questo gioco
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
        alert(`${selectedGame.name} aggiunto alla wishlist per ${getConsoleName(selectedConsole)}!`)
      } else if (selectedAction === 'library') {
        setLibraryLoading(prev => ({ ...prev, [selectedGame._id]: true }))
        await addGameToLibrary(selectedGame.igdb_id || selectedGame._id, selectedConsole)
        alert(`${selectedGame.name} aggiunto alla libreria per ${getConsoleName(selectedConsole)}!`)
      }
      closeConsoleModal()
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

  // Reset filtri
  const resetFilters = () => {
    setFilters({
      name: '',
      genres: [],
      platforms: [],
      developer: [],
      publisher: '',
      game_mode: []
    })
    setSortBy('name')
    setSortOrder('asc')
    setPage(1)
  }

  // Funzione per aprire la modal delle immagini
  const openImageModal = (game) => {
    const images = []
    
    // Aggiungi l'immagine di copertina se disponibile
    if (game.cover_image) {
      images.push({ url: game.cover_image, type: 'Copertina' })
    }
    
    // Aggiungi gli screenshots se disponibili
    if (game.screenshots) {
      const screenshotUrls = game.screenshots.split(',').filter(url => url.trim())
      screenshotUrls.forEach(url => {
        images.push({ url: url.trim(), type: 'Screenshot' })
      })
    }
    
    // Aggiungi gli artworks se disponibili
    if (game.artworks) {
      const artworkUrls = game.artworks.split(',').filter(url => url.trim())
      artworkUrls.forEach(url => {
        images.push({ url: url.trim(), type: 'Artwork' })
      })
    }
    
    if (images.length > 0) {
      setSelectedGameImages(images)
      setCurrentImageIndex(0)
      setIsImageModalOpen(true)
    } else {
      alert('Nessuna immagine disponibile per questo gioco')
    }
  }

  // Funzione per chiudere la modal delle immagini
  const closeImageModal = () => {
    setIsImageModalOpen(false)
    setSelectedGameImages([])
    setCurrentImageIndex(0)
  }

  // Funzione per navigare tra le immagini
  const nextImage = () => {
    setCurrentImageIndex((prev) => 
      prev === selectedGameImages.length - 1 ? 0 : prev + 1
    )
  }

  const prevImage = () => {
    setCurrentImageIndex((prev) => 
      prev === 0 ? selectedGameImages.length - 1 : prev - 1
    )
  }

  // Funzione per aprire la modal di aggiornamento metadati
  const openMetadataModal = (game) => {
    setSelectedGameForMetadata(game)
    setIsMetadataModalOpen(true)
    setSearchResults([])
    setSearchQuery('')
    setSearchError('')
  }

  // Funzione per cercare giochi su IGDB
  const searchIGDBGame = async (query) => {
    if (!query.trim()) return
    
    setIsSearching(true)
    setSearchError('')
    try {
      const response = await searchIGDBGames(query)
      setSearchResults(response.games || [])
    } catch (error) {
      setSearchError(error.message || 'Errore durante la ricerca')
      setSearchResults([])
    } finally {
      setIsSearching(false)
    }
  }

  // Funzione per aggiornare i metadati
  const handleUpdateMetadata = async (game) => {
    if (!game?._id) return;
    
    if (!game?.igdb_id) {
      alert('Questo gioco non ha un ID IGDB nel database. Impossibile aggiornare i metadati.');
      return;
    }

    try {
      await updateGameMetadata(game._id, game.igdb_id);
      await searchGames();
      alert('Metadati aggiornati con successo!');
    } catch (error) {
      alert(error.message || 'Errore durante l\'aggiornamento dei metadati');
    }
  };

  return (
    <>
      <PageTitle>Esplora Giochi</PageTitle>

      {/* Sezione Filtri */}
      <div className="px-4 py-3 mb-8 bg-white rounded-lg shadow-md dark:bg-gray-800">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-700 dark:text-gray-300">
            Filtri di Ricerca
          </h3>
          {/* <Button
            layout="outline"
            size="small"
            onClick={() => setIsFilterModalOpen(true)}
            icon={FilterIcon}
          >
            Filtri Avanzati
          </Button> */}
        </div>
        
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <div>
            <Input
              className="mt-1"
              placeholder="Cerca per nome..."
              value={filters.name}
              onChange={(e) => handleFilterChange('name', e.target.value)}
              icon={SearchIcon}
            />
          </div>
          
          <div>
            <Select
              className="mt-1"
              value={sortBy}
              onChange={(e) => handleSortChange(e.target.value)}
            >
              <option value="name">Nome</option>
              <option value="release_date">Data di Uscita</option>
              <option value="total_rating">Valutazione</option>
              <option value="total_rating_count">Numero Recensioni</option>
            </Select>
          </div>
          
          <div>
            <Button
              layout="outline"
              size="small"
              onClick={resetFilters}
            >
              Reset Filtri
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
              <TableCell>
                <Button
                  layout="link"
                  onClick={() => handleSortChange('name')}
                  className="flex items-center"
                >
                  Gioco
                  {sortBy === 'name' && (
                    <span className="ml-1">{sortOrder === 'asc' ? '↑' : '↓'}</span>
                  )}
                </Button>
              </TableCell>
              <TableCell>Piattaforme</TableCell>
              <TableCell>Generi</TableCell>
              <TableCell>Publisher</TableCell>
              <TableCell>Sviluppatore</TableCell>
              <TableCell>Modalità di Gioco</TableCell>
              <TableCell>ID Piattaforme</TableCell>
              <TableCell>
                <Button
                  layout="link"
                  onClick={() => handleSortChange('release_date')}
                  className="flex items-center"
                >
                  Data di Uscita
                  {sortBy === 'release_date' && (
                    <span className="ml-1">{sortOrder === 'asc' ? '↑' : '↓'}</span>
                  )}
                </Button>
              </TableCell>
              <TableCell>
                <Button
                  layout="link"
                  onClick={() => handleSortChange('total_rating')}
                  className="flex items-center"
                >
                  Valutazione
                  {sortBy === 'total_rating' && (
                    <span className="ml-1">{sortOrder === 'asc' ? '↑' : '↓'}</span>
                  )}
                </Button>
              </TableCell>
              <TableCell>
                <Button
                  layout="link"
                  onClick={() => handleSortChange('total_rating_count')}
                  className="flex items-center"
                >
                  Recensioni
                  {sortBy === 'total_rating_count' && (
                    <span className="ml-1">{sortOrder === 'asc' ? '↑' : '↓'}</span>
                  )}
                </Button>
              </TableCell>
              <TableCell>Stato</TableCell>
              <TableCell>Azioni</TableCell>
            </tr>
          </TableHeader>
          <TableBody>
            {games.map((game, i) => (
              <TableRow key={i}>
                <TableCell>
                  <div className="flex items-center text-sm">
                    {/* <img
                      className="hidden w-12 h-12 mr-3 md:block object-cover rounded"
                      src={game.cover_image || 'placeholder-image-url.jpg'}
                      alt={game.name}
                      onError={(e) => {
                        e.target.src = 'placeholder-image-url.jpg'
                      }}
                    /> */}

                    <img
                      className="hidden w-12 h-12 mr-3 md:block object-cover rounded"
                      src={game.cover_image || '/default_cover.png'}
                      alt={game.name}
                      onError={(e) => {
                        e.target.onerror = null
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
                    {!game.platform_names && game.platforms?.map((platform, idx) => (
                      <Badge key={idx} type="success">
                        {platform.abbreviation || platform.name}
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
                    {!game.genre_names && game.genres?.map((genre, idx) => (
                      <Badge key={idx} type="info">
                        {genre.name}
                      </Badge>
                    ))}
                  </div>
                </TableCell>
                <TableCell>
                  <div className="text-sm">
                    {game.publisher_names?.join(', ') || game.publisher || 'N/A'}
                  </div>
                </TableCell>
                <TableCell>
                  <div className="text-sm">
                    {game.developer_names?.join(', ') || game.developer || 'N/A'}
                  </div>
                </TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-1">
                    {game.game_mode_names?.map((mode, idx) => (
                      <Badge key={idx} type="warning">
                        {mode}
                      </Badge>
                    ))}
                    {!game.game_mode_names && game.game_modes?.map((mode, idx) => (
                      <Badge key={idx} type="warning">
                        {mode.name}
                      </Badge>
                    ))}
                  </div>
                </TableCell>
                <TableCell>
                  <div className="text-xs space-y-1">
                    {game.steam_game_id && (
                      <div className="text-blue-600 dark:text-blue-400">
                        Steam: {game.steam_game_id}
                      </div>
                    )}
                    {game.psn_game_id && (
                      <div className="text-green-600 dark:text-green-400">
                        PSN: {game.psn_game_id}
                      </div>
                    )}
                    {!game.steam_game_id && !game.psn_game_id && (
                      <span className="text-gray-400">N/A</span>
                    )}
                  </div>
                </TableCell>
                <TableCell>
                  <span className="text-sm">
                    {game.release_date ? new Date(game.release_date * 1000).toLocaleDateString() : 'TBA'}
                  </span>
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
                  <span className="text-sm">
                    {game.total_rating_count || 0}
                  </span>
                </TableCell>
                <TableCell>
                  <div className="text-sm">
                    {game.toVerify ? (
                      <Badge type="warning">Da Verificare</Badge>
                    ) : (
                      <Badge type="success">Verificato</Badge>
                    )}
                  </div>
                </TableCell>
                <TableCell>
                  <div className="flex items-center space-x-2">
                    <Button
                      layout="link"
                      size="small"
                      aria-label="Update Metadata"
                      onClick={() => handleUpdateMetadata(game)}
                      className="text-blue-600 hover:text-blue-900"
                      title={game?.igdb_id ? 'Aggiorna metadati da IGDB' : 'ID IGDB non disponibile'}
                    >
                      <RefreshIcon className="w-5 h-5" />
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

      {/* Modal Filtri Avanzati */}
      <Modal isOpen={isFilterModalOpen} onClose={() => setIsFilterModalOpen(false)}>
        <ModalHeader>Filtri Avanzati</ModalHeader>
        <ModalBody>
          <div className="grid gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Generi
              </label>
              <Select
                multiple
                value={filters.genres}
                onChange={(e) => {
                  const selectedOptions = Array.from(e.target.selectedOptions, option => option.value)
                  handleFilterChange('genres', selectedOptions)
                }}
              >
                {genres.map((genre) => (
                  <option key={genre._id} value={genre._id}>
                    {genre.genre_name || genre.name}
                  </option>
                ))}
              </Select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Piattaforme
              </label>
              <Select
                multiple
                value={filters.platforms}
                onChange={(e) => {
                  const selectedOptions = Array.from(e.target.selectedOptions, option => option.value)
                  handleFilterChange('platforms', selectedOptions)
                }}
              >
                {consoles.map((console) => (
                  <option key={console._id} value={console._id}>
                    {console.name}
                  </option>
                ))}
              </Select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Sviluppatori
              </label>
              <Select
                multiple
                value={filters.developer}
                onChange={(e) => {
                  const selectedOptions = Array.from(e.target.selectedOptions, option => option.value)
                  handleFilterChange('developer', selectedOptions)
                }}
              >
                {companies.map((company) => (
                  <option key={company._id} value={company._id}>
                    {company.company_name || company.name}
                  </option>
                ))}
              </Select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Publisher
              </label>
              <Select
                value={filters.publisher}
                onChange={(e) => handleFilterChange('publisher', e.target.value)}
              >
                <option value="">Tutti i publisher</option>
                {companies.map((company) => (
                  <option key={company._id} value={company._id}>
                    {company.company_name || company.name}
                  </option>
                ))}
              </Select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Modalità di Gioco
              </label>
              <Select
                multiple
                value={filters.game_mode}
                onChange={(e) => {
                  const selectedOptions = Array.from(e.target.selectedOptions, option => option.value)
                  handleFilterChange('game_mode', selectedOptions)
                }}
              >
                {gameModes.map((mode) => (
                  <option key={mode._id} value={mode._id}>
                    {mode.game_mode_name || mode.name}
                  </option>
                ))}
              </Select>
            </div>
          </div>
        </ModalBody>
        <ModalFooter>
          <Button layout="outline" onClick={() => setIsFilterModalOpen(false)}>
            Chiudi
          </Button>
        </ModalFooter>
      </Modal>

      {/* Modal Immagini */}
      <Modal isOpen={isImageModalOpen} onClose={closeImageModal} size="large">
        <ModalHeader>
          <div className="flex items-center justify-between">
            <span>Immagini del Gioco</span>
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-500">
                {currentImageIndex + 1} di {selectedGameImages.length}
              </span>
            </div>
          </div>
        </ModalHeader>
        <ModalBody>
          {selectedGameImages.length > 0 && (
            <div className="relative">
              <div className="flex justify-center mb-4">
                {/* <img
                  src={selectedGameImages[currentImageIndex].url}
                  alt={`${selectedGameImages[currentImageIndex].type} ${currentImageIndex + 1}`}
                  className="max-w-full max-h-96 object-contain rounded"
                  onError={(e) => {
                    e.target.src = 'placeholder-image-url.jpg'
                  }}
                /> */}
                <img
                  src={selectedGameImages[currentImageIndex].url}
                  alt={`${selectedGameImages[currentImageIndex].type} ${currentImageIndex + 1}`}
                  className="max-w-full max-h-96 object-contain rounded"
                  onError={(e) => {
                    e.target.onerror = null
                    e.target.src = '/default_cover.png'
                  }}
                />
              </div>
              <div className="text-center mb-4">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  {selectedGameImages[currentImageIndex].type}
                </span>
              </div>
              {selectedGameImages.length > 1 && (
                <div className="flex justify-center space-x-2">
                  <Button
                    layout="outline"
                    size="small"
                    onClick={prevImage}
                  >
                    ← Precedente
                  </Button>
                  <Button
                    layout="outline"
                    size="small"
                    onClick={nextImage}
                  >
                    Successiva →
                  </Button>
                </div>
              )}
            </div>
          )}
        </ModalBody>
        <ModalFooter>
          <Button layout="outline" onClick={closeImageModal}>
            Chiudi
          </Button>
        </ModalFooter>
      </Modal>

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

      {/* Modal per l'aggiornamento dei metadati */}
      <Modal isOpen={isMetadataModalOpen} onClose={() => setIsMetadataModalOpen(false)}>
        <ModalHeader>
          Aggiorna Metadati - {selectedGameForMetadata?.name}
        </ModalHeader>
        <ModalBody>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Cerca gioco su IGDB
              </label>
              <div className="flex space-x-2">
                <Input
                  className="flex-1"
                  placeholder="Cerca gioco..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
                <Button onClick={() => searchIGDBGame(searchQuery)} disabled={isSearching}>
                  {isSearching ? 'Ricerca...' : 'Cerca'}
                </Button>
              </div>
            </div>

            {searchError && (
              <div className="text-red-600 dark:text-red-400 text-sm">
                {searchError}
              </div>
            )}

            <div className="mt-4 space-y-4">
              {searchResults.map((result) => (
                <div
                  key={result.igdb_id}
                  className="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
                >
                  <div className="flex items-center space-x-3">
                    {result.cover?.thumb_url && (
                      <img
                        src={result.cover.thumb_url}
                        alt={result.name}
                        className="w-12 h-12 object-cover rounded"
                        onError={(e) => {
                          e.target.onerror = null
                          e.target.src = '/default_cover.png'
                        }}
                      />
                    )}
                    <div>
                      <div className="font-medium">{result.name}</div>
                      <div className="text-sm text-gray-500">
                        {result.release_date ? new Date(result.release_date * 1000).getFullYear() : 'N/A'} 
                        {result.total_rating && ` • ${Math.round(result.total_rating)}/100`}
                      </div>
                    </div>
                  </div>
                  <Button
                    size="small"
                    onClick={() => handleUpdateMetadata(result)}
                  >
                    Usa Questi Metadati
                  </Button>
                </div>
              ))}
            </div>
          </div>
        </ModalBody>
        <ModalFooter>
          <Button layout="outline" onClick={() => setIsMetadataModalOpen(false)}>
            Chiudi
          </Button>
        </ModalFooter>
      </Modal>
    </>
  )
}

export default GameExplorer 