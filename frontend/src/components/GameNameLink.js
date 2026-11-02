import React from 'react'
import { Link } from 'react-router-dom'

/**
 * Nome gioco cliccabile: apre la pagina di dettaglio (/app/games/:gameId).
 * Uso: <GameNameLink name={g.name} gameId={g.game_id} />
 */
const GameNameLink = ({ name, gameId, className = '', originalName }) => {
  if (!gameId) return <span className={className}>{name}</span>
  return (
    <Link
      to={`/app/games/${gameId}`}
      className={`font-semibold text-gray-900 dark:text-white hover:text-purple-600 dark:hover:text-purple-400 ${className}`}
    >
      {name}
    </Link>
  )
}

export default GameNameLink
