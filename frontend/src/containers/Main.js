import React from 'react'

function Main({ children }) {
  return (
    <main className="h-full overflow-y-auto">
      <div className="w-full max-w-9xl grid px-4 sm:px-6 lg:px-8 mx-auto">{children}</div>
    </main>
  )
}

export default Main
