import { useDeferredValue, useMemo, useState } from 'react'
import type { CardResult } from '../../types'
import { money } from '../../types'
import Filter from './Filter'
import CardImage from './CardImage'
import './PriceResults.scss'

export default function PriceResults({ result, rarities, sets, sources, sort, setRarities, setSets, setSources, setSort, onPreview, bookmarked, onToggleBookmark }: { result: CardResult; rarities: string[]; sets: string[]; sources: string[]; sort: string; setRarities: (values: string[]) => void; setSets: (values: string[]) => void; setSources: (values: string[]) => void; setSort: (value: string) => void; onPreview: (preview: { url: string; alt: string }) => void; bookmarked: boolean; onToggleBookmark: () => void }) {
  const [showText, setShowText] = useState(false)
  const deferredListings = useDeferredValue(result.listings)
  const hasAe = deferredListings.some((listing) => listing.source === 'tcg-corner')
  const listings = useMemo(() => deferredListings.filter((listing) => (!rarities.length || rarities.includes(listing.rarity || '')) && (!sets.length || sets.includes(listing.setName || '')) && (!sources.length || sources.includes(listing.source))).sort((a, b) => sort === 'high' ? (b.priceIdr ?? 0) - (a.priceIdr ?? 0) : sort === 'rarity' ? (a.rarity || '').localeCompare(b.rarity || '') : sort === 'set' ? (a.setName || '').localeCompare(b.setName || '') : (a.priceIdr ?? 0) - (b.priceIdr ?? 0)), [deferredListings, rarities, sets, sources, sort])
  const cardImage = result.card.imageUrl || result.listings.find((listing) => listing.imageUrl)?.imageUrl
  const clear = (setter: (values: string[]) => void) => setter([])
  return <section className="results-section">
    <div className="result-header">
      <CardImage src={cardImage} alt={`${result.card.canonicalName} card image`} onPreview={onPreview} />
       <div className="card-identity"><p className="eyebrow">Resolved card</p><h2>{result.card.canonicalName}</h2><p className="japanese">{result.card.japaneseBaseName}</p></div>
       <div className="card-actions">{result.card.englishText && <button className="text-toggle" type="button" aria-expanded={showText} onClick={() => setShowText(!showText)}>{showText ? 'Hide text' : 'Show text'}</button>}<button className={`bookmark ${bookmarked ? 'is-bookmarked' : ''}`} type="button" aria-pressed={bookmarked} onClick={onToggleBookmark}>{bookmarked ? 'Bookmarked' : 'Bookmark search'}</button><a className="wiki-link" href={result.card.sourceUrl} target="_blank" rel="noreferrer">Yugipedia ↗</a></div>
    </div>
    {showText && <p className="english-text">{result.card.englishText}</p>}
    <div className="meta-row">
      <span>{result.exchangeRate ? Object.entries(result.exchangeRate.rates).filter(([currency]) => currency !== 'IDR').map(([currency, value]) => `1 ${currency} = ${Math.round(value).toLocaleString('en-US')} IDR`).join(' · ') + ` · ${result.exchangeRate.retrievedAt}` : 'IDR rate unavailable'}</span>
      <span className="meta-links"><a href={result.yuyuteiSearchUrl} target="_blank" rel="noreferrer">Open Yuyu-tei search ↗</a>{result.tcgCornerSearchUrl && <a href={result.tcgCornerSearchUrl} target="_blank" rel="noreferrer">Open TCG Corner search ↗</a>}</span>
    </div>
    <div className="controls">
      <Filter label="Rarity" values={result.filters.rarities} selected={rarities} onChange={setRarities} />
      <Filter label="Set" values={result.filters.sets} selected={sets} onChange={setSets} />
      {hasAe && <Filter label="Source" values={['yuyutei', 'tcg-corner']} selected={sources} onChange={setSources} labels={{ yuyutei: 'JP · Yuyu-tei', 'tcg-corner': 'AE · TCG Corner' }} />}
      <label className="sort-control">Sort<select value={sort} onChange={(event) => setSort(event.target.value)}><option value="low">Lowest price</option><option value="high">Highest price</option><option value="rarity">Rarity</option><option value="set">Set</option></select></label>
      <button className="clear" type="button" onClick={() => { clear(setRarities); clear(setSets); clear(setSources); setSort('low') }}>Clear all filters</button>
    </div>
    <div className="results-line"><strong>{listings.length} listing{listings.length === 1 ? '' : 's'}</strong><span>{result.warnings.join(' ')}</span></div>
    <div className="listing-list">{listings.map((listing) => <article className="listing" key={`${listing.sourceUrl}-${listing.rarity}`}>
      {listing.imageUrl ? <button className="image-button listing-image" type="button" onClick={() => onPreview({ url: listing.imageUrl!, alt: listing.setNumber || 'Card image' })}><img src={listing.imageUrl} alt="" loading="lazy" /></button> : <span className="listing-image placeholder" aria-hidden="true" />}
      <div className="listing-main"><span className="rarity">{listing.source === 'tcg-corner' ? <span className="chip source-tag">AE</span> : <span className="chip source-tag jp">JP</span>}{listing.rarity || 'Rarity unknown'}</span><strong>{listing.setNumber || 'Set number unknown'}</strong><span className="muted">{listing.setName || 'Set unknown'}{listing.condition ? ` · ${listing.condition}` : ''}{listing.inStock === false && <span className="chip out-of-stock">Out of stock</span>}</span></div>
      <div className="price-stack"><strong>{money(listing.priceIdr, 'IDR')}</strong><span>{listing.currency === 'USD' ? money(listing.priceUsd ?? null, 'USD') : money(listing.priceJpy, 'JPY')}{listing.onSale ? ' · sale' : ''}</span></div><a className="source-link" href={listing.sourceUrl || result.yuyuteiSearchUrl} target="_blank" rel="noreferrer">Source ↗</a>
    </article>)}</div>
  </section>
}
