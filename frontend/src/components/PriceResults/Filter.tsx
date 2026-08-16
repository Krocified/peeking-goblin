export default function Filter({ label, values, selected, onChange }: { label: string; values: string[]; selected: string[]; onChange: (values: string[]) => void }) {
  const value = selected[0] ?? ''
  return <div className="filter-control">
    <label htmlFor={`${label}-filter`}>{label}</label>
    <div className="filter-field">
      <select id={`${label}-filter`} value={value} onChange={(event) => onChange(event.target.value ? [event.target.value] : [])}>
        <option value="">All</option>
        {values.map((option) => <option key={option} value={option}>{option}</option>)}
      </select>
      {value && <button className="filter-clear" type="button" onClick={() => onChange([])} aria-label={`Clear ${label.toLowerCase()} filter`}>×</button>}
    </div>
  </div>
}
