import React from 'react'

/** Scheletro per card (Wishlist, statistiche) */
export function CardSkeleton() {
  return (
    <div className="p-4 bg-white rounded-lg shadow-md dark:bg-gray-800 animate-pulse" aria-hidden="true">
      <div className="h-5 w-2/3 mx-auto bg-gray-200 rounded dark:bg-gray-700 mb-6"></div>
      <div className="w-24 h-24 mx-auto bg-gray-200 rounded dark:bg-gray-700 mb-6"></div>
      <div className="h-4 w-1/2 mx-auto bg-gray-200 rounded dark:bg-gray-700"></div>
    </div>
  )
}

/** Griglia di scheletri per card */
export function CardSkeletonGrid({ count = 6 }) {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {Array.from({ length: count }).map((_, i) => (
        <CardSkeleton key={i} />
      ))}
    </div>
  )
}

/** Scheletro per righe di tabella */
export function TableSkeleton({ rows = 5, cols = 5 }) {
  return (
    <div className="animate-pulse" aria-hidden="true">
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex gap-4 py-3 border-b border-gray-200 dark:border-gray-700">
          {Array.from({ length: cols }).map((_, c) => (
            <div key={c} className="h-4 flex-1 bg-gray-200 rounded dark:bg-gray-700"></div>
          ))}
        </div>
      ))}
    </div>
  )
}
