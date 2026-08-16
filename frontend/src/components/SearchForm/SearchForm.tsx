import type { FormEvent } from 'react'
import './SearchForm.scss'

export default function SearchForm({ query, setQuery, loading, onSubmit }: { query: string; setQuery: (value: string) => void; loading: boolean; onSubmit: (event: FormEvent) => void }) {
  return <form className="search-form" onSubmit={onSubmit}>
    <label className="sr-only" htmlFor="card-name">Card name</label>
    <input id="card-name" value={query} onChange={(event) => setQuery(event.target.value)} placeholder='Try Maxx "C"' autoComplete="off" required minLength={3} maxLength={100} />
    <button type="submit" disabled={loading}>Search <span aria-hidden="true">↗</span></button>
  </form>
}
