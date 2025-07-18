import React, { useState, useEffect } from 'react'
import PageTitle from '../components/Typography/PageTitle'
import SectionTitle from '../components/Typography/SectionTitle'
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
  Select,
} from '@windmill/react-ui'
import { TrashIcon, EditIcon } from '../icons'
import InfoCard from '../components/Cards/InfoCard'
import RoundIcon from '../components/RoundIcon'
import { GamesIcon, TrophyIcon, PlayIcon, StarIcon } from '../icons'

function MyLibrary() {
  // Stati per i giochi
  const [games, setGames] = useState([])
  const [page, setPage] = useState(1)
  const [totalResults, setTotalResults] = useState(0)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  
  // Stati per i filtri
  const [selectedPlatform, setSelectedPlatform] = useState('')
  const [sortBy, setSortBy] = useState('name')
  const [sortOrder, setSortOrder] = useState('asc')
  
  // Statistiche
  const [stats, setStats] = useState({
    totalGames: 0,
    totalTrophies: 0,
    totalPlayTime: 0,
    completedGames: 0
  })

  const resultsPerPage = 10

  // Carica i giochi quando cambiano i filtri
  useEffect(() => {
    const fetchGames = async () => {
      setIsLoading(true)
      setError('')
      try {
        const response = await fetch(`/api/games?page=${page}&limit=${resultsPerPage}&sort_by=${sortBy}&sort_order=${sortOrder}${selectedPlatform ? `&platforms=${selectedPlatform}` : ''}`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        })
        
        if (!response.ok) throw new Error('Errore nel caricamento dei giochi')
        
        const data = await response.json()
        // Assicurati che games sia sempre un array
        setGames(Array.isArray(data.games) ? data.games : [])
        setTotalResults(data.pagination?.total_count || 0)
        
        // Aggiorna le statistiche
        try {
          const platformStats = await fetch('/api/platforms-users', {
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
          }).then(res => res.json())
          
          // Accedi all'array platforms dalla risposta con controllo di sicurezza
          const platforms = Array.isArray(platformStats.platforms) ? platformStats.platforms : []
          
          setStats({
            totalGames: platforms.reduce((acc, p) => acc + (p.game_count || 0), 0),
            totalTrophies: platforms.reduce((acc, p) => acc + (p.earned_achievements || 0), 0),
            totalPlayTime: platforms.reduce((acc, p) => acc + (p.play_count || 0), 0),
            completedGames: platforms.reduce((acc, p) => acc + (p.full_trophies_count || 0), 0)
          })
        } catch (statsError) {
          console.error('Errore nel caricamento delle statistiche:', statsError)
          // Mantieni le statistiche di default in caso di errore
        }
      } catch (err) {
        setError('Errore durante il caricamento dei giochi: ' + err.message)
        console.error(err)
      } finally {
        setIsLoading(false)
      }
    }

    fetchGames()
  }, [page, selectedPlatform, sortBy, sortOrder])

  // Gestione cambio pagina
  const onPageChange = (p) => {
    setPage(p)
  }

  // Sincronizza con una piattaforma
  const syncPlatform = async (platform) => {
    try {
      const response = await fetch(`/api/sync/${platform}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })
      
      if (!response.ok) throw new Error(`Errore nella sincronizzazione con ${platform}`)
      
      const data = await response.json()
      // Mostra un messaggio di successo
      alert(`Sincronizzazione con ${platform} avviata! Job ID: ${data.job_id}`)
    } catch (err) {
      setError(`Errore durante la sincronizzazione con ${platform}: ${err.message}`)
    }
  }

  return (
    <>
      <PageTitle>La Mia Libreria</PageTitle>

      {/* Cards statistiche */}
      <div className="grid gap-6 mb-8 md:grid-cols-2 xl:grid-cols-4">
        <InfoCard title="Giochi Totali" value={stats.totalGames}>
          <RoundIcon
            icon={GamesIcon}
            iconColorClass="text-orange-500 dark:text-orange-100"
            bgColorClass="bg-orange-100 dark:bg-orange-500"
            className="mr-4"
          />
        </InfoCard>

        <InfoCard title="Trofei/Achievement" value={stats.totalTrophies}>
          <RoundIcon
            icon={TrophyIcon}
            iconColorClass="text-green-500 dark:text-green-100"
            bgColorClass="bg-green-100 dark:bg-green-500"
            className="mr-4"
          />
        </InfoCard>

        <InfoCard title="Ore Giocate" value={stats.totalPlayTime}>
          <RoundIcon
            icon={PlayIcon}
            iconColorClass="text-blue-500 dark:text-blue-100"
            bgColorClass="bg-blue-100 dark:bg-blue-500"
            className="mr-4"
          />
        </InfoCard>

        <InfoCard title="Giochi Completati" value={stats.completedGames}>
          <RoundIcon
            icon={StarIcon}
            iconColorClass="text-purple-500 dark:text-purple-100"
            bgColorClass="bg-purple-100 dark:bg-purple-500"
            className="mr-4"
          />
        </InfoCard>
      </div>

      {/* Controlli */}
      <div className="flex flex-col md:flex-row justify-between mb-8">
        <div className="flex flex-col md:flex-row md:w-2/3 gap-4">
          <Select
            className="mt-1"
            onChange={(e) => setSelectedPlatform(e.target.value)}
            value={selectedPlatform}
          >
            <option value="">Tutte le piattaforme</option>
            <option value="6">PC (Steam)</option>
            <option value="48">PlayStation 4</option>
            <option value="167">PlayStation 5</option>
          </Select>

          <Select
            className="mt-1"
            onChange={(e) => setSortBy(e.target.value)}
            value={sortBy}
          >
            <option value="name">Nome</option>
            <option value="release_date">Data di uscita</option>
            <option value="total_rating">Valutazione</option>
          </Select>

          <Select
            className="mt-1"
            onChange={(e) => setSortOrder(e.target.value)}
            value={sortOrder}
          >
            <option value="asc">Crescente</option>
            <option value="desc">Decrescente</option>
          </Select>
        </div>

        <div className="flex gap-4 mt-4 md:mt-0">
          <Button onClick={() => syncPlatform('steam')}>
            Sincronizza Steam
          </Button>
          <Button onClick={() => syncPlatform('psn')}>
            Sincronizza PSN
          </Button>
        </div>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4" role="alert">
          <span className="block sm:inline">{error}</span>
        </div>
      )}

      {/* Tabella giochi */}
      <TableContainer className="mb-8">
        <Table>
          <TableHeader>
            <tr>
              <TableCell>Gioco</TableCell>
              <TableCell>Piattaforma</TableCell>
              <TableCell>Trofei/Achievement</TableCell>
              <TableCell>Ore Giocate</TableCell>
              <TableCell>Stato</TableCell>
              <TableCell>Azioni</TableCell>
            </tr>
          </TableHeader>
          <TableBody>
            {games.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8">
                  <div className="text-gray-500 dark:text-gray-400">
                    {isLoading ? (
                      <p>Caricamento giochi...</p>
                    ) : (
                      <div>
                        <p className="mb-2">Nessun gioco trovato nella tua libreria</p>
                        <p className="text-sm">Prova a sincronizzare con Steam o PSN per aggiungere i tuoi giochi</p>
                      </div>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              games.map((game, i) => (
                <TableRow key={i}>
                  <TableCell>
                    <div className="flex items-center text-sm">
                      {game.cover_image && (
                        <img
                          className="hidden w-12 h-12 rounded mr-3 md:block"
                          src={game.cover_image}
                          alt={game.name}
                        />
                      )}
                      <div>
                        <p className="font-semibold">{game.name}</p>
                        <p className="text-xs text-gray-600 dark:text-gray-400">
                          {game.developer_names?.[0]}
                        </p>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm">
                      {game.platform_names?.join(', ')}
                    </span>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm">
                      {game.num_trophies || 0}
                    </span>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm">
                      {game.play_count || 0}h
                    </span>
                  </TableCell>
                  <TableCell>
                    <Badge type={game.full_trophies_count ? 'success' : 'warning'}>
                      {game.full_trophies_count ? 'Completato' : 'In corso'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center space-x-4">
                      <Button layout="link" size="icon" aria-label="Edit">
                        <EditIcon className="w-5 h-5" aria-hidden="true" />
                      </Button>
                      <Button layout="link" size="icon" aria-label="Delete">
                        <TrashIcon className="w-5 h-5" aria-hidden="true" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
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

export default MyLibrary 