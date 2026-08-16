import type { CandidatePayload } from '../../types'
import './CandidatePicker.scss'

export default function CandidatePicker({ payload, loading, onSelect, onPage }: { payload: CandidatePayload; loading: boolean; onSelect: (name: string) => void; onPage: (page: number) => void }) {
  const pagination = payload.pagination
  const page = pagination?.page ?? 0
  const totalPages = pagination?.totalPages ?? 1
  return <section className={`candidate-section ${loading ? 'is-loading' : ''}`}>
    <div className="section-heading">
      <h2>Choose the card</h2>
      <p>{loading ? 'Searching Yuyu-tei for the selected card…' : payload.candidates.length > 1 ? 'Select the exact card before checking Yuyu-tei.' : 'Did you mean one of these cards?'}</p>
      {pagination && !loading && <p className="candidate-count">{pagination.total} possible cards · page {page + 1} of {totalPages}</p>}
    </div>
    <div className="candidate-list">
      {payload.candidates.map((candidate) => <button className="candidate" key={candidate.name} type="button" disabled={loading} onClick={() => onSelect(candidate.name)}>
        {candidate.imageUrl ? <img className="candidate-image" src={candidate.imageUrl} alt="" loading="lazy" /> : <span className="candidate-image placeholder" aria-hidden="true" />}
        <span className="candidate-name"><strong>{candidate.name}</strong><small>{candidate.source}</small></span><span aria-hidden="true">↗</span>
      </button>)}
    </div>
    {pagination && totalPages > 1 && <nav className="candidate-pagination" aria-label="Candidate pages">
      <button className="page-button" type="button" disabled={loading || !pagination.hasPrevious} onClick={() => onPage(page - 1)}>Previous</button>
      <select className="page-select" value={page} disabled={loading} onChange={(event) => onPage(Number(event.target.value))} aria-label="Jump to page">
        {Array.from({ length: totalPages }, (_, index) => <option key={index} value={index}>Page {index + 1} of {totalPages}</option>)}
      </select>
      <button className="page-button" type="button" disabled={loading || !pagination.hasMore} onClick={() => onPage(page + 1)}>Next</button>
    </nav>}
  </section>
}
