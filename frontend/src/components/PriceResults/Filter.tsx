export default function Filter({ label, values, selected, onChange, labels }: { label: string; values: string[]; selected: string[]; onChange: (values: string[]) => void; labels?: Record<string, string> }) {
  const value = selected[0] ?? ''
  return <div className="filter-control">
    <label htmlFor={`${label}-filter`}>{label}</label>
    <div className="filter-field">
      <select id={`${label}-filter`} value={value} onChange={(event) => onChange(event.target.value ? [event.target.value] : [])}>
        <option value="">All</option>
        {values.map((option) => <option key={option} value={option}>{labels?.[option] ?? option}</option>)}
      </select>
      {value && <button className="filter-clear" type="button" onClick={() => onChange([])} aria-label={`Clear ${label.toLowerCase()} filter`}>×</button>}
    </div>
  </div>
}
