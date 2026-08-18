import type { FormEvent } from 'react'
import './SearchForm.scss'

export default function SearchForm({ query, setQuery, loading, includeAe, setIncludeAe, onSubmit }: { query: string; setQuery: (value: string) => void; loading: boolean; includeAe: boolean; setIncludeAe: (value: boolean) => void; onSubmit: (event: FormEvent) => void }) {
  return <form className="search-form" onSubmit={onSubmit}>
    <label className="sr-only" htmlFor="card-name">Card name</label>
    <input id="card-name" value={query} onChange={(event) => setQuery(event.target.value)} placeholder='Try Maxx "C"' autoComplete="off" required minLength={3} maxLength={100} />
    <button type="submit" disabled={loading} aria-label="Search"><span className="search-label">Search</span><svg className="search-icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 5 5" /></svg></button>
    <label className="ae-toggle">
      <input type="checkbox" checked={includeAe} onChange={(event) => setIncludeAe(event.target.checked)} />
      <span>Include Asian English prints</span>
    </label>
  </form>
}
