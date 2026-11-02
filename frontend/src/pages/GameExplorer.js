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
import { HeartIcon, GamesIcon, SearchIcon, RefreshIcon } from '../icons'
import { getAllGames, getGenres, getCompanies, getGameModes, getConsoles, updateGameMetadata, searchIGDBGames, getConsoleNames } from '../services/api'
import { useToast } from '../context/ToastContext'
import GameNameLink from '../components/GameNameLink'

function GameExplorer() {
  const { notify } = useToast()
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

  // Stati per la modal di aggiornamento metadati
  const [isMetadataModalOpen, setIsMetadataModalOpen] = useState(false)
  const [selectedGameForMetadata, setSelectedGameForMetadata] = useState(null)
  const [searchResults, setSearchResults] = useState([])
  const [searchQuery, setSearchQuery] = useState('')
  const [isSearching, setIsSearching] = useState(false)
  const [searchError, setSearchError] = useState('')

  // Cache per i nomi delle console
  const [consoleNamesCache, setConsoleNamesCache] = useState({})

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
      
      // Carica i nomi delle console per i risultati
      loadConsoleNames(response.games || [])
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
    if (!query.trim()) return;
    
    setIsSearching(true);
    setSearchError('');
    try {
      // Limita i risultati a massimo 10 record per la ricerca metadati
      const response = await searchIGDBGames(query, {
        page: 1,
        limit: 10
      });
      setSearchResults(response.games || []);
    } catch (error) {
      setSearchError(error.message || 'Errore durante la ricerca');
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  // Funzione per aggiornare i metadati
  const handleUpdateMetadata = async (igdbGame) => {
    if (!selectedGameForMetadata?._id) return;

    try {
      // Verifica che igdbGame.igdb_id esista e sia convertibile in numero
      if (!igdbGame?.igdb_id) {
        throw new Error('ID IGDB non trovato');
      }

      // Converti l'ID in numero se è una stringa
      const igdbId = typeof igdbGame.igdb_id === 'string' ? parseInt(igdbGame.igdb_id, 10) : igdbGame.igdb_id;
      
      // Verifica che l'ID sia un numero valido
      if (isNaN(igdbId) || igdbId <= 0) {
        throw new Error('ID IGDB non valido');
      }


      await updateGameMetadata(selectedGameForMetadata._id, igdbId);
      await searchGames(); // Ricarica la lista dei giochi
      setIsMetadataModalOpen(false); // Chiude la modal
      notify('Metadati aggiornati con successo', 'success');
    } catch (error) {
      console.error('Errore nell\'aggiornamento metadati:', error);

      // Gestione specifica per l'errore di chiave duplicata
      if (error.message && error.message.includes('E11000 duplicate key error')) {
        notify('Gioco già presente, scegline un altro', 'error');
      } else {
        notify(error.message || 'Errore durante l\'aggiornamento dei metadati', 'error');
      }
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
            <strong>Suggerimento:</strong> Usa il pulsante <GamesIcon className="w-4 h-4 inline text-blue-500" /> per aggiungere alla libreria (giochi che possiedi) 
            e il pulsante <HeartIcon className="w-4 h-4 inline text-red-500" /> per aggiungere alla wishlist (giochi che desideri).
          </p>
        </div>
        <Table>
          <TableHeader>
            <tr>
              <TableCell className="w-1/4 min-w-64">
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
              <TableCell className="w-1/6 min-w-48">Console</TableCell>
              <TableCell className="w-1/6 min-w-48">Generi</TableCell>
              <TableCell className="w-1/8 min-w-32">Publisher</TableCell>
              <TableCell className="w-1/8 min-w-32">Sviluppatore</TableCell>
              <TableCell className="w-1/8 min-w-40">Modalità di Gioco</TableCell>
              <TableCell className="w-1/8 min-w-32">ID Piattaforme</TableCell>
              <TableCell className="w-1/8 min-w-32">
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
              <TableCell className="w-1/8 min-w-32">
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
              <TableCell className="w-1/8 min-w-32">
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
              <TableCell className="w-1/8 min-w-32">Stato</TableCell>
              <TableCell className="w-1/8 min-w-32">Azioni</TableCell>
            </tr>
          </TableHeader>
          <TableBody>
            {games.map((game, i) => (
              <TableRow key={i}>
                <TableCell className="w-1/4 min-w-64">
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

                    <div className="flex-1 min-w-0">
                      <GameNameLink name={game.name} gameId={game.igdb_id} className="truncate block" />
                      {game.original_name && game.original_name !== game.name && (
                        <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                          {game.original_name}
                        </p>
                      )}
                    </div>
                  </div>
                </TableCell>
                <TableCell className="w-1/6 min-w-48">
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
                <TableCell className="w-1/6 min-w-48">
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
                <TableCell className="w-1/8 min-w-32">
                  <div className="text-sm truncate">
                    {game.publisher_names?.join(', ') || game.publisher || 'N/A'}
                  </div>
                </TableCell>
                <TableCell className="w-1/8 min-w-32">
                  <div className="text-sm truncate">
                    {game.developer_names?.join(', ') || game.developer || 'N/A'}
                  </div>
                </TableCell>
                <TableCell className="w-1/8 min-w-40">
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
                <TableCell className="w-1/8 min-w-32">
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
                <TableCell className="w-1/8 min-w-32">
                  <span className="text-sm">
                    {game.release_date ? new Date(game.release_date * 1000).toLocaleDateString() : 'TBA'}
                  </span>
                </TableCell>
                <TableCell className="w-1/8 min-w-32">
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
                <TableCell className="w-1/8 min-w-32">
                  <span className="text-sm">
                    {game.total_rating_count || 0}
                  </span>
                </TableCell>
                <TableCell className="w-1/8 min-w-32">
                  <div className="text-sm">
                    {game.toVerify ? (
                      <Badge type="warning">Da Verificare</Badge>
                    ) : (
                      <Badge type="success">Verificato</Badge>
                    )}
                  </div>
                </TableCell>
                <TableCell className="w-1/8 min-w-32">
                  <div className="flex items-center space-x-2">
                    <Button
                      layout="link"
                      size="small"
                      aria-label="Update Metadata"
                      onClick={() => openMetadataModal(game)}
                      className="text-blue-600 hover:text-blue-900"
                      title="Cerca e aggiorna metadati da IGDB"
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

      <Modal isOpen={isMetadataModalOpen} onClose={() => setIsMetadataModalOpen(false)}>
        <ModalHeader>
          Aggiorna Metadati - {selectedGameForMetadata?.name}
        </ModalHeader>
        <ModalBody>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Cerca un gioco su IGDB per sostituire i metadati attuali
              </label>
              <div className="flex space-x-2">
                <Input
                  className="flex-1"
                  placeholder="Cerca gioco..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && searchIGDBGame(searchQuery)}
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

            <div className="mt-4 space-y-4 h-64 overflow-y-auto border rounded-lg">
              {searchResults.map((result) => (
                <div
                  key={result.id}
                  className="flex items-center justify-between p-3 border-b last:border-b-0 hover:bg-gray-50 dark:hover:bg-gray-700"
                >
                  <div className="flex items-center space-x-3 flex-1 min-w-0">
                    {result.cover?.url && (
                      <img
                        src={result.cover.url}
                        alt={result.name}
                        className="w-12 h-12 object-cover rounded flex-shrink-0"
                        onError={(e) => {
                          e.target.onerror = null
                          e.target.src = '/default_cover.png'
                        }}
                      />
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="font-medium truncate">{result.name}</div>
                      <div className="text-sm text-gray-500">
                        {result.first_release_date ? new Date(result.first_release_date * 1000).getFullYear() : 'N/A'} 
                        {result.rating && ` • ${Math.round(result.rating)}/100`}
                      </div>
                      {result.platforms && (
                        <div className="text-xs text-gray-400 truncate">
                          Piattaforme: {result.platforms.map(p => p.name).join(', ')}
                        </div>
                      )}
                    </div>
                  </div>
                  <Button
                    size="small"
                    onClick={() => handleUpdateMetadata(result)}
                    className="w-20 ml-3 flex-shrink-0"
                  >
                    Usa Dati
                  </Button>
                </div>
              ))}
              {searchResults.length === 0 && (
                <div className="p-8 text-center text-gray-500">
                  Nessun risultato trovato. Prova a cercare un gioco.
                </div>
              )}
            </div>
          </div>
        </ModalBody>
        <ModalFooter>
          <div className="w-full flex justify-between items-center">
            <span className="text-sm text-gray-500">
              I metadati del gioco verranno sostituiti con quelli selezionati
            </span>
            <Button layout="outline" onClick={() => setIsMetadataModalOpen(false)}>
              Chiudi
            </Button>
          </div>
        </ModalFooter>
      </Modal>
    </>
  )
}

export default GameExplorer 