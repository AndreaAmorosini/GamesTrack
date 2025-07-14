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
import { HeartIcon } from '../icons'
import { searchIGDBGames } from '../services/api'

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
  
  const resultsPerPage = 10

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
                      src={game.cover?.thumb_url || 'placeholder-image-url.jpg'}
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
                  <div className="flex items-center space-x-4">
                    <Button 
                      layout="link" 
                      size="icon" 
                      aria-label="Add to Wishlist"
                      disabled={true}
                      className="text-gray-400 cursor-not-allowed"
                      title="Funzionalità wishlist temporaneamente disabilitata"
                    >
                      <HeartIcon className="w-5 h-5" aria-hidden="true" />
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