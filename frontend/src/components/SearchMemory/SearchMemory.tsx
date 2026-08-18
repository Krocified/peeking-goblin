import type { SavedSearch } from '../../types'
import './SearchMemory.scss'

export default function SearchMemory({ compact, showBookmarks, onToggle, history, bookmarks, onClearHistory, onClearBookmarks, onRun, onRemoveBookmark }: { compact: boolean; showBookmarks: boolean; onToggle: () => void; history: SavedSearch[]; bookmarks: SavedSearch[]; onClearHistory: () => void; onClearBookmarks: () => void; onRun: (saved: SavedSearch) => void; onRemoveBookmark: (saved: SavedSearch) => void }) {
  if (!history.length && !bookmarks.length) return null
  const item = (saved: SavedSearch, removable = false) => <li key={`${saved.query}-${saved.title}-${saved.includeAe}`}>
    <button type="button" onClick={() => onRun(saved)}>{saved.query}{saved.includeAe && <span>AE</span>}</button>
    {removable && <button className="memory-remove" type="button" onClick={() => onRemoveBookmark(saved)} aria-label={`Remove ${saved.query} bookmark`}>×</button>}
  </li>
  if (compact) return <section className="search-memory compact" aria-label="Saved searches">
    {bookmarks.length > 0 && <>
      <button className="memory-toggle" type="button" aria-expanded={showBookmarks} onClick={onToggle}>{showBookmarks ? 'Hide saved' : `Show saved · ${bookmarks.length}`}</button>
      {showBookmarks && <div><div className="memory-heading"><p className="eyebrow">Bookmarks</p><button type="button" onClick={onClearBookmarks}>Clear</button></div><ul>{bookmarks.map((saved) => item(saved, true))}</ul></div>}
    </>}
  </section>
  return <section className="search-memory" aria-label="Saved searches">
    {bookmarks.length > 0 && <div><div className="memory-heading"><p className="eyebrow">Bookmarks</p><button type="button" onClick={onClearBookmarks}>Clear</button></div><ul>{bookmarks.map((saved) => item(saved, true))}</ul></div>}
    {history.length > 0 && <div><div className="memory-heading"><p className="eyebrow">Recent searches</p><button type="button" onClick={onClearHistory}>Clear</button></div><ul>{history.map((saved) => item(saved))}</ul></div>}
  </section>
}
