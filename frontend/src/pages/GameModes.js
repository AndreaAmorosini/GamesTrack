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
import { SearchIcon, UsersIcon, GamepadIcon } from '../icons'
import { getGameModes } from '../services/api'

function GameModes() {
  // Stati per i dati
  const [gameModes, setGameModes] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  
  // Stati per i filtri
  const [nameFilter, setNameFilter] = useState('')
  
  // Stati per la paginazione
  const [page, setPage] = useState(1)
  const [totalResults, setTotalResults] = useState(0)
  const resultsPerPage = 20

  // Carica le modalità di gioco
  const fetchGameModes = async () => {
    setIsLoading(true)
    setError('')
    try {
      const params = {
        page,
        limit: resultsPerPage
      }
      if (nameFilter) params.name = nameFilter
      
      const response = await getGameModes(params)
      setGameModes(response.game_modes || response || [])
      setTotalResults(response.pagination?.total_count || response?.length || 0)
    } catch (err) {
      setError('Errore durante il caricamento delle modalità di gioco: ' + (err.message || 'Errore sconosciuto'))
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }

  // Carica le modalità quando cambiano i filtri o la pagina
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      fetchGameModes()
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

  // Funzione per ottenere il colore del badge basato sul nome della modalità
  const getModeColor = (modeName) => {
    if (!modeName) return 'default'
    
    const colorMap = {
      'Single-player': 'success',
      'Multiplayer': 'warning',
      'Co-op': 'info',
      'Competitive': 'danger',
      'Local Multiplayer': 'warning',
      'Online Multiplayer': 'danger',
      'Split-screen': 'info',
      'LAN': 'warning',
      'MMO': 'danger',
      'Battle Royale': 'danger',
      'MOBA': 'danger',
      'Racing': 'warning',
      'Fighting': 'danger',
      'Sports': 'success',
      'Puzzle': 'info',
      'Strategy': 'warning',
      'RPG': 'success',
      'Adventure': 'info',
      'Action': 'danger',
      'Simulation': 'success',
      'Sandbox': 'info',
      'Open World': 'success',
      'Linear': 'warning',
      'Story-driven': 'info',
      'Arcade': 'warning',
      'Casual': 'info',
      'Hardcore': 'danger',
      'Indie': 'warning',
      'AAA': 'success',
      'Retro': 'info',
      'Modern': 'success',
      'Classic': 'warning'
    }
    
    return colorMap[modeName] || 'default'
  }

  // Funzione per ottenere l'icona della modalità
  const getModeIcon = (modeName) => {
    if (!modeName) return '🎮'
    
    const iconMap = {
      'Single-player': '👤',
      'Multiplayer': '👥',
      'Co-op': '🤝',
      'Competitive': '🏆',
      'Local Multiplayer': '👥',
      'Online Multiplayer': '🌐',
      'Split-screen': '📺',
      'LAN': '🔗',
      'MMO': '🌐',
      'Battle Royale': '🏆',
      'MOBA': '⚔️',
      'Racing': '🏎️',
      'Fighting': '🥊',
      'Sports': '⚽',
      'Puzzle': '🧩',
      'Strategy': '🎯',
      'RPG': '⚔️',
      'Adventure': '🗺️',
      'Action': '⚔️',
      'Simulation': '🏗️',
      'Sandbox': '🏖️',
      'Open World': '🌍',
      'Linear': '📏',
      'Story-driven': '📖',
      'Arcade': '🎮',
      'Casual': '😊',
      'Hardcore': '💀',
      'Indie': '🎨',
      'AAA': '💎',
      'Retro': '📺',
      'Modern': '🚀',
      'Classic': '📼'
    }
    
    return iconMap[modeName] || '🎮'
  }

  // Funzione per ottenere la descrizione della modalità
  const getModeDescription = (modeName) => {
    if (!modeName) return 'Modalità di gioco'
    
    const descriptionMap = {
      'Single-player': 'Gioco per un solo giocatore',
      'Multiplayer': 'Gioco per più giocatori',
      'Co-op': 'Gioco cooperativo',
      'Competitive': 'Gioco competitivo',
      'Local Multiplayer': 'Multiplayer locale',
      'Online Multiplayer': 'Multiplayer online',
      'Split-screen': 'Schermo diviso',
      'LAN': 'Rete locale',
      'MMO': 'Massively Multiplayer Online',
      'Battle Royale': 'Modalità battle royale',
      'MOBA': 'Multiplayer Online Battle Arena',
      'Racing': 'Gara di velocità',
      'Fighting': 'Combattimento',
      'Sports': 'Sport',
      'Puzzle': 'Puzzle',
      'Strategy': 'Strategia',
      'RPG': 'Role Playing Game',
      'Adventure': 'Avventura',
      'Action': 'Azione',
      'Simulation': 'Simulazione',
      'Sandbox': 'Sandbox creativo',
      'Open World': 'Mondo aperto',
      'Linear': 'Progressione lineare',
      'Story-driven': 'Guidato dalla storia',
      'Arcade': 'Stile arcade',
      'Casual': 'Gioco casual',
      'Hardcore': 'Gioco hardcore',
      'Indie': 'Gioco indie',
      'AAA': 'Gioco AAA',
      'Retro': 'Stile retrò',
      'Modern': 'Stile moderno',
      'Classic': 'Gioco classico'
    }
    
    return descriptionMap[modeName] || 'Modalità di gioco'
  }

  return (
    <>
      <PageTitle>Modalità di Gioco</PageTitle>

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
              onClick={fetchGameModes}
              disabled={isLoading}
              size="small"
            >
              {isLoading ? 'Caricamento...' : 'Aggiorna'}
            </Button>
          </div>
        </div>
      </div>

      {/* Messaggi di stato */}
      {isLoading && <p className="text-gray-600 dark:text-gray-400">Caricamento modalità in corso...</p>}
      {error && <p className="text-red-600 dark:text-red-400">{error}</p>}

      {/* Tabella Modalità */}
      <TableContainer className="mb-8">
        <div className="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <p className="text-sm text-blue-700 dark:text-blue-300">
            <strong>💡 Informazioni:</strong> Questa pagina mostra tutte le modalità di gioco presenti nel database.
          </p>
        </div>
        <Table>
          <TableHeader>
            <tr>
              <TableCell>Nome Modalità</TableCell>
              <TableCell>ID IGDB</TableCell>
              <TableCell>ID Database</TableCell>
            </tr>
          </TableHeader>
          <TableBody>
            {gameModes.length === 0 ? (
              <TableRow>
                <TableCell colSpan="3" className="text-center py-8">
                  <div className="text-gray-500 dark:text-gray-400">
                    <UsersIcon className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                    <p>Nessuna modalità trovata</p>
                    <p className="text-sm">Prova a modificare i filtri di ricerca</p>
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              gameModes.map((mode, i) => (
                <TableRow key={i}>
                  <TableCell>
                    <div className="flex items-center text-sm">
                      <div className="w-8 h-8 mr-3 bg-gray-200 dark:bg-gray-700 rounded flex items-center justify-center">
                        <span className="text-lg">{getModeIcon(mode.game_mode_name)}</span>
                      </div>
                      <div>
                        <p className="font-semibold">{mode.game_mode_name || 'Nome non disponibile'}</p>
                        <Badge type={getModeColor(mode.game_mode_name)} className="mt-1">
                          {mode.game_mode_name || 'N/A'}
                        </Badge>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm font-mono text-gray-600 dark:text-gray-400">
                      {mode.igdb_id || 'N/A'}
                    </span>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm font-mono text-gray-500">
                      {mode._id || 'N/A'}
                    </span>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
        {gameModes.length > 0 && (
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
      {gameModes.length > 0 && (
        <div className="grid gap-6 mb-8 md:grid-cols-2">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-blue-100 dark:bg-blue-900">
                <UsersIcon className="h-6 w-6 text-blue-600 dark:text-blue-400" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  Totale Modalità
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
                  {gameModes.filter(mode => mode.game_mode_name && mode.game_mode_name.trim()).length}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Griglia Modalità Popolari */}
      {gameModes.length > 0 && (
        <div className="mb-8">
          <h3 className="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-4">
            Modalità Popolari
          </h3>
          <div className="grid gap-4 md:grid-cols-4 lg:grid-cols-6">
            {gameModes.slice(0, 12).map((mode, i) => (
              <div key={i} className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4 hover:shadow-lg transition-shadow">
                <div className="text-center">
                  <div className="text-3xl mb-2">{getModeIcon(mode.game_mode_name)}</div>
                  <h4 className="font-semibold text-sm text-gray-900 dark:text-white mb-1">
                    {mode.game_mode_name || 'Nome non disponibile'}
                  </h4>
                  <Badge type={getModeColor(mode.game_mode_name)} className="text-xs">
                    {mode.game_mode_name || 'N/A'}
                  </Badge>
                  <p className="text-xs text-gray-500 mt-2">
                    {getModeDescription(mode.game_mode_name)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Categorie Modalità */}
      {gameModes.length > 0 && (
        <div className="mb-8">
          <h3 className="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-4">
            Categorie Modalità
          </h3>
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {/* Single Player */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
              <div className="flex items-center mb-4">
                <div className="p-2 rounded-full bg-green-100 dark:bg-green-900 mr-3">
                  <span className="text-xl">👤</span>
                </div>
                <h4 className="font-semibold text-gray-900 dark:text-white">Single Player</h4>
              </div>
              <div className="space-y-2">
                {gameModes.filter(mode => 
                  mode.game_mode_name && (
                    mode.game_mode_name.toLowerCase().includes('single') || 
                    mode.game_mode_name.toLowerCase().includes('solo')
                  )
                ).slice(0, 5).map((mode, i) => (
                  <Badge key={i} type="success" className="mr-2 mb-2">
                    {mode.game_mode_name}
                  </Badge>
                ))}
              </div>
            </div>

            {/* Multiplayer */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
              <div className="flex items-center mb-4">
                <div className="p-2 rounded-full bg-yellow-100 dark:bg-yellow-900 mr-3">
                  <span className="text-xl">👥</span>
                </div>
                <h4 className="font-semibold text-gray-900 dark:text-white">Multiplayer</h4>
              </div>
              <div className="space-y-2">
                {gameModes.filter(mode => 
                  mode.game_mode_name && (
                    mode.game_mode_name.toLowerCase().includes('multiplayer') || 
                    mode.game_mode_name.toLowerCase().includes('co-op')
                  )
                ).slice(0, 5).map((mode, i) => (
                  <Badge key={i} type="warning" className="mr-2 mb-2">
                    {mode.game_mode_name}
                  </Badge>
                ))}
              </div>
            </div>

            {/* Competitive */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
              <div className="flex items-center mb-4">
                <div className="p-2 rounded-full bg-red-100 dark:bg-red-900 mr-3">
                  <span className="text-xl">🏆</span>
                </div>
                <h4 className="font-semibold text-gray-900 dark:text-white">Competitive</h4>
              </div>
              <div className="space-y-2">
                {gameModes.filter(mode => 
                  mode.game_mode_name && (
                    mode.game_mode_name.toLowerCase().includes('competitive') || 
                    mode.game_mode_name.toLowerCase().includes('battle') ||
                    mode.game_mode_name.toLowerCase().includes('moba')
                  )
                ).slice(0, 5).map((mode, i) => (
                  <Badge key={i} type="danger" className="mr-2 mb-2">
                    {mode.game_mode_name}
                  </Badge>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

export default GameModes 