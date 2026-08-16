import { useDeferredValue, useEffect, useMemo, useRef, useState, startTransition } from 'react'
import type { FormEvent } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.scss'

type Candidate = { name: string; source: string; imageUrl?: string | null }
type Pagination = { page: number; pageSize: number; total: number; totalPages: number; hasPrevious: boolean; hasMore: boolean }
type CandidatePayload = { selectionRequired: true; query: string; candidates: Candidate[]; pagination?: Pagination }
type Listing = {
  setNumber: string | null
  setName: string | null
  rarity: string | null
  condition: string | null
  priceJpy: number
  priceIdr: number | null
  onSale: boolean | null
  inStock: boolean | null
  stockText?: string | null
  imageUrl: string | null
  sourceUrl: string | null
}
type CardResult = {
  query: string
  card: { canonicalName: string; japaneseBaseName: string; englishText?: string; imageUrl?: string | null; sourceUrl: string }
  exchangeRate: { value: number; retrievedAt: string } | null
  filters: { rarities: string[]; sets: string[] }
  listings: Listing[]
  warnings: string[]
  yuyuteiSearchUrl: string
}

const API_BASE = import.meta.env.VITE_API_BASE_URL

const money = (value: number | null, currency: string) => value == null ? '—' : new Intl.NumberFormat('en-US', {
  style: 'currency', currency, maximumFractionDigits: 0,
}).format(value)

