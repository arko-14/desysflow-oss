import { useState } from 'react'

const PROVIDERS = [
    {
        key: 'aws',
        label: 'AWS',
        icon: '☁️',
        color: '#ff9900',
        gradient: 'linear-gradient(135deg, rgba(255,153,0,0.15), rgba(255,153,0,0.04))',
        desc: 'Amazon Web Services',
    },
    {
        key: 'gcp',
        label: 'GCP',
        icon: '🔵',
        color: '#4285f4',
        gradient: 'linear-gradient(135deg, rgba(66,133,244,0.15), rgba(66,133,244,0.04))',
        desc: 'Google Cloud Platform',
    },
    {
        key: 'azure',
        label: 'Azure',
        icon: '🔷',
        color: '#0078d4',
        gradient: 'linear-gradient(135deg, rgba(0,120,212,0.15), rgba(0,120,212,0.04))',
        desc: 'Microsoft Azure',
    },
    {
        key: 'digitalocean',
        label: 'DigitalOcean',
        icon: '🌊',
        color: '#0080ff',
        gradient: 'linear-gradient(135deg, rgba(0,128,255,0.15), rgba(0,128,255,0.04))',
        desc: 'Simple cloud hosting',
    },
    {
        key: 'on_prem',
        label: 'On-Prem',
        icon: '🏢',
        color: '#10b981',
        gradient: 'linear-gradient(135deg, rgba(16,185,129,0.15), rgba(16,185,129,0.04))',
        desc: 'Self-hosted infrastructure',
    },
    {
        key: 'local',
        label: 'Local',
        icon: '💻',
        color: '#8b5cf6',
        gradient: 'linear-gradient(135deg, rgba(139,92,246,0.15), rgba(139,92,246,0.04))',
        desc: 'Local / Self-hosted with Docker',
    },
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

export default function CloudProviderSelector({
    cloudData,
    selectedProvider,
    onProviderSelect,
    isRedesigning,
}) {
    const providerServices = cloudData?.[selectedProvider] || {}

    return (
        <div className="cloud-selector">
            <div className="cloud-selector__header">
                <span className="cloud-selector__title">☁️ Cloud Provider</span>
                <span className="cloud-selector__subtitle">
                    Select to redesign for a provider
                </span>
            </div>

            {/* Provider Cards */}
            <div className="cloud-selector__grid">
                {PROVIDERS.map((p) => {
                    const isActive = selectedProvider === p.key
                    return (
                        <button
                            key={p.key}
                            className={`cloud-selector__card ${isActive ? 'cloud-selector__card--active' : ''}`}
                            style={{
                                background: isActive ? p.gradient : undefined,
                                borderColor: isActive ? p.color : undefined,
                            }}
                            onClick={() => onProviderSelect(p.key)}
                            disabled={isRedesigning}
                            title={p.desc}
                        >
                            <span className="cloud-selector__card-icon">{p.icon}</span>
                            <span
                                className="cloud-selector__card-label"
                                style={isActive ? { color: p.color } : undefined}
                            >
                                {p.label}
                            </span>
                            {isActive && isRedesigning && (
                                <span className="cloud-selector__spinner" />
                            )}
                        </button>
                    )
                })}
            </div>

            {/* Provider Services (shown when a provider is active and we have data) */}
            {selectedProvider && Object.keys(providerServices).length > 0 && (
                <div className="cloud-selector__services fade-in">
                    <p className="cloud-selector__services-title">
                        Services for{' '}
                        <strong style={{ color: PROVIDERS.find((p) => p.key === selectedProvider)?.color }}>
                            {PROVIDERS.find((p) => p.key === selectedProvider)?.label}
                        </strong>
                    </p>
                    <div className="cloud-selector__services-grid">
                        {SERVICE_CATEGORIES.map(({ key, icon, label }) => {
                            const items = providerServices[key]
                            if (!items || !Array.isArray(items) || items.length === 0) return null
                            return (
                                <div key={key} className="cloud-selector__svc-card">
                                    <span className="cloud-selector__svc-title">
                                        {icon} {label}
                                    </span>
                                    <div className="cloud-selector__svc-tags">
                                        {items.map((svc, i) => (
                                            <span key={i} className="cloud-tag">{svc}</span>
                                        ))}
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                </div>
            )}
        </div>
    )
}
