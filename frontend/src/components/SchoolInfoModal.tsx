import { School } from '../types'

interface SchoolInfoModalProps {
  school: School;
  onClose: () => void;
}

function SchoolInfoModal({ school, onClose }: SchoolInfoModalProps): JSX.Element {
  const reviews = school.reviews ?? []

  return (
    <div className="school-info-modal-backdrop" role="presentation" onClick={onClose}>
      <section
        className="school-info-modal"
        role="dialog"
        aria-modal="true"
        aria-label={`${school.title} information`}
        onClick={(event) => event.stopPropagation()}
      >
        <header className="school-info-header">
          <h2>{school.title}</h2>
          <button type="button" className="school-info-close-btn" onClick={onClose} aria-label="Close">
            ×
          </button>
        </header>

        <div className="school-info-content">
          <h3>AI Summary</h3>
          <p>{school.descr || 'No summary available.'}</p>

          <h3>Read real student's reviews</h3>
          {reviews.length === 0 ? (
            <p>No reviews available.</p>
          ) : (
            <div className="school-info-reviews">
              {reviews.map((review, index) => (
                <article key={`${school.id}-review-${index}`} className="school-info-review-card">
                  <p>{review.text ?? 'No review text.'}</p>
                  <p className="school-info-review-meta">
                    {review.rating != null ? `Rating: ${review.rating}` : 'Rating unavailable'}
                    {review.reviewer_type ? ` · ${review.reviewer_type}` : ''}
                    {review.date ? ` · ${review.date}` : ''}
                  </p>
                </article>
              ))}
            </div>
          )}

          <h3>Niche Page</h3>
          {school.nicheUrl ? (
            <a href={school.nicheUrl} target="_blank" rel="noreferrer">
              {school.nicheUrl}
            </a>
          ) : (
            <p>Niche URL not available.</p>
          )}
        </div>
      </section>
    </div>
  )
}

export default SchoolInfoModal
