interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  loading: boolean;
}

function SearchBar({ value, onChange, onSubmit, loading }: SearchBarProps): JSX.Element {
  return (
    <form
      className="input-box"
      onSubmit={(event) => {
        event.preventDefault()
        onSubmit()
      }}
    >
      <span aria-hidden="true">🔎</span>
      <input
        id="search-input"
        placeholder="Describe your dream school (e.g. warm weather, big sports culture)"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-label="Search for schools"
      />
      <button type="submit" disabled={loading} className="search-submit-btn">
        {loading ? 'Searching...' : 'Search'}
      </button>
    </form>
  )
}

export default SearchBar
