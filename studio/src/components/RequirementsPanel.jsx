export default function RequirementsPanel({ data }) {
    if (!data || Object.keys(data).length === 0) {
        return (
            <div className="requirements">
                <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem' }}>
                    No requirements data available.
                </p>
            </div>
        )
    }

    const formatLabel = (key) =>
        key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())

    return (
        <div className="requirements fade-in">
            <div className="section-header">
                <div className="section-header__icon section-header__icon--purple">📋</div>
                <div className="section-header__text">
                    <h3>Extracted Requirements</h3>
                    <p>Structured requirements from your design prompt</p>
                </div>
            </div>

            <div className="requirements__grid">
                {Object.entries(data).map(([key, value]) => (
                    <div key={key} className="req-card">
                        <p className="req-card__label">{formatLabel(key)}</p>
                        {Array.isArray(value) ? (
                            <ul className="req-card__list">
                                {value.length > 0 ? (
                                    value.map((item, i) => <li key={i}>{item}</li>)
                                ) : (
                                    <li style={{ color: 'var(--text-muted)' }}>None specified</li>
                                )}
                            </ul>
                        ) : (
                            <p className="req-card__value">{String(value)}</p>
                        )}
                    </div>
                ))}
            </div>
        </div>
    )
}
