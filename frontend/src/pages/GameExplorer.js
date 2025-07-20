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
import { HeartIcon, GamesIcon, SearchIcon, FilterIcon } from '../icons'
import { getAllGames, getGenres, getCompanies, getGameModes, getConsoles, addGameToWishlist, addGameToLibrary } from '../services/api'

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

  // Effettua la ricerca quando cambiano i parametri
  useEffect(() => {
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

  // Funzione per aggiungere un gioco alla wishlist
  const handleAddToWishlist = async (game) => {
    try {
      setWishlistLoading(prev => ({ ...prev, [game._id]: true }))
      
      // Determina la piattaforma principale del gioco
      let platform = 'manual'
      if (game.platforms && game.platforms.length > 0) {
        const platformInfo = game.platforms[0]
        const platformId = platformInfo.id || platformInfo.name
        
        if ([6, 'PC (Microsoft Windows)', 'PC'].includes(platformId)) {
          platform = 'steam'
        } else if ([48, 167, 'PlayStation 4', 'PlayStation 5', 'PS4', 'PS5'].includes(platformId)) {
          platform = 'psn'
        } else {
          platform = 'manual'
        }
      }
      
      await addGameToWishlist(game.igdb_id || game._id, platform)
      alert(`${game.name} aggiunto alla wishlist!`)
    } catch (err) {
      console.error('Error adding to wishlist:', err)
      alert(err.message || 'Errore nell\'aggiunta alla wishlist')
    } finally {
      setWishlistLoading(prev => ({ ...prev, [game._id]: false }))
    }
  }

  // Funzione per aggiungere un gioco alla libreria
  const handleAddToLibrary = async (game) => {
    try {
      setLibraryLoading(prev => ({ ...prev, [game._id]: true }))
      
      // Determina la piattaforma principale del gioco
      let platform = 'manual'
      if (game.platforms && game.platforms.length > 0) {
        const platformInfo = game.platforms[0]
        const platformId = platformInfo.id || platformInfo.name
        
        if ([6, 'PC (Microsoft Windows)', 'PC'].includes(platformId)) {
          platform = 'steam'
        } else if ([48, 167, 'PlayStation 4', 'PlayStation 5', 'PS4', 'PS5'].includes(platformId)) {
          platform = 'psn'
        } else {
          platform = 'manual'
        }
      }
      
      await addGameToLibrary(game.igdb_id || game._id, platform)
      alert(`${game.name} aggiunto alla libreria!`)
    } catch (err) {
      console.error('Error adding to library:', err)
      alert(err.message || 'Errore nell\'aggiunta alla libreria')
    } finally {
      setLibraryLoading(prev => ({ ...prev, [game._id]: false }))
    }
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

  return (
    <>
      <PageTitle>Esplora Giochi</PageTitle>

      {/* Sezione Filtri */}
      <div className="px-4 py-3 mb-8 bg-white rounded-lg shadow-md dark:bg-gray-800">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-700 dark:text-gray-300">
            Filtri di Ricerca
          </h3>
          <Button
            layout="outline"
            size="small"
            onClick={() => setIsFilterModalOpen(true)}
            icon={FilterIcon}
          >
            Filtri Avanzati
          </Button>
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
              <TableCell>Recensioni</TableCell>
              <TableCell>Stato</TableCell>
            </tr>
          </TableHeader>
          <TableBody>
            {games.map((game, i) => (
              <TableRow key={i}>
                <TableCell>
                  <div className="flex items-center text-sm">
                    <img
                      className="hidden w-12 h-12 mr-3 md:block object-cover rounded"
                      src={game.cover_image || 'placeholder-image-url.jpg'}
                      alt={game.name}
                      onError={(e) => {
                        e.target.src = 'placeholder-image-url.jpg'
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
                <img
                  src={selectedGameImages[currentImageIndex].url}
                  alt={`${selectedGameImages[currentImageIndex].type} ${currentImageIndex + 1}`}
                  className="max-w-full max-h-96 object-contain rounded"
                  onError={(e) => {
                    e.target.src = 'placeholder-image-url.jpg'
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
    </>
  )
}

export default GameExplorer 