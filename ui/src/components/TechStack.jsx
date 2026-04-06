export default function TechStack({ data }) {
    if (!data || Object.keys(data).length === 0) {
        return (
            <div className="tech-stack">
                <p className="report__empty">No tech stack data available.</p>
            </div>
        )
    }

    const CATEGORY_META = {
        languages: { icon: '💻', label: 'Languages' },
        frameworks: { icon: '🧱', label: 'Frameworks' },
        databases: { icon: '🗄️', label: 'Databases' },
        message_queues: { icon: '📨', label: 'Message Queues' },
        caching: { icon: '⚡', label: 'Caching' },
        monitoring: { icon: '📈', label: 'Monitoring & Observability' },
        ci_cd: { icon: '🔄', label: 'CI/CD' },
        containerization: { icon: '🐳', label: 'Containerization' },
    }

    return (
        <div className="tech-stack fade-in">
            <div className="section-header">
                <div className="section-header__icon section-header__icon--amber">🛠️</div>
                <div className="section-header__text">
                    <h3>Tech Stack</h3>
                    <p>Technologies and tools powering the architecture</p>
                </div>
            </div>

            <div className="tech-stack__grid">
                {Object.entries(data).map(([key, items]) => {
                    const meta = CATEGORY_META[key] || { icon: '📦', label: key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) }
                    if (!Array.isArray(items) || items.length === 0) return null

                    return (
                        <div key={key} className="tech-stack__category">
                            <h4 className="tech-stack__category-title">
                                <span>{meta.icon}</span> {meta.label}
                            </h4>
                            <div className="tech-stack__tags">
                                {items.map((item, i) => (
                                    <span key={i} className="tech-tag">{item}</span>
                                ))}
                            </div>
                        </div>
                    )
                })}
            </div>
        </div>
    )
}
