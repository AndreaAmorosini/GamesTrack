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
import { SearchIcon, BuildingIcon, GlobeIcon } from '../icons'
import { getCompanies } from '../services/api'

function Companies() {
  // Stati per i dati
  const [companies, setCompanies] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  
  // Stati per i filtri
  const [nameFilter, setNameFilter] = useState('')
  const [countryFilter, setCountryFilter] = useState('')
  
  // Stati per la paginazione
  const [page, setPage] = useState(1)
  const [totalResults, setTotalResults] = useState(0)
  const resultsPerPage = 10

  // Carica le aziende
  const fetchCompanies = async () => {
    setIsLoading(true)
    setError('')
    try {
      const params = {
        page,
        limit: resultsPerPage
      }
      if (nameFilter && nameFilter.trim()) params.name = nameFilter
      if (countryFilter && countryFilter.trim()) params.country = countryFilter
      
      const response = await getCompanies(params)
      setCompanies(response.companies || response || [])
      setTotalResults(response.pagination?.total_count || response?.length || 0)
    } catch (err) {
      setError('Errore durante il caricamento delle aziende: ' + (err.message || 'Errore sconosciuto'))
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }

  // Carica le aziende quando cambiano i filtri o la pagina
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      fetchCompanies()
    }, 500) // Debounce della ricerca

    return () => clearTimeout(timeoutId)
  }, [nameFilter, countryFilter, page])

  // Gestione cambio pagina
  const onPageChange = (p) => {
    setPage(p)
    // Scroll to top quando cambia pagina
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  // Reset filtri
  const resetFilters = () => {
    setNameFilter('')
    setCountryFilter('')
    setPage(1)
  }

  // Funzione per ottenere il badge del paese
  const getCountryBadge = (country) => {
    if (!country) return <Badge type="default">N/A</Badge>
    
    const countryMap = {
      'USA': { type: 'success', name: 'Stati Uniti' },
      'Japan': { type: 'warning', name: 'Giappone' },
      'UK': { type: 'info', name: 'Regno Unito' },
      'Germany': { type: 'danger', name: 'Germania' },
      'France': { type: 'success', name: 'Francia' },
      'Canada': { type: 'info', name: 'Canada' },
      'South Korea': { type: 'warning', name: 'Corea del Sud' },
      'Sweden': { type: 'success', name: 'Svezia' },
      'Poland': { type: 'danger', name: 'Polonia' },
      'Italy': { type: 'success', name: 'Italia' },
      'Spain': { type: 'warning', name: 'Spagna' },
      'Netherlands': { type: 'info', name: 'Paesi Bassi' },
      'Australia': { type: 'success', name: 'Australia' },
      'China': { type: 'danger', name: 'Cina' },
      'Russia': { type: 'warning', name: 'Russia' },
      'Brazil': { type: 'success', name: 'Brasile' },
      'India': { type: 'info', name: 'India' },
      'Mexico': { type: 'warning', name: 'Messico' },
      'Argentina': { type: 'success', name: 'Argentina' },
      'Chile': { type: 'info', name: 'Cile' }
    }
    
    const countryInfo = countryMap[country] || { type: 'default', name: country }
    return <Badge type={countryInfo.type}>{countryInfo.name}</Badge>
  }

  // Funzione per formattare la data
  const formatDate = (dateString) => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleDateString('it-IT')
  }

  // Ottieni lista unica dei paesi
  const uniqueCountries = [...new Set(companies.map(company => company.country).filter(country => country && country.trim()))].sort()

  return (
    <>
      <PageTitle>Aziende</PageTitle>

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
          
          <div>
            <Select
              className="mt-1"
              value={countryFilter}
              onChange={(e) => setCountryFilter(e.target.value)}
            >
              <option value="">Tutti i paesi</option>
              {uniqueCountries.map((country) => (
                <option key={country} value={country}>
                  {country}
                </option>
              ))}
            </Select>
          </div>
          
          <div className="flex items-end">
            <Button
              onClick={fetchCompanies}
              disabled={isLoading}
              size="small"
            >
              {isLoading ? 'Caricamento...' : 'Aggiorna'}
            </Button>
          </div>
        </div>
      </div>

      {/* Messaggi di stato */}
      {isLoading && (
        <div className="mb-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <div className="flex items-center">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500 mr-2"></div>
            <p className="text-blue-700 dark:text-blue-300">Caricamento aziende in corso...</p>
          </div>
        </div>
      )}
      {error && (
        <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
          <p className="text-red-700 dark:text-red-300">{error}</p>
        </div>
      )}

      {/* Tabella Aziende */}
      <TableContainer className="mb-8">
        <div className="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <div className="flex items-center justify-between">
            <p className="text-sm text-blue-700 dark:text-blue-300">
              <strong>💡 Informazioni:</strong> Questa pagina mostra tutte le aziende (sviluppatori e publisher) presenti nel database.
            </p>
            {companies.length > 0 && (
              <div className="text-sm text-blue-600 dark:text-blue-400">
                Mostrando {companies.length} di {totalResults} aziende
                {totalResults > resultsPerPage && (
                  <span className="ml-2">(Pagina {page} di {Math.ceil(totalResults / resultsPerPage)})</span>
                )}
              </div>
            )}
          </div>
        </div>
        <Table>
          <TableHeader>
            <tr>
              <TableCell>Nome Azienda</TableCell>
              <TableCell>Paese</TableCell>
              <TableCell>ID IGDB</TableCell>
              <TableCell>ID Database</TableCell>
            </tr>
          </TableHeader>
          <TableBody>
            {companies.length === 0 ? (
              <TableRow>
                <TableCell colSpan="4" className="text-center py-8">
                  <div className="text-gray-500 dark:text-gray-400">
                    <BuildingIcon className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                    <p>Nessuna azienda trovata</p>
                    <p className="text-sm">Prova a modificare i filtri di ricerca</p>
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              companies.map((company, i) => (
                <TableRow key={i}>
                  <TableCell>
                    <div className="flex items-center text-sm">
                      <div className="w-8 h-8 mr-3 bg-gray-200 dark:bg-gray-700 rounded flex items-center justify-center">
                        <BuildingIcon className="w-4 h-4 text-gray-500" />
                      </div>
                      <div>
                        <p className="font-semibold">{company.company_name || 'Nome non disponibile'}</p>
                        <p className="text-xs text-gray-600 dark:text-gray-400">
                          ID: {company.igdb_id || 'N/A'}
                        </p>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    {getCountryBadge(company.country)}
                  </TableCell>
                  <TableCell>
                    <span className="text-sm font-mono text-gray-600 dark:text-gray-400">
                      {company.igdb_id || 'N/A'}
                    </span>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm font-mono text-gray-500">
                      {company._id || 'N/A'}
                    </span>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
        {companies.length > 0 && (
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
      {companies.length > 0 && (
        <div className="grid gap-6 mb-8 md:grid-cols-3">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-blue-100 dark:bg-blue-900">
                <BuildingIcon className="h-6 w-6 text-blue-600 dark:text-blue-400" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  Totale Aziende
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
                <BuildingIcon className="h-6 w-6 text-green-600 dark:text-green-400" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  Con Paese
                </p>
                <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                  {companies.filter(company => company.country && company.country.trim()).length}
                </p>
              </div>
            </div>
          </div>
          
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-purple-100 dark:bg-purple-900">
                <GlobeIcon className="h-6 w-6 text-purple-600 dark:text-purple-400" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  Paesi Unici
                </p>
                <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                  {uniqueCountries.length}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

export default Companies 