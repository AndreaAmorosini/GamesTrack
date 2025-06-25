import React, { useState } from 'react'
import { Link, useHistory } from 'react-router-dom'
import ImageLight from '../assets/img/create-account-office.jpeg'
import ImageDark from '../assets/img/create-account-office-dark.jpeg'
import { GithubIcon, TwitterIcon } from '../icons'
import { Input, Label, Button, HelperText } from '@windmill/react-ui'
import { register } from '../services/api'

function CreateAccount() {
  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const history = useHistory()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    // Validazione
    if (!email || !username || !password || !confirmPassword) {
      setError('Tutti i campi sono obbligatori')
      return
    }

    if (password !== confirmPassword) {
      setError('Le password non coincidono')
      return
    }

    if (password.length < 8) {
      setError('La password deve essere lunga almeno 8 caratteri')
      return
    }

    try {
      setIsLoading(true)
      await register({ email, username, password })
      history.push('/login')
    } catch (err) {
      setError('Errore durante la registrazione. Riprova più tardi.')
      console.error('Registration error:', err)
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
              <h1 className="mb-4 text-xl font-semibold text-gray-700 dark:text-gray-200">
                Crea account
              </h1>

              <form onSubmit={handleSubmit}>
                {error && (
                  <HelperText valid={false} className="mb-4">
                    {error}
                  </HelperText>
                )}

                <Label>
                  <span>Email</span>
                  <Input 
                    className="mt-1" 
                    type="email" 
                    placeholder="john@doe.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </Label>

                <Label className="mt-4">
                  <span>Username</span>
                  <Input 
                    className="mt-1" 
                    type="text" 
                    placeholder="johndoe"
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

                <Label className="mt-4">
                  <span>Conferma password</span>
                  <Input 
                    className="mt-1" 
                    type="password" 
                    placeholder="***************"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                  />
                </Label>

                <Button 
                  type="submit" 
                  block 
                  className="mt-4"
                  disabled={isLoading}
                >
                  {isLoading ? 'Creazione in corso...' : 'Crea account'}
                </Button>
              </form>

              <p className="mt-4">
                <Link
                  className="text-sm font-medium text-purple-600 dark:text-purple-400 hover:underline"
                  to="/login"
                >
                  Hai già un account? Accedi
                </Link>
              </p>
            </div>
          </main>
        </div>
      </div>
    </div>
  )
}

export default CreateAccount
