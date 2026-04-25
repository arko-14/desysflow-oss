import { useState } from 'react'

const PROVIDERS = [
    { key: 'aws', label: 'AWS', color: '#ff9900' },
    { key: 'gcp', label: 'GCP', color: '#4285f4' },
    { key: 'azure', label: 'Azure', color: '#0078d4' },
    { key: 'digitalocean', label: 'DigitalOcean', color: '#0080ff' },
    { key: 'on_prem', label: 'On-Prem', color: '#10b981' },
]

const SERVICE_CATEGORIES = [
    { key: 'compute', icon: '🖥️', label: 'Compute' },
    { key: 'database', icon: '🗄️', label: 'Database' },
    { key: 'cache', icon: '⚡', label: 'Cache' },
    { key: 'queue', icon: '📨', label: 'Queue / Messaging' },
    { key: 'storage', icon: '💾', label: 'Storage' },
    { key: 'cdn', icon: '🌐', label: 'CDN' },
    { key: 'monitoring', icon: '📈', label: 'Monitoring' },
    { key: 'networking', icon: '🔗', label: 'Networking' },
]

export default function CloudInfra({ data }) {
    const [activeProvider, setActiveProvider] = useState('aws')

    if (!data || Object.keys(data).length === 0) {
        return (
            <div className="cloud-infra">
                <p className="report__empty">No cloud infrastructure data available.</p>
            </div>
        )
    }

    const providerData = data[activeProvider] || {}

    return (
        <div className="cloud-infra fade-in">
            <div className="section-header">
                <div className="section-header__icon section-header__icon--green">☁️</div>
                <div className="section-header__text">
                    <h3>Cloud Infrastructure</h3>
                    <p>Managed service mapping across cloud providers</p>
                </div>
            </div>

            {/* Provider Tabs */}
            <div className="cloud-infra__providers">
                {PROVIDERS.map((p) => (
                    <button
                        key={p.key}
                        className={`cloud-infra__provider-btn ${activeProvider === p.key ? 'cloud-infra__provider-btn--active' : ''}`}
                        style={activeProvider === p.key ? { borderColor: p.color, color: p.color } : {}}
                        onClick={() => setActiveProvider(p.key)}
                    >
                        {p.label}
                    </button>
                ))}
            </div>

            {/* Service Grid */}
            <div className="cloud-infra__grid">
                {SERVICE_CATEGORIES.map(({ key, icon, label }) => {
                    const services = providerData[key]
                    if (!services || !Array.isArray(services) || services.length === 0) return null

                    return (
                        <div key={key} className="cloud-infra__card">
                            <h4 className="cloud-infra__card-title">
                                <span>{icon}</span> {label}
                            </h4>
                            <div className="cloud-infra__services">
                                {services.map((svc, i) => (
                                    <span key={i} className="cloud-tag">{svc}</span>
                                ))}
                            </div>
                        </div>
                    )
                })}
            </div>
        </div>
    )
}
