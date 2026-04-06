function renderItems(items) {
  if (!Array.isArray(items) || items.length === 0) {
    return <p className="doc-empty">No content available.</p>
  }
  return (
    <ul className="doc-list">
      {items.map((item, index) => (
        <li key={index}>{String(item)}</li>
      ))}
    </ul>
  )
}

export default function NonTechnicalDoc({ data }) {
  if (!data || Object.keys(data).length === 0) {
    return <p className="doc-empty">No non-technical document available yet.</p>
  }

  const deliveryShape = data.delivery_shape || {}
  const platformNotes = data.platform_notes || {}

  return (
    <div className="doc-view fade-in">
      <section className="doc-section">
        <h4>Project Summary</h4>
        <p>{data.summary || 'No summary available.'}</p>
      </section>

      <section className="doc-grid">
        <article className="doc-card">
          <h4>Business Value</h4>
          {renderItems(data.business_value || [])}
        </article>
        <article className="doc-card">
          <h4>Target Users</h4>
          {renderItems(data.target_users || [])}
        </article>
      </section>

      <section className="doc-grid">
        <article className="doc-card">
          <h4>Key Capabilities</h4>
          {renderItems(data.key_capabilities || [])}
        </article>
        <article className="doc-card">
          <h4>Delivery Shape</h4>
          <dl className="doc-facts">
            {Object.entries(deliveryShape).map(([key, value]) => (
              <div key={key} className="doc-facts__row">
                <dt>{key.replace(/_/g, ' ')}</dt>
                <dd>{String(value || 'Not specified')}</dd>
              </div>
            ))}
          </dl>
        </article>
      </section>

      <section className="doc-grid">
        <article className="doc-card">
          <h4>Go-To-Market Notes</h4>
          {renderItems(data.go_to_market_notes || [])}
        </article>
        <article className="doc-card">
          <h4>Delivery Risks</h4>
          {renderItems(data.delivery_risks || [])}
        </article>
      </section>

      <section className="doc-grid">
        <article className="doc-card">
          <h4>Future Improvements</h4>
          {renderItems(data.future_improvements || [])}
        </article>
        <article className="doc-card">
          <h4>Platform Notes</h4>
          <dl className="doc-facts">
            {Object.entries(platformNotes).map(([key, value]) => (
              <div key={key} className="doc-facts__row">
                <dt>{key.replace(/_/g, ' ')}</dt>
                <dd>{Array.isArray(value) ? value.join(', ') : String(value || 'Not specified')}</dd>
              </div>
            ))}
          </dl>
        </article>
      </section>
    </div>
  )
}
