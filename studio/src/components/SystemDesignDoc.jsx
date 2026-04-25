function ListPills({ items }) {
    if (!Array.isArray(items) || items.length === 0) return null
    return (
        <div className="pill-list">
            {items.map((item, idx) => (
                <span key={`${item}-${idx}`} className="pill">
                    {item}
                </span>
            ))}
        </div>
    )
}

function KeyValues({ data }) {
    if (!data || typeof data !== 'object' || Array.isArray(data)) return null
    const entries = Object.entries(data)
    if (entries.length === 0) return null
    return (
        <div className="kv-grid">
            {entries.map(([key, value]) => (
                <div key={key} className="kv-card">
                    <p className="kv-card__key">{key.replace(/_/g, ' ')}</p>
                    <p className="kv-card__value">{Array.isArray(value) ? value.join(', ') : String(value)}</p>
                </div>
            ))}
        </div>
    )
}

export default function SystemDesignDoc({ doc }) {
    if (!doc || Object.keys(doc).length === 0) {
        return <p className="empty">No design document generated yet.</p>
    }

    const overview = doc.overview || {}
    const architecture = doc.architecture || {}
    const implementation = doc.implementation || {}
    const platform = doc.platform || {}
    const meta = doc.meta || {}

    return (
        <div className="doc">
            <section className="doc-section">
                <h3>System Overview</h3>
                <p><strong>Preferred language:</strong> {meta.preferred_language || 'Python'}</p>
                <p>{meta.implementation_contract || 'This document should be concrete enough for a coding agent to implement.'}</p>
                <p>{overview.summary || 'No overview available.'}</p>
                <KeyValues data={overview.capacity} />
            </section>

            <section className="doc-section">
                <h3>Architecture</h3>
                <ListPills items={architecture.services} />
                <ListPills items={architecture.databases} />
                <ListPills items={architecture.message_queues} />
                <ListPills items={architecture.caching_layer} />
                <p><strong>Scaling:</strong> {architecture.scaling_strategy || 'Not specified'}</p>
                <p><strong>Availability:</strong> {architecture.availability || 'Not specified'}</p>
            </section>

            <section className="doc-section">
                <h3>Implementation</h3>
                <p><strong>API Endpoints:</strong> {Array.isArray(implementation.api_endpoints) ? implementation.api_endpoints.length : 0}</p>
                <p><strong>Data Schemas:</strong> {Array.isArray(implementation.database_schemas) ? implementation.database_schemas.length : 0}</p>
                <p><strong>Service Links:</strong> {Array.isArray(implementation.service_communication) ? implementation.service_communication.length : 0}</p>
                <p><strong>Security Controls:</strong> {Array.isArray(implementation.security) ? implementation.security.length : 0}</p>
                <KeyValues data={implementation.deployment} />
            </section>

            <section className="doc-section">
                <h3>Platform</h3>
                <KeyValues data={platform.tech_stack} />
            </section>
        </div>
    )
}
