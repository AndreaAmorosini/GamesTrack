import React, { useState, useEffect } from 'react'
import { useHistory } from 'react-router-dom'
import PageTitle from '../components/Typography/PageTitle'
import SectionTitle from '../components/Typography/SectionTitle'
import { Input, HelperText, Label, Button } from '@windmill/react-ui'
import { getUserProfile, updateUserProfile } from '../services/api'

function Forms() {
  const history = useHistory()
  const [formData, setFormData] = useState({
    email: '',
    username: '',
    password: '',
    steam: '',
    steam_api_key: '',
    psn: '',
    psn_api_key: '',
    metadata_api_key: ''
  })

  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    const loadUserData = async () => {
      try {
        // Verifica se esiste un token
        const token = localStorage.getItem('token')
        if (!token) {
          setError('Sessione scaduta. Effettua nuovamente il login.')
          history.push('/login')
          return
        }

        setIsLoading(true)
        const userData = await getUserProfile()
        console.log('Dati utente ricevuti:', userData) // Per debug
        setFormData(prevData => ({
          ...prevData,
          email: userData.email || '',
          username: userData.username || '',
          steam: userData.steam || '',
          steam_api_key: userData.steam_api_key || '',
          psn: userData.psn || '',
          psn_api_key: userData.psn_api_key || '',
          metadata_api_key: userData.metadata_api_key || ''
        }))
      } catch (err) {
        console.error('Error loading user data:', err)
        if (err.message === 'No token found' || err.message.includes('401') || err.message.includes('403')) {
          setError('Sessione scaduta. Effettua nuovamente il login.')
          history.push('/login')
        } else if (err.message.includes('404')) {
          setError('Impossibile trovare i dati utente. Riprova più tardi.')
        } else {
          setError('Errore nel caricamento dei dati utente. Riprova più tardi.')
        }
      } finally {
        setIsLoading(false)
      }
    }

    loadUserData()
  }, [history])

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prevData => ({
      ...prevData,
      [name]: value
    }))
    console.log('Form data aggiornato:', formData) // Per debug
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    setIsLoading(true)

    try {
      // Verifica se esiste un token
      const token = localStorage.getItem('token')
      if (!token) {
        setError('Sessione scaduta. Effettua nuovamente il login.')
        history.push('/login')
        return
      }

      console.log('Dati inviati al server:', formData) // Per debug
      await updateUserProfile(formData)
      setSuccess('Profilo aggiornato con successo')
      // Reset password field after successful update
      setFormData(prev => ({
        ...prev,
        password: ''
      }))
    } catch (err) {
      console.error('Error updating profile:', err)
      if (err.message.includes('401') || err.message.includes('403')) {
        setError('Sessione scaduta. Effettua nuovamente il login.')
        history.push('/login')
      } else {
        setError(err.message || 'Errore durante l\'aggiornamento del profilo')
      }
    } finally {
      setIsLoading(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-lg font-semibold text-gray-700 dark:text-gray-200">
          Caricamento...
        </div>
      </div>
    )
  }

  return (
    <>
      <PageTitle>Profilo Utente</PageTitle>

      <div className="px-4 py-3 mb-8 bg-white rounded-lg shadow-md dark:bg-gray-800">
        <form onSubmit={handleSubmit}>
          {error && (
            <div className="mb-4 text-red-600 dark:text-red-400">
              <HelperText valid={false}>{error}</HelperText>
            </div>
          )}
          {success && (
            <div className="mb-4 text-green-600 dark:text-green-400">
              <HelperText valid={true}>{success}</HelperText>
            </div>
          )}

          <SectionTitle>Informazioni Base</SectionTitle>
          <Label className="mt-4">
            <span>Email</span>
            <Input
              className="mt-1"
              name="email"
              type="email"
              placeholder="email@example.com"
              value={formData.email}
              onChange={handleChange}
              required
            />
          </Label>

          <Label className="mt-4">
            <span>Username</span>
            <Input
              className="mt-1"
              name="username"
              placeholder="Il tuo username"
              value={formData.username}
              disabled={true}
              readOnly={true}
              required
              minLength={3}
              maxLength={50}
            />
            <HelperText>
              L'username non può essere modificato dopo la registrazione
            </HelperText>
          </Label>

          <Label className="mt-4">
            <span>Password</span>
            <Input
              className="mt-1"
              name="password"
              type="password"
              placeholder="Lascia vuoto per non modificare"
              value={formData.password}
              onChange={handleChange}
              minLength={8}
            />
            <HelperText>
              La password deve essere di almeno 8 caratteri
            </HelperText>
          </Label>

          <SectionTitle className="mt-6">Steam</SectionTitle>
          <Label className="mt-4">
            <span>Steam ID</span>
            <Input
              className="mt-1"
              name="steam"
              placeholder="Il tuo Steam ID"
              value={formData.steam}
              onChange={handleChange}
            />
          </Label>

          <Label className="mt-4">
            <span>Steam API Key</span>
            <Input
              className="mt-1"
              name="steam_api_key"
              type="password"
              placeholder="La tua Steam API Key"
              value={formData.steam_api_key}
              onChange={handleChange}
            />
            <HelperText>
              Puoi ottenere la tua API Key da{' '}
              <a
                href="https://steamcommunity.com/dev/apikey"
                target="_blank"
                rel="noopener noreferrer"
                className="text-purple-600 dark:text-purple-400 hover:underline"
              >
                Steam Developer
              </a>
            </HelperText>
          </Label>

          <SectionTitle className="mt-6">PlayStation Network</SectionTitle>
          <Label className="mt-4">
            <span>PSN ID</span>
            <Input
              className="mt-1"
              name="psn"
              placeholder="Il tuo PSN ID"
              value={formData.psn}
              onChange={handleChange}
            />
          </Label>

          <Label className="mt-4">
            <span>PSN API Key</span>
            <Input
              className="mt-1"
              name="psn_api_key"
              type="password"
              placeholder="La tua PSN API Key"
              value={formData.psn_api_key}
              onChange={handleChange}
            />
          </Label>

          <SectionTitle className="mt-6">API Metadata</SectionTitle>
          <Label className="mt-4">
            <span>Metadata API Key</span>
            <Input
              className="mt-1"
              name="metadata_api_key"
              type="password"
              placeholder="La tua Metadata API Key"
              value={formData.metadata_api_key}
              onChange={handleChange}
            />
          </Label>

          <div className="mt-6">
            <Button
              type="submit"
              disabled={isLoading}
              className="w-full"
            >
              {isLoading ? 'Salvataggio in corso...' : 'Salva Modifiche'}
            </Button>
          </div>
        </form>
      </div>
    </>
  )
}

export default Forms
