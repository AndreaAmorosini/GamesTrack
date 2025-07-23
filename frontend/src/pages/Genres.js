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
} from '@windmill/react-ui'
import { SearchIcon, TagIcon, GamepadIcon } from '../icons'
import { getGenres } from '../services/api'

function Genres() {
  // Stati per i dati
  const [genres, setGenres] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  
  // Stati per i filtri
  const [nameFilter, setNameFilter] = useState('')
  
  // Stati per la paginazione
  const [page, setPage] = useState(1)
  const [totalResults, setTotalResults] = useState(0)
  const resultsPerPage = 20

  // Carica i generi
  const fetchGenres = async () => {
    setIsLoading(true)
    setError('')
    try {
      const params = {
        page,
        limit: resultsPerPage
      }
      if (nameFilter) params.name = nameFilter
      
      const response = await getGenres(params)
      setGenres(response.genres || response || [])
      setTotalResults(response.pagination?.total_count || response?.length || 0)
    } catch (err) {
      setError('Errore durante il caricamento dei generi: ' + (err.message || 'Errore sconosciuto'))
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }

  // Carica i generi quando cambiano i filtri o la pagina
  useEffect(() => {
    const fetchGenres = async () => {
      setIsLoading(true)
      setError('')
      try {
        const response = await getGenres({
          page,
          limit: resultsPerPage,
          name: nameFilter
        })
        setGenres(response.genres || [])
        setTotalResults(response.pagination?.total_count || 0)
      } catch (err) {
        // Non mostrare errori se è un errore di autenticazione
        if (err.message !== 'Sessione scaduta') {
          setError('Errore durante il caricamento dei generi: ' + err.message)
        }
        console.error(err)
      } finally {
        setIsLoading(false)
      }
    }

    const timeoutId = setTimeout(() => {
      fetchGenres()
    }, 500) // Debounce della ricerca

    return () => clearTimeout(timeoutId)
  }, [nameFilter, page])

  // Gestione cambio pagina
  const onPageChange = (p) => {
    setPage(p)
    // Scroll to top quando cambia pagina
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  // Reset filtri
  const resetFilters = () => {
    setNameFilter('')
    setPage(1)
  }

  // Funzione per ottenere il colore del badge basato sul nome del genere
  const getGenreColor = (genreName) => {
    const colorMap = {
      'Action': 'danger',
      'Adventure': 'success',
      'RPG': 'warning',
      'Strategy': 'info',
      'Simulation': 'success',
      'Sports': 'danger',
      'Racing': 'warning',
      'Fighting': 'danger',
      'Shooter': 'danger',
      'Puzzle': 'info',
      'Platform': 'success',
      'Horror': 'danger',
      'Stealth': 'warning',
      'Survival': 'danger',
      'Visual Novel': 'info',
      'Educational': 'success',
      'Music': 'warning',
      'Party': 'success',
      'Sandbox': 'info',
      'Tower Defense': 'warning',
      'Roguelike': 'danger',
      'Metroidvania': 'success',
      'Open World': 'info',
      'Linear': 'warning',
      'Turn-based': 'info',
      'Real-time': 'danger',
      'Tactical': 'warning',
      'Grand Strategy': 'info',
      '4X': 'warning',
      'MOBA': 'danger',
      'Battle Royale': 'danger',
      'MMO': 'success',
      'Co-op': 'success',
      'Competitive': 'danger',
      'Casual': 'info',
      'Hardcore': 'danger',
      'Indie': 'warning',
      'AAA': 'success',
      'Retro': 'info',
      'Modern': 'success',
      'Classic': 'warning'
    }
    
    return colorMap[genreName] || 'default'
  }

  // Funzione per ottenere l'icona del genere
  const getGenreIcon = (genreName) => {
    const iconMap = {
      'Action': '⚔️',
      'Adventure': '🗺️',
      'RPG': '⚔️',
      'Strategy': '🎯',
      'Simulation': '🏗️',
      'Sports': '⚽',
      'Racing': '🏎️',
      'Fighting': '🥊',
      'Shooter': '🔫',
      'Puzzle': '🧩',
      'Platform': '🏃',
      'Horror': '👻',
      'Stealth': '🕵️',
      'Survival': '🏕️',
      'Visual Novel': '📖',
      'Educational': '📚',
      'Music': '🎵',
      'Party': '🎉',
      'Sandbox': '🏖️',
      'Tower Defense': '🏰',
      'Roguelike': '🎲',
      'Metroidvania': '🗺️',
      'Open World': '🌍',
      'Linear': '📏',
      'Turn-based': '⏰',
      'Real-time': '⚡',
      'Tactical': '🎖️',
      'Grand Strategy': '👑',
      '4X': '🌍',
      'MOBA': '⚔️',
      'Battle Royale': '🏆',
      'MMO': '🌐',
      'Co-op': '🤝',
      'Competitive': '🏆',
      'Casual': '😊',
      'Hardcore': '💀',
      'Indie': '🎨',
      'AAA': '💎',
      'Retro': '📺',
      'Modern': '🚀',
      'Classic': '📼'
    }
    
    return iconMap[genreName] || '🎮'
  }

  return (
    <>
      <PageTitle>Generi di Giochi</PageTitle>

      {/* Sezione Filtri */}
      <div className="px-4 py-3 mb-8 bg-white rounded-lg shadow-md dark:bg-gray-800">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-700 dark:text-gray-300">
            Filtri di Ricerca
          </h3>
          <Button
            layout="outline"
            size="small"
            onClick={resetFilters}
          >
            Reset Filtri
          </Button>
        </div>
        
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <div>
            <Input
              className="mt-1"
              placeholder="Cerca per nome..."
              value={nameFilter}
              onChange={(e) => setNameFilter(e.target.value)}
              icon={SearchIcon}
            />
          </div>
          
          <div className="flex items-end">
            <Button
              onClick={fetchGenres}
              disabled={isLoading}
              size="small"
            >
              {isLoading ? 'Caricamento...' : 'Aggiorna'}
            </Button>
          </div>
        </div>
      </div>

      {/* Messaggi di stato */}
      {isLoading && <p className="text-gray-600 dark:text-gray-400">Caricamento generi in corso...</p>}
      {error && <p className="text-red-600 dark:text-red-400">{error}</p>}

      {/* Tabella Generi */}
      <TableContainer className="mb-8">
        <div className="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <p className="text-sm text-blue-700 dark:text-blue-300">
            <strong>💡 Informazioni:</strong> Questa pagina mostra tutti i generi di giochi presenti nel database.
          </p>
        </div>
        <Table>
          <TableHeader>
            <tr>
              <TableCell>Nome Genere</TableCell>
              <TableCell>ID IGDB</TableCell>
              <TableCell>ID Database</TableCell>
            </tr>
          </TableHeader>
          <TableBody>
            {genres.length === 0 ? (
              <TableRow>
                <TableCell colSpan="3" className="text-center py-8">
                  <div className="text-gray-500 dark:text-gray-400">
                    <TagIcon className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                    <p>Nessun genere trovato</p>
                    <p className="text-sm">Prova a modificare i filtri di ricerca</p>
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              genres.map((genre, i) => (
                <TableRow key={i}>
                  <TableCell>
                    <div className="flex items-center text-sm">
                      <div className="w-8 h-8 mr-3 bg-gray-200 dark:bg-gray-700 rounded flex items-center justify-center">
                        <span className="text-lg">{getGenreIcon(genre.genre_name)}</span>
                      </div>
                      <div>
                        <p className="font-semibold">{genre.genre_name || 'Nome non disponibile'}</p>
                        <Badge type={getGenreColor(genre.genre_name)} className="mt-1">
                          {genre.genre_name || 'N/A'}
                        </Badge>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm font-mono text-gray-600 dark:text-gray-400">
                      {genre.igdb_id || 'N/A'}
                    </span>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm font-mono text-gray-500">
                      {genre._id || 'N/A'}
                    </span>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
        {genres.length > 0 && (
          <TableFooter>
            <Pagination
              totalResults={totalResults}
              resultsPerPage={resultsPerPage}
              onChange={onPageChange}
              label="Table navigation"
            />
          </TableFooter>
        )}
      </TableContainer>

      {/* Statistiche */}
      {genres.length > 0 && (
        <div className="grid gap-6 mb-8 md:grid-cols-2">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-blue-100 dark:bg-blue-900">
                <TagIcon className="h-6 w-6 text-blue-600 dark:text-blue-400" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  Totale Generi
                </p>
                <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                  {totalResults}
                </p>
              </div>
            </div>
          </div>
          
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-green-100 dark:bg-green-900">
                <GamepadIcon className="h-6 w-6 text-green-600 dark:text-green-400" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  Con Nome
                </p>
                <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                  {genres.filter(genre => genre.genre_name && genre.genre_name.trim()).length}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Griglia Generi Popolari */}
      {genres.length > 0 && (
        <div className="mb-8">
          <h3 className="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-4">
            Generi Popolari
          </h3>
          <div className="grid gap-4 md:grid-cols-4 lg:grid-cols-6">
            {genres.slice(0, 12).map((genre, i) => (
              <div key={i} className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4 hover:shadow-lg transition-shadow">
                <div className="text-center">
                  <div className="text-3xl mb-2">{getGenreIcon(genre.genre_name)}</div>
                  <h4 className="font-semibold text-sm text-gray-900 dark:text-white mb-1">
                    {genre.genre_name || 'Nome non disponibile'}
                  </h4>
                  <Badge type={getGenreColor(genre.genre_name)} className="text-xs">
                    {genre.genre_name || 'N/A'}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  )
}

export default Genres 