import { useEffect, useRef, useState, startTransition } from 'react'
import type { FormEvent } from 'react'
import type { CandidatePayload, CardResult } from '../../types'
import { API_BASE } from '../../types'
import Brand from '../Brand/Brand'
import SearchForm from '../SearchForm/SearchForm'
import CandidatePicker from '../CandidatePicker/CandidatePicker'
import PriceResults from '../PriceResults/PriceResults'
import ImageDialog from '../ImageDialog/ImageDialog'
import './App.scss'

export default function App() {
  const [query, setQuery] = useState('')
  const [result, setResult] = useState<CardResult | null>(null)
  const [candidates, setCandidates] = useState<CandidatePayload | null>(null)
  const [status, setStatus] = useState('')
  const [statusType, setStatusType] = useState('')
  const [loading, setLoading] = useState(false)
  const [preview, setPreview] = useState<{ url: string; alt: string } | null>(null)
  const [rarities, setRarities] = useState<string[]>([])
  const [sets, setSets] = useState<string[]>([])
  const [sort, setSort] = useState('low')
  const abortRef = useRef<AbortController | null>(null)
  const compact = Boolean(result || candidates)

  useEffect(() => () => abortRef.current?.abort(), [])

  async function search(name: string, title?: string, page?: number, candidatesOnly = false) {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    setLoading(true)
    setStatus(title ? 'Loading the selected card…' : candidatesOnly ? 'Loading card names…' : 'Searching card names…')
    setStatusType('loading')
    try {
      const params = new URLSearchParams({ name })
      if (title) params.set('title', title)
      if (page != null) params.set('page', String(page))
      if (candidatesOnly) params.set('candidates_only', '1')
      const response = await fetch(`${API_BASE}/api/card-price?${params}`, { signal: controller.signal })
      const body = await response.json()
      if (!response.ok) throw new Error(body.error || 'Search failed')
      if (body.selectionRequired && (body as CandidatePayload).candidates.length > 1) {
        setResult(null)
        setCandidates(body as CandidatePayload)
        setStatus('Choose a card to continue.')
        setStatusType('error')
      } else if (body.selectionRequired) {
        search(name, (body as CandidatePayload).candidates[0]?.name || name)
        return
      } else {
        startTransition(() => {
          setResult(body as CardResult)
          setCandidates(null)
          setRarities([])
          setSets([])
          setSort('low')
        })
        setStatus('Live lookup complete.')
        setStatusType('success')
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return
      setStatus(error instanceof Error ? error.message : 'Search failed')
      setStatusType('error')
    } finally {
      if (!controller.signal.aborted) setLoading(false)
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    const name = query.trim()
    if (name.length < 3) {
      setStatus('Enter at least 3 characters.')
      setStatusType('error')
      return
    }
    search(name)
  }

  function goHome() {
    abortRef.current?.abort()
    setResult(null)
    setCandidates(null)
    setStatus('')
    setStatusType('')
    setLoading(false)
  }

  return <main className={`app-shell ${compact ? 'is-compact' : ''}`}>
    <div className="topline">
      <Brand compact={compact} onHome={goHome} />
      <SearchForm query={query} setQuery={setQuery} loading={loading} onSubmit={submit} />
    </div>
    <p className={`status ${statusType}`} aria-live="polite">{loading && <span className="spinner" aria-hidden="true" />}{status}</p>
    {candidates && <CandidatePicker payload={candidates} loading={loading} onSelect={(name) => { setQuery(name); search(name, name) }} onPage={(page) => search(candidates.query, undefined, page, true)} />}
    {result && <PriceResults result={result} rarities={rarities} sets={sets} sort={sort} setRarities={setRarities} setSets={setSets} setSort={setSort} onPreview={setPreview} />}
    {loading && <div className="loading-bar" role="status"><span /></div>}
    <ImageDialog preview={preview} onClose={() => setPreview(null)} />
  </main>
}
