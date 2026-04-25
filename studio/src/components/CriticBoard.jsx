const SEVERITY_ORDER = ['critical', 'warning', 'info']

export default function CriticBoard({ summary }) {
    const items = summary?.items || []
    const counts = summary?.counts || {}
    const severityCounts = counts.severity || {}

    if (!items.length) {
        return <p className="empty">No critic output generated yet.</p>
    }

    return (
        <div className="critic-board">
            <div className="critic-stats">
                {SEVERITY_ORDER.map((severity) => (
                    <div key={severity} className={`critic-stat critic-stat--${severity}`}>
                        <span className="critic-stat__value">{severityCounts[severity] || 0}</span>
                        <span className="critic-stat__label">{severity}</span>
                    </div>
                ))}
                <div className="critic-stat">
                    <span className="critic-stat__value">{counts.total || items.length}</span>
                    <span className="critic-stat__label">total</span>
                </div>
            </div>

            <div className="critic-list">
                {items.map((item, idx) => (
                    <article key={`${item.text}-${idx}`} className={`critic-item critic-item--${item.severity}`}>
                        <header>
                            <span className="critic-item__severity">{item.severity}</span>
                            <span className="critic-item__category">{item.category}</span>
                        </header>
                        <p>{item.text}</p>
                    </article>
                ))}
            </div>
        </div>
    )
}
