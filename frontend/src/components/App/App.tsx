import { useEffect, useRef, useState, startTransition } from 'react'
import type { FormEvent } from 'react'
import type { CandidatePayload, CardResult, SavedSearch } from '../../types'
import { API_BASE } from '../../types'
import Brand from '../Brand/Brand'
import SearchForm from '../SearchForm/SearchForm'
import CandidatePicker from '../CandidatePicker/CandidatePicker'
import PriceResults from '../PriceResults/PriceResults'
import ImageDialog from '../ImageDialog/ImageDialog'
import SearchMemory from '../SearchMemory/SearchMemory'
import './App.scss'

const HISTORY_KEY = 'peeking-goblin.search-history'
const BOOKMARKS_KEY = 'peeking-goblin.search-bookmarks'

function readSavedSearches(key: string): SavedSearch[] {
  try {
    const value = JSON.parse(localStorage.getItem(key) || '[]')
    return Array.isArray(value) ? value.filter((item): item is SavedSearch => item && typeof item.query === 'string' && typeof item.includeAe === 'boolean' && typeof item.createdAt === 'number') : []
  } catch {
    return []
  }
}

function searchKey(search: SavedSearch) {
  return `${search.query.trim().toLowerCase()}::${search.title?.trim().toLowerCase() || ''}::${search.includeAe}`
}

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
  const [sources, setSources] = useState<string[]>([])
  const [sort, setSort] = useState('low')
  const [includeAe, setIncludeAe] = useState(false)
  const [resultIncludeAe, setResultIncludeAe] = useState(false)
  const [history, setHistory] = useState<SavedSearch[]>(() => readSavedSearches(HISTORY_KEY))
  const [bookmarks, setBookmarks] = useState<SavedSearch[]>(() => readSavedSearches(BOOKMARKS_KEY))
  const [showBookmarks, setShowBookmarks] = useState(false)
  const abortRef = useRef<AbortController | null>(null)
  const compact = Boolean(result || candidates)

  useEffect(() => () => abortRef.current?.abort(), [])
  useEffect(() => localStorage.setItem(HISTORY_KEY, JSON.stringify(history)), [history])
  useEffect(() => localStorage.setItem(BOOKMARKS_KEY, JSON.stringify(bookmarks)), [bookmarks])

  // background refetch when AE catalog finishes warming — no spinner, no reload
  useEffect(() => {
    if (!result?.aePending) return
    const timer = setTimeout(() => search(result.query, result.card.resolvedTitle, undefined, false, true, resultIncludeAe), 4000)
    return () => clearTimeout(timer)
  }, [result])

  async function search(name: string, title?: string, page?: number, candidatesOnly = false, silent = false, ae = includeAe) {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    if (!silent) {
      setLoading(true)
      setStatus(title ? 'Loading the selected card…' : candidatesOnly ? 'Loading card names…' : 'Searching card names…')
      setStatusType('loading')
    }
    try {
      const params = new URLSearchParams({ name })
      if (title) params.set('title', title)
      if (page != null) params.set('page', String(page))
      if (candidatesOnly) params.set('candidates_only', '1')
      if (ae) params.set('include_ae', '1')
      const response = await fetch(`${API_BASE}/api/card-price?${params}`, { signal: controller.signal })
      const body = await response.json()
      if (!response.ok) throw new Error(body.error || 'Search failed')
      if (body.selectionRequired && (body as CandidatePayload).candidates.length > 1) {
        setResult(null)
        setCandidates(body as CandidatePayload)
        if (!silent) {
          setStatus('Choose a card to continue.')
          setStatusType('error')
        }
      } else if (body.selectionRequired) {
        search(name, (body as CandidatePayload).candidates[0]?.name || name, undefined, false, false, ae)
        return
      } else {
        startTransition(() => {
          setResult(body as CardResult)
          setResultIncludeAe(ae)
          setCandidates(null)
          if (!silent) {
            setRarities([])
            setSets([])
            setSources([])
            setSort('low')
            const saved = { query: name, title: (body as CardResult).card.resolvedTitle, includeAe: ae, createdAt: Date.now() }
            setHistory((current) => [saved, ...current.filter((item) => searchKey(item) !== searchKey(saved))].slice(0, 10))
          }
        })
        if (!silent) {
          setStatus('Live lookup complete.')
          setStatusType('success')
        }
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return
      if (!silent) {
        setStatus(error instanceof Error ? error.message : 'Search failed')
        setStatusType('error')
      }
    } finally {
      if (!controller.signal.aborted && !silent) setLoading(false)
    }
  }

  function runSavedSearch(saved: SavedSearch) {
    setQuery(saved.query)
    setIncludeAe(saved.includeAe)
    search(saved.query, saved.title, undefined, false, false, saved.includeAe)
  }

  function toggleBookmark() {
    if (!result) return
    const saved = { query: result.card.canonicalName, title: result.card.resolvedTitle, includeAe: resultIncludeAe, createdAt: Date.now() }
    setBookmarks((current) => current.some((item) => searchKey(item) === searchKey(saved))
      ? current.filter((item) => searchKey(item) !== searchKey(saved))
      : [saved, ...current])
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
    setShowBookmarks(false)
  }

  return <>
    <main className={`app-shell ${compact ? 'is-compact' : ''}`}>
      <div className="topline">
        <Brand compact={compact} onHome={goHome} />
        <SearchForm query={query} setQuery={setQuery} loading={loading} includeAe={includeAe} setIncludeAe={setIncludeAe} onSubmit={submit} />
      </div>
      <SearchMemory compact={compact} showBookmarks={showBookmarks} onToggle={() => setShowBookmarks((shown) => !shown)} history={history} bookmarks={bookmarks} onClearHistory={() => setHistory([])} onClearBookmarks={() => setBookmarks([])} onRun={runSavedSearch} onRemoveBookmark={(saved) => setBookmarks((current) => current.filter((item) => searchKey(item) !== searchKey(saved)))} />
      <p className={`status ${statusType}`} aria-live="polite">{loading && <span className="spinner" aria-hidden="true" />}{status}</p>
      {candidates && <CandidatePicker payload={candidates} loading={loading} onSelect={(name) => { setQuery(name); search(name, name) }} onPage={(page) => search(candidates.query, undefined, page, true)} />}
      {result && <PriceResults result={result} rarities={rarities} sets={sets} sources={sources} sort={sort} setRarities={setRarities} setSets={setSets} setSources={setSources} setSort={setSort} onPreview={setPreview} bookmarked={bookmarks.some((item) => searchKey(item) === searchKey({ query: result.card.canonicalName, title: result.card.resolvedTitle, includeAe: resultIncludeAe, createdAt: 0 }))} onToggleBookmark={toggleBookmark} />}
      {loading && <div className="loading-bar" role="status"><span /></div>}
      <ImageDialog preview={preview} onClose={() => setPreview(null)} />
    </main>
    <footer className="site-footer"><span><a href="https://github.com/Krocified/peeking-goblin" target="_blank" rel="noreferrer">Open source</a> · built by <a href="https://github.com/Krocified" target="_blank" rel="noreferrer">Krocified</a></span><a className="footer-action" href="https://github.com/Krocified/peeking-goblin/issues" target="_blank" rel="noreferrer">Report an issue ↗</a></footer>
  </>
}
