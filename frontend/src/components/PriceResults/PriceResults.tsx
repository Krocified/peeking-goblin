import { useDeferredValue, useMemo, useState } from 'react'
import type { CardResult } from '../../types'
import { money } from '../../types'
import Filter from './Filter'
import './PriceResults.scss'

export default function PriceResults({ result, rarities, sets, sort, setRarities, setSets, setSort, onPreview }: { result: CardResult; rarities: string[]; sets: string[]; sort: string; setRarities: (values: string[]) => void; setSets: (values: string[]) => void; setSort: (value: string) => void; onPreview: (preview: { url: string; alt: string }) => void }) {
  const [showText, setShowText] = useState(false)
  const deferredListings = useDeferredValue(result.listings)
  const listings = useMemo(() => deferredListings.filter((listing) => (!rarities.length || rarities.includes(listing.rarity || '')) && (!sets.length || sets.includes(listing.setName || ''))).sort((a, b) => sort === 'high' ? b.priceJpy - a.priceJpy : sort === 'rarity' ? (a.rarity || '').localeCompare(b.rarity || '') : sort === 'set' ? (a.setName || '').localeCompare(b.setName || '') : a.priceJpy - b.priceJpy), [deferredListings, rarities, sets, sort])
  const cardImage = result.card.imageUrl || result.listings.find((listing) => listing.imageUrl)?.imageUrl
  const clear = (setter: (values: string[]) => void) => setter([])
  return <section className="results-section">
    <div className="result-header">
      {cardImage && <button className="image-button card-image" type="button" onClick={() => onPreview({ url: cardImage, alt: `${result.card.canonicalName} card image` })}><img src={cardImage} alt={`${result.card.canonicalName} card image`} /></button>}
      <div className="card-identity"><p className="eyebrow">Resolved card</p><h2>{result.card.canonicalName}</h2><p className="japanese">{result.card.japaneseBaseName}</p></div>
      <div className="card-actions">{result.card.englishText && <button className="text-toggle" type="button" aria-expanded={showText} onClick={() => setShowText(!showText)}>{showText ? 'Hide text' : 'Show text'}</button>}<a className="wiki-link" href={result.card.sourceUrl} target="_blank" rel="noreferrer">Yugipedia ↗</a></div>
    </div>
    {showText && <p className="english-text">{result.card.englishText}</p>}
    <div className="meta-row"><span>{result.exchangeRate ? `1 JPY = ${result.exchangeRate.value} IDR · ${result.exchangeRate.retrievedAt}` : 'IDR rate unavailable'}</span><a href={result.yuyuteiSearchUrl} target="_blank" rel="noreferrer">Open Yuyu-tei search ↗</a></div>
    <div className="controls">
      <Filter label="Rarity" values={result.filters.rarities} selected={rarities} onChange={setRarities} />
      <Filter label="Set" values={result.filters.sets} selected={sets} onChange={setSets} />
      <label className="sort-control">Sort<select value={sort} onChange={(event) => setSort(event.target.value)}><option value="low">Lowest price</option><option value="high">Highest price</option><option value="rarity">Rarity</option><option value="set">Set</option></select></label>
      <button className="clear" type="button" onClick={() => { clear(setRarities); clear(setSets); setSort('low') }}>Clear all filters</button>
    </div>
    <div className="results-line"><strong>{listings.length} listing{listings.length === 1 ? '' : 's'}</strong><span>{result.warnings.join(' ')}</span></div>
    <div className="listing-list">{listings.map((listing) => <article className="listing" key={`${listing.sourceUrl}-${listing.rarity}`}>
      {listing.imageUrl ? <button className="image-button listing-image" type="button" onClick={() => onPreview({ url: listing.imageUrl!, alt: listing.setNumber || 'Card image' })}><img src={listing.imageUrl} alt="" loading="lazy" /></button> : <span className="listing-image placeholder" aria-hidden="true" />}
      <div className="listing-main"><span className="rarity">{listing.rarity || 'Rarity unknown'}</span><strong>{listing.setNumber || 'Set number unknown'}</strong><span className="muted">{listing.setName || 'Set unknown'}{listing.condition ? ` · ${listing.condition}` : ''}{listing.inStock === false && <span className="chip out-of-stock">Out of stock</span>}</span></div>
      <div className="price-stack"><strong>{money(listing.priceIdr, 'IDR')}</strong><span>{money(listing.priceJpy, 'JPY')}{listing.onSale ? ' · sale' : ''}</span></div><a className="source-link" href={listing.sourceUrl || result.yuyuteiSearchUrl} target="_blank" rel="noreferrer">Source ↗</a>
    </article>)}</div>
  </section>
}
