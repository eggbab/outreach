/*
  Reusable skeleton loading components.
  Shows immediately while API data loads.
*/

export function SkeletonCard({ className = '' }) {
  return (
    <div className={`bg-white rounded-xl border border-gray-200 p-5 animate-pulse ${className}`}>
      <div className="h-3 bg-gray-200 rounded w-1/3 mb-3" />
      <div className="h-6 bg-gray-200 rounded w-1/2" />
    </div>
  )
}

export function SkeletonRow() {
  return (
    <div className="px-4 py-3 flex items-center gap-4 animate-pulse">
      <div className="h-3 bg-gray-200 rounded flex-1" />
      <div className="h-3 bg-gray-200 rounded w-24" />
      <div className="h-3 bg-gray-200 rounded w-16" />
      <div className="h-5 bg-gray-200 rounded w-12" />
    </div>
  )
}

export function SkeletonPage({ cards = 4, rows = 5 }) {
  return (
    <div>
      <div className="mb-8 animate-pulse">
        <div className="h-7 bg-gray-200 rounded w-40 mb-2" />
        <div className="h-4 bg-gray-200 rounded w-64" />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {Array.from({ length: cards }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
      <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
        {Array.from({ length: rows }).map((_, i) => (
          <SkeletonRow key={i} />
        ))}
      </div>
    </div>
  )
}

export function SkeletonKanban() {
  return (
    <div className="flex gap-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="flex-1 animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-16 mb-3" />
          <div className="space-y-2">
            <div className="h-16 bg-gray-100 rounded-lg" />
            {i < 2 && <div className="h-16 bg-gray-100 rounded-lg" />}
          </div>
        </div>
      ))}
    </div>
  )
}
