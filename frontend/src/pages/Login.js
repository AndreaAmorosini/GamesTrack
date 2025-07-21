import React, { useState, useEffect } from 'react'
import { Link, useHistory } from 'react-router-dom'
import ImageLight from '../assets/img/login-office.jpeg'
import ImageDark from '../assets/img/login-office-dark.jpeg'
import { GithubIcon, TwitterIcon } from '../icons'
import { Label, Input, Button, HelperText } from '@windmill/react-ui'
import { login, getUserProfile, isAuthenticated } from '../services/api'

function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const history = useHistory()

  // Reindirizza automaticamente se l'utente è già autenticato
  useEffect(() => {
    if (isAuthenticated()) {
      const { from } = history.location.state || {};
      if (from) {
        history.push(from.pathname);
      } else {
        history.push('/app');
      }
    }
  }, [history]);

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    try {
      // Prima effettuiamo il login
      const loginData = await login(username, password)
      console.log('Login successful:', loginData)
      
      try {
        // Se il login ha successo, proviamo a ottenere i dati dell'utente
        const userData = await getUserProfile()
        console.log('User data retrieved:', userData)
        localStorage.setItem('user', JSON.stringify(userData))
      } catch (userError) {
        // Se fallisce il recupero dei dati utente, logghiamo l'errore ma procediamo
        console.warn('Failed to fetch user profile:', userError)
      }

      // Controlla se c'è una destinazione salvata dal ProtectedRoute
      const { from } = history.location.state || {};
      if (from) {
        // Redirect alla pagina originale richiesta
        history.push(from.pathname);
      } else {
        // Redirect alla dashboard di default
        history.push('/app');
      }
    } catch (err) {
      console.error('Login error:', err)
      if (err.message.includes('Incorrect username or password')) {
        setError('Username o password non validi')
      } else {
        setError('Si è verificato un errore durante il login. Riprova più tardi.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex items-center min-h-screen p-6 bg-gray-50 dark:bg-gray-900">
      <div className="flex-1 h-full max-w-4xl mx-auto overflow-hidden bg-white rounded-lg shadow-xl dark:bg-gray-800">
        <div className="flex flex-col overflow-y-auto md:flex-row">
          <div className="h-32 md:h-auto md:w-1/2">
            <img
              aria-hidden="true"
              className="object-cover w-full h-full dark:hidden"
              src={ImageLight}
              alt="Office"
            />
            <img
              aria-hidden="true"
              className="hidden object-cover w-full h-full dark:block"
              src={ImageDark}
              alt="Office"
            />
          </div>
          <main className="flex items-center justify-center p-6 sm:p-12 md:w-1/2">
            <div className="w-full">
              <h1 className="mb-4 text-xl font-semibold text-gray-700 dark:text-gray-200">Login</h1>
              <form onSubmit={handleSubmit}>
                <Label>
                  <span>Username</span>
                  <Input 
                    className="mt-1" 
                    type="text" 
                    placeholder="Il tuo username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                  />
                </Label>

                <Label className="mt-4">
                  <span>Password</span>
                  <Input 
                    className="mt-1" 
                    type="password" 
                    placeholder="***************"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                </Label>

                {error && (
                  <HelperText valid={false} className="mt-4">
                    {error}
                  </HelperText>
                )}

                <Button 
                  type="submit" 
                  className="mt-4" 
                  block 
                  disabled={isLoading}
                >
                  {isLoading ? 'Accesso in corso...' : 'Accedi'}
                </Button>
              </form>

              <hr className="my-8" />

              <Button block layout="outline">
                <GithubIcon className="w-4 h-4 mr-2" aria-hidden="true" />
                Github
              </Button>
              <Button className="mt-4" block layout="outline">
                <TwitterIcon className="w-4 h-4 mr-2" aria-hidden="true" />
                Twitter
              </Button>

              <p className="mt-4">
                <Link
                  className="text-sm font-medium text-purple-600 dark:text-purple-400 hover:underline"
                  to="/forgot-password"
                >
                  Password dimenticata?
                </Link>
              </p>
              <p className="mt-1">
                <Link
                  className="text-sm font-medium text-purple-600 dark:text-purple-400 hover:underline"
                  to="/create-account"
                >
                  Crea un account
                </Link>
              </p>
            </div>
          </main>
        </div>
      </div>
    </div>
  )
}

export default Login