function App() {
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
      if (body.selectionRequired) {
        setResult(null)
        setCandidates(body as CandidatePayload)
        setStatus('Choose a card to continue.')
        setStatusType('error')
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

  return <main className={`app-shell ${compact ? 'is-compact' : ''}`}>
    <div className="topline">
      <header className="brand">
        <p className="eyebrow">Yugioh OCG / market lens</p>
        <h1>{compact ? <>Find the print. <em>Know the price.</em></> : <>Find the print.<br /><em>Know the price.</em></>}</h1>
        {!compact && <p className="lede">Search an English card name. We resolve the Japanese base name, then pull Yuyu-tei listings by printing.</p>}
      </header>
      <form className="search-form" onSubmit={submit}>
        <label className="sr-only" htmlFor="card-name">Card name</label>
        <input id="card-name" value={query} onChange={(event) => setQuery(event.target.value)} placeholder='Try Maxx "C"' autoComplete="off" required minLength={3} maxLength={100} />
        <button type="submit" disabled={loading}>Search <span aria-hidden="true">↗</span></button>
      </form>
    </div>
    <p className={`status ${statusType}`} aria-live="polite">{status}</p>
    {candidates && <CandidatePicker payload={candidates} onSelect={(name) => { setQuery(name); search(name, name) }} onPage={(page) => search(candidates.query, undefined, page, true)} />}
    {result && <PriceResults result={result} rarities={rarities} sets={sets} sort={sort} setRarities={setRarities} setSets={setSets} setSort={setSort} onPreview={setPreview} />}
    <ImageDialog preview={preview} onClose={() => setPreview(null)} />
  </main>
}

function CandidatePicker({ payload, onSelect, onPage }: { payload: CandidatePayload; onSelect: (name: string) => void; onPage: (page: number) => void }) {
  const pagination = payload.pagination
  const page = pagination?.page ?? 0
  const totalPages = pagination?.totalPages ?? 1
  return <section className="candidate-section">
    <div className="section-heading">
      <p className="eyebrow">{payload.candidates.length > 1 ? 'Ambiguous search' : 'Suggested match'}</p>
      <h2>Choose the card</h2>
      <p>{payload.candidates.length > 1 ? 'Select the exact card before checking Yuyu-tei.' : 'Did you mean one of these cards?'}</p>
      {pagination && <p className="candidate-count">{pagination.total} possible cards · page {page + 1} of {totalPages}</p>}
    </div>
    <div className="candidate-list">
      {payload.candidates.map((candidate) => <button className="candidate" key={candidate.name} type="button" onClick={() => onSelect(candidate.name)}>
        {candidate.imageUrl ? <img className="candidate-image" src={candidate.imageUrl} alt="" loading="lazy" /> : <span className="candidate-image placeholder" aria-hidden="true" />}
        <span className="candidate-name"><strong>{candidate.name}</strong><small>{candidate.source}</small></span><span aria-hidden="true">↗</span>
      </button>)}
    </div>
    {pagination && totalPages > 1 && <nav className="candidate-pagination" aria-label="Candidate pages">
      <button className="page-button" type="button" disabled={!pagination.hasPrevious} onClick={() => onPage(page - 1)}>Previous</button>
      <label htmlFor="candidate-page">Page</label><input id="candidate-page" type="number" min={1} max={totalPages} defaultValue={page + 1} onKeyDown={(event) => { if (event.key === 'Enter') onPage(Number(event.currentTarget.value) - 1) }} />
      <button className="page-button" type="button" onClick={(event) => onPage(Number((event.currentTarget.previousElementSibling as HTMLInputElement).value) - 1)}>Go</button>
      <button className="page-button" type="button" disabled={!pagination.hasMore} onClick={() => onPage(page + 1)}>Next</button>
    </nav>}
  </section>
}

function PriceResults({ result, rarities, sets, sort, setRarities, setSets, setSort, onPreview }: { result: CardResult; rarities: string[]; sets: string[]; sort: string; setRarities: (values: string[]) => void; setSets: (values: string[]) => void; setSort: (value: string) => void; onPreview: (preview: { url: string; alt: string }) => void }) {
  const deferredListings = useDeferredValue(result.listings)
  const listings = useMemo(() => deferredListings.filter((listing) => (!rarities.length || rarities.includes(listing.rarity || '')) && (!sets.length || sets.includes(listing.setName || ''))).sort((a, b) => sort === 'high' ? b.priceJpy - a.priceJpy : sort === 'rarity' ? (a.rarity || '').localeCompare(b.rarity || '') : sort === 'set' ? (a.setName || '').localeCompare(b.setName || '') : a.priceJpy - b.priceJpy), [deferredListings, rarities, sets, sort])
  const cardImage = result.card.imageUrl || result.listings.find((listing) => listing.imageUrl)?.imageUrl
  const clear = (setter: (values: string[]) => void) => setter([])
  return <section className="results-section">
    <div className="result-header">
      {cardImage && <button className="image-button card-image" type="button" onClick={() => onPreview({ url: cardImage, alt: `${result.card.canonicalName} card image` })}><img src={cardImage} alt={`${result.card.canonicalName} card image`} /></button>}
      <div className="card-identity"><p className="eyebrow">Resolved card</p><h2>{result.card.canonicalName}</h2><p className="japanese">{result.card.japaneseBaseName}</p></div>
      <div className="card-actions">{result.card.englishText && <details className="text-toggle"><summary>English text</summary><p>{result.card.englishText}</p></details>}<a className="wiki-link" href={result.card.sourceUrl} target="_blank" rel="noreferrer">Yugipedia ↗</a></div>
    </div>
    <div className="meta-row"><span>{result.exchangeRate ? `1 JPY = ${result.exchangeRate.value} IDR · ${result.exchangeRate.retrievedAt}` : 'IDR rate unavailable'}</span><a href={result.yuyuteiSearchUrl} target="_blank" rel="noreferrer">Open Yuyu-tei search ↗</a></div>
    <div className="controls">
      <Filter label="Rarity" values={result.filters.rarities} selected={rarities} onChange={setRarities} onClear={() => clear(setRarities)} />
      <Filter label="Set" values={result.filters.sets} selected={sets} onChange={setSets} onClear={() => clear(setSets)} />
      <label className="sort-control">Sort<select value={sort} onChange={(event) => setSort(event.target.value)}><option value="low">Lowest price</option><option value="high">Highest price</option><option value="rarity">Rarity</option><option value="set">Set</option></select></label>
      <button className="clear" type="button" onClick={() => { clear(setRarities); clear(setSets); setSort('low') }}>Clear all filters</button>
    </div>
    <div className="results-line"><strong>{listings.length} listing{listings.length === 1 ? '' : 's'}</strong><span>{result.warnings.join(' ')}</span></div>
    <div className="listing-list">{listings.map((listing) => <article className="listing" key={`${listing.sourceUrl}-${listing.rarity}`}>
      {listing.imageUrl ? <button className="image-button listing-image" type="button" onClick={() => onPreview({ url: listing.imageUrl!, alt: listing.setNumber || 'Card image' })}><img src={listing.imageUrl} alt="" loading="lazy" /></button> : <span className="listing-image placeholder" aria-hidden="true" />}
      <div className="listing-main"><span className="rarity">{listing.rarity || 'Rarity unknown'}</span><strong>{listing.setNumber || 'Set number unknown'}</strong><span className="muted">{listing.setName || 'Set unknown'}{listing.condition ? ` · ${listing.condition}` : ''}</span></div>
      <div className="price-stack"><strong>{money(listing.priceIdr, 'IDR')}</strong><span>{money(listing.priceJpy, 'JPY')}{listing.onSale ? ' · sale' : ''}</span></div><a className="source-link" href={listing.sourceUrl || result.yuyuteiSearchUrl} target="_blank" rel="noreferrer">Source ↗</a>
    </article>)}</div>
  </section>
}

function Filter({ label, values, selected, onChange, onClear }: { label: string; values: string[]; selected: string[]; onChange: (values: string[]) => void; onClear: () => void }) {
  return <div className="filter-control"><label htmlFor={`${label}-filter`}>{label}</label><select id={`${label}-filter`} multiple value={selected} onChange={(event) => onChange(Array.from(event.target.selectedOptions, (option) => option.value))}>{values.map((value) => <option key={value} value={value}>{value}</option>)}</select><button className="clear-filter" type="button" onClick={onClear}>Clear {label.toLowerCase()}</button></div>
}

function ImageDialog({ preview, onClose }: { preview: { url: string; alt: string } | null; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null)
  useEffect(() => { if (preview && !dialog.current?.open) dialog.current?.showModal(); if (!preview && dialog.current?.open) dialog.current.close() }, [preview])
  return <dialog ref={dialog} className="image-dialog" onClick={(event) => { if (event.target === dialog.current) onClose() }}><button className="dialog-close" type="button" onClick={onClose} aria-label="Close image preview">×</button>{preview && <><img src={preview.url} alt={preview.alt} /><p>{preview.alt}</p></>}</dialog>
}

createRoot(document.getElementById('root')!).render(<App />)
