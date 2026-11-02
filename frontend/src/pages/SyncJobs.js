import React, { useState, useEffect, useRef } from 'react'
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
  Select,
  Card,
  CardBody,
  Modal,
  ModalHeader,
  ModalBody,
  ModalFooter,
} from '@windmill/react-ui'
import { SyncIcon, CheckIcon, XIcon, ClockIcon } from '../icons'
import { TableSkeleton } from '../components/Skeletons'
import { getSyncJobs, getSyncLogs } from '../services/api'
import { useSync } from '../context/SyncContext'

function SyncJobs() {
  // Stato globale delle sync (condiviso con le altre pagine)
  const { activeSync, isSyncing, startingPlatform, startSync } = useSync()

  // Stati per i job
  const [jobs, setJobs] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  
  // Stati per i filtri
  const [statusFilter, setStatusFilter] = useState('')
  const [platformFilter, setPlatformFilter] = useState('')
  
  // Stati per la paginazione
  const [page, setPage] = useState(1)
  const [totalResults, setTotalResults] = useState(0)

  // Stati per il visualizzatore di log
  const [logsModalJob, setLogsModalJob] = useState(null) // job_string_id
  const [logsContent, setLogsContent] = useState([])
  const [logsLoading, setLogsLoading] = useState(false)
  const resultsPerPage = 20

  // Carica i job di sincronizzazione
  const fetchJobs = async () => {
    setIsLoading(true)
    setError('')
    try {
      const params = {
        page: page,
        limit: resultsPerPage
      }
      if (statusFilter) params.status = statusFilter
      if (platformFilter) params.platform = platformFilter
      
      const response = await getSyncJobs(params)
      setJobs(response.jobs || [])
      setTotalResults(response.total_count || 0)
    } catch (err) {
      setError('Errore durante il caricamento dei job: ' + (err.message || 'Errore sconosciuto'))
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }

  // Carica i job quando cambiano i filtri o la pagina
  useEffect(() => {
    fetchJobs()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, platformFilter, page])

  // Gestione cambio pagina
  const onPageChange = (p) => {
    setPage(p)
  }

  // Ricarica i job quando una sync (gestita dal SyncContext) si conclude
  const prevSyncRef = useRef(null)
  useEffect(() => {
    if (prevSyncRef.current && !activeSync) {
      fetchJobs()
    }
    prevSyncRef.current = activeSync
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeSync])

  // --- Visualizzazione dei log di un job ---
  const openLogs = async (jobStringId) => {
    setLogsModalJob(jobStringId)
    setLogsContent([])
    setLogsLoading(true)
    try {
      const data = await getSyncLogs(jobStringId)
      setLogsContent(data.logs || [])
    } catch (err) {
      setLogsContent([{ level: 'ERROR', message: err.message || 'Errore nel caricamento dei log' }])
    } finally {
      setLogsLoading(false)
    }
  }

  // Aggiorna i log in tempo reale mentre il modal è aperto e il job è in corso
  useEffect(() => {
    if (!logsModalJob) return undefined
    const timer = setInterval(async () => {
      try {
        const data = await getSyncLogs(logsModalJob)
        setLogsContent(data.logs || [])
      } catch (err) {
        // silenzioso: il modal resta sui dati correnti
      }
    }, 3000)
    return () => clearInterval(timer)
  }, [logsModalJob])

  // Reset filtri
  const resetFilters = () => {
    setStatusFilter('')
    setPlatformFilter('')
    setPage(1)
  }

  // Funzione per ottenere il badge del status
  const getStatusBadge = (status) => {
    switch (status?.toLowerCase()) {
      case 'success':
        return <Badge type="success">Completato</Badge>
      case 'fail':
        return <Badge type="danger">Fallito</Badge>
      case 'in_progress':
        return <Badge type="warning">In Corso</Badge>
      case 'queued':
        return <Badge type="info">In Attesa</Badge>
      default:
        return <Badge type="default">{status || 'Sconosciuto'}</Badge>
    }
  }

  // Funzione per ottenere l'icona del status
  const getStatusIcon = (status) => {
    switch (status?.toLowerCase()) {
      case 'success':
        return <CheckIcon className="w-4 h-4 text-green-500" />
      case 'fail':
        return <XIcon className="w-4 h-4 text-red-500" />
      case 'in_progress':
        return <SyncIcon className="w-4 h-4 text-yellow-500" />
      case 'queued':
        return <ClockIcon className="w-4 h-4 text-blue-500" />
      default:
        return <ClockIcon className="w-4 h-4 text-gray-500" />
    }
  }

  // Funzione per formattare la data
  const formatDate = (dateString) => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleString('it-IT')
  }

  // Funzione per formattare la durata
  const formatDuration = (seconds) => {
    if (!seconds) return 'N/A'
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = seconds % 60
    
    if (hours > 0) {
      return `${hours}h ${minutes}m ${secs}s`
    } else if (minutes > 0) {
      return `${minutes}m ${secs}s`
    } else {
      return `${secs}s`
    }
  }

  // Funzione per ottenere il nome leggibile di una piattaforma
  const getPlatformName = (platform) => {
    switch (platform?.toLowerCase()) {
      case 'steam': return 'Steam'
      case 'psn': return 'PSN'
      case 'retroachievements': return 'RetroAchievements'
      case 'gog': return 'GOG'
      default: return platform
    }
  }

  // Funzione per ottenere il badge della piattaforma
  const getPlatformBadge = (platform) => {
    switch (platform?.toLowerCase()) {
      case 'steam':
        return <Badge type="success">Steam</Badge>
      case 'psn':
        return <Badge type="warning">PlayStation Network</Badge>
      case 'retroachievements':
        return <Badge type="danger">RetroAchievements</Badge>
      case 'gog':
        return <Badge type="neutral">GOG</Badge>
      case 'price_track':
        return <Badge type="info">Tracking Prezzi</Badge>
      default:
        return <Badge type="default">{platform || 'N/A'}</Badge>
    }
  }

  return (
    <>
      <PageTitle>Storico Sincronizzazioni</PageTitle>

      {/* Avvio pipeline di sincronizzazione */}
      <Card className="mb-8">
        <CardBody>
          <h3 className="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-4">
            Avvia sincronizzazione
          </h3>
          <div className="flex flex-wrap gap-3">
            {['steam', 'psn', 'retroachievements', 'gog'].map((platform) => (
              <Button
                key={platform}
                onClick={() => startSync(platform)}
                disabled={isSyncing}
                className={isSyncing ? 'opacity-50 cursor-not-allowed' : ''}
              >
                {startingPlatform === platform ? 'Avvio...' : `Sincronizza ${getPlatformName(platform)}`}
              </Button>
            ))}
          </div>
          {activeSync && (
            <div className="mt-4 flex items-center text-sm text-yellow-600 dark:text-yellow-400">
              <SyncIcon className="w-4 h-4 mr-2 animate-spin" />
              Job {activeSync.jobId.slice(0, 8)}... in corso — stato: {activeSync.status}
            </div>
          )}
          <p className="mt-3 text-xs text-gray-500 dark:text-gray-400">
            Le credenziali delle piattaforme si configurano nella pagina <strong>Servizi</strong>.
          </p>
        </CardBody>
      </Card>

      {/* Sezione Filtri */}
      <div className="px-4 py-3 mb-8 bg-white rounded-lg shadow-md dark:bg-gray-800">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-700 dark:text-gray-300">
            Filtri
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
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Status
            </label>
            <Select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="">Tutti gli status</option>
              <option value="success">Completato</option>
              <option value="fail">Fallito</option>
              <option value="in_progress">In Corso</option>
              <option value="queued">In Attesa</option>
            </Select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Piattaforma
            </label>
            <Select
              value={platformFilter}
              onChange={(e) => setPlatformFilter(e.target.value)}
            >
              <option value="">Tutte le piattaforme</option>
              <option value="steam">Steam</option>
              <option value="psn">PlayStation Network</option>
              <option value="retroachievements">RetroAchievements</option>
              <option value="gog">GOG</option>
              <option value="price_track">Tracking Prezzi</option>
            </Select>
          </div>
          
          <div className="flex items-end">
            <Button
              onClick={fetchJobs}
              disabled={isLoading}
              size="small"
            >
              {isLoading ? 'Caricamento...' : 'Aggiorna'}
            </Button>
          </div>
        </div>
      </div>

      {/* Messaggi di stato */}
      {error && <p className="text-red-600 dark:text-red-400">{error}</p>}

      {/* Tabella Job */}
      <TableContainer className="mb-8">
        <div className="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <p className="text-sm text-blue-700 dark:text-blue-300">
            <strong>Informazioni:</strong> Questa pagina mostra lo storico di tutte le sincronizzazioni effettuate con le tue piattaforme di gioco.
          </p>
        </div>
        <Table>
          <TableHeader>
            <tr>
              <TableCell>Job ID</TableCell>
              <TableCell>Piattaforma</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Creato</TableCell>
              <TableCell>Completato</TableCell>
              <TableCell>Durata</TableCell>
              <TableCell>Dettagli</TableCell>
            </tr>
          </TableHeader>
          <TableBody>
            {jobs.length === 0 ? (
              <TableRow>
                <TableCell colSpan="7" className="text-center py-8">
                  <div className="text-gray-500 dark:text-gray-400">
                    {isLoading ? (
                      <div className="text-left">
                        <TableSkeleton rows={5} cols={6} />
                      </div>
                    ) : (
                      <div>
                        <SyncIcon className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                        <p>Nessun job di sincronizzazione trovato</p>
                        <p className="text-sm">Avvia la tua prima sincronizzazione con i pulsanti qui sopra</p>
                      </div>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              jobs.map((job, i) => (
                <TableRow key={i}>
                  <TableCell>
                    <div className="flex items-center">
                      {getStatusIcon(job.status)}
                      <span className="ml-2 font-mono text-sm">
                        {job.job_id || job._id}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell>
                    {getPlatformBadge(job.platform)}
                  </TableCell>
                  <TableCell>
                    {getStatusBadge(job.status)}
                  </TableCell>
                  <TableCell>
                    <span className="text-sm">
                      {formatDate(job.created_at)}
                    </span>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm">
                      {job.completed_at ? formatDate(job.completed_at) : 'N/A'}
                    </span>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm">
                      {formatDuration(job.duration)}
                    </span>
                  </TableCell>
                  <TableCell>
                    <div className="text-sm">
                      {job.result && (
                        <div>
                          <p><strong>Giochi sincronizzati:</strong> {job.result.games_synced || job.game_inserted || 0}</p>
                          <p><strong>Achievement/Trofei:</strong> {job.result.achievements_synced || 0}</p>
                          {job.error && (
                            <p className="text-red-600"><strong>Errore:</strong> {job.error}</p>
                          )}
                        </div>
                      )}
                      {job.job_string_id && (
                        <Button size="small" layout="outline" onClick={() => openLogs(job.job_string_id)}>
                          Visualizza log
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
        {jobs.length > 0 && (
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
      {jobs.length > 0 && (
        <div className="grid gap-6 mb-8 md:grid-cols-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-blue-100 dark:bg-blue-900">
                <SyncIcon className="h-6 w-6 text-blue-600 dark:text-blue-400" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  Totale Job
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
                <CheckIcon className="h-6 w-6 text-green-600 dark:text-green-400" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  Completati
                </p>
                <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                  {jobs.filter(job => job.status === 'success').length}
                </p>
              </div>
            </div>
          </div>
          
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-red-100 dark:bg-red-900">
                <XIcon className="h-6 w-6 text-red-600 dark:text-red-400" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  Falliti
                </p>
                <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                  {jobs.filter(job => job.status === 'fail').length}
                </p>
              </div>
            </div>
          </div>
          
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-yellow-100 dark:bg-yellow-900">
                <ClockIcon className="h-6 w-6 text-yellow-600 dark:text-yellow-400" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  In Corso
                </p>
                <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                  {jobs.filter(job => job.status === 'in_progress').length}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal log job */}
      <Modal isOpen={!!logsModalJob} onClose={() => setLogsModalJob(null)}>
        <ModalHeader className="text-center">
          Log job: {logsModalJob}
        </ModalHeader>
        <ModalBody>
          {logsLoading ? (
            <p className="text-sm text-gray-500">Caricamento log...</p>
          ) : (
            <div className="max-h-96 overflow-y-auto bg-gray-900 text-gray-100 rounded-lg p-3 font-mono text-xs">
              {logsContent.length === 0 ? (
                <p className="text-gray-400">Nessun log disponibile per questo job</p>
              ) : (
                logsContent.map((entry, i) => (
                  <div key={i} className="mb-1">
                    <span className="text-gray-500">{entry.timestamp ? new Date(entry.timestamp).toLocaleTimeString('it-IT') : ''}</span>
                    {' '}
                    <span className={entry.level === 'ERROR' ? 'text-red-400' : entry.level === 'WARNING' ? 'text-yellow-400' : 'text-gray-300'}>
                      [{entry.level}]
                    </span>
                    {' '}
                    <span>{entry.message}</span>
                  </div>
                ))
              )}
            </div>
          )}
          <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
            I log si aggiornano automaticamente ogni 3 secondi mentre il modal è aperto.
          </p>
        </ModalBody>
        <ModalFooter>
          <div className="hidden sm:block">
            <Button layout="outline" onClick={() => setLogsModalJob(null)}>Chiudi</Button>
          </div>
        </ModalFooter>
      </Modal>
    </>
  )
}

export default SyncJobs