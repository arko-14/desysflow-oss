import { useState, useMemo } from 'react'

/* ── Severity + Category detection ──────────────────────────────── */
const SEVERITY_KEYWORDS = {
    critical: ['critical', 'single point of failure', 'data loss', 'outage', 'breach', 'no authentication', 'no encryption', 'unencrypted'],
    warning: ['risk', 'bottleneck', 'concern', 'missing', 'lack', 'no monitoring', 'no observability', 'expensive', 'cost'],
    info: [],
}

const CATEGORIES = {
    scalability: ['scalab', 'bottleneck', 'throughput', 'horizontal', 'vertical', 'load', 'partition', 'shard'],
    security: ['security', 'auth', 'encrypt', 'token', 'injection', 'xss', 'cors', 'ssl', 'tls', 'firewall'],
    operational: ['operational', 'deploy', 'rollback', 'downtime', 'migration', 'config', 'ci/cd', 'complexity'],
    observability: ['observ', 'monitor', 'log', 'metric', 'tracing', 'alert', 'dashboard'],
    cost: ['cost', 'budget', 'expensive', 'pricing', 'billing', 'waste', 'optimization'],
}

const CATEGORY_META = {
    scalability: { icon: '📈', label: 'Scalability', color: '#8b5cf6' },
    security: { icon: '🔒', label: 'Security', color: '#f43f5e' },
    operational: { icon: '⚙️', label: 'Operational', color: '#f59e0b' },
    observability: { icon: '👁️', label: 'Observability', color: '#06b6d4' },
    cost: { icon: '💰', label: 'Cost', color: '#10b981' },
    general: { icon: '📋', label: 'General', color: '#64748b' },
}

const SEVERITY_META = {
    critical: { label: 'Critical', color: '#f43f5e', bg: 'rgba(244,63,94,0.12)' },
    warning: { label: 'Warning', color: '#f59e0b', bg: 'rgba(245,158,11,0.12)' },
    info: { label: 'Info', color: '#06b6d4', bg: 'rgba(6,182,212,0.12)' },
}

function detectSeverity(text) {
    const lower = text.toLowerCase()
    if (SEVERITY_KEYWORDS.critical.some((k) => lower.includes(k))) return 'critical'
    if (SEVERITY_KEYWORDS.warning.some((k) => lower.includes(k))) return 'warning'
    return 'info'
}

function detectCategory(text) {
    const lower = text.toLowerCase()
    for (const [cat, keywords] of Object.entries(CATEGORIES)) {
        if (keywords.some((k) => lower.includes(k))) return cat
    }
    return 'general'
}

function processFeedback(feedback) {
    if (!feedback || feedback.length === 0) return []
    return feedback.map((item) => ({
        text: item,
        severity: detectSeverity(item),
        category: detectCategory(item),
    }))
}

/* ── Main Component ─────────────────────────────────────────── */
export default function CriticFeedback({ feedback }) {
    const [expandedCat, setExpandedCat] = useState(null)
    const processsed = useMemo(() => processFeedback(feedback), [feedback])

    if (!feedback || feedback.length === 0) {
        return (
            <div className="critic">
                <p className="report__empty">No critic feedback provided.</p>
            </div>
        )
    }

    // Group by category
    const groups = {}
    for (const item of processsed) {
        if (!groups[item.category]) groups[item.category] = []
        groups[item.category].push(item)
    }

    // Sort: critical first
    const severityOrder = { critical: 0, warning: 1, info: 2 }
    for (const cat of Object.keys(groups)) {
        groups[cat].sort((a, b) => severityOrder[a.severity] - severityOrder[b.severity])
    }

    // Category order
    const catOrder = ['security', 'scalability', 'operational', 'observability', 'cost', 'general']
    const orderedGroups = catOrder.filter((c) => groups[c])

    // Count severities
    const counts = { critical: 0, warning: 0, info: 0 }
    for (const item of processsed) counts[item.severity]++

    return (
        <div className="critic fade-in">
            <div className="section-header">
                <div className="section-header__icon section-header__icon--rose">🔍</div>
                <div className="section-header__text">
                    <h3>Architecture Critic Review</h3>
                    <p>Principal engineer analysis — {processsed.length} findings</p>
                </div>
            </div>

            {/* Severity summary badges */}
            <div className="critic__summary">
                {Object.entries(counts).filter(([, c]) => c > 0).map(([sev, count]) => {
                    const meta = SEVERITY_META[sev]
                    return (
                        <span
                            key={sev}
                            className="critic__severity-badge"
                            style={{ background: meta.bg, color: meta.color }}
                        >
                            {count} {meta.label}
                        </span>
                    )
                })}
            </div>

            {/* Category groups */}
            <div className="critic__groups">
                {orderedGroups.map((cat) => {
                    const meta = CATEGORY_META[cat]
                    const items = groups[cat]
                    const isExpanded = expandedCat === cat || expandedCat === null

                    return (
                        <div key={cat} className="critic__group">
                            <button
                                className="critic__group-header"
                                onClick={() => setExpandedCat(expandedCat === cat ? null : cat)}
                            >
                                <span className="critic__group-icon" style={{ color: meta.color }}>
                                    {meta.icon}
                                </span>
                                <span className="critic__group-label">{meta.label}</span>
                                <span className="critic__group-count">{items.length}</span>
                                <span className={`critic__group-arrow ${isExpanded ? 'critic__group-arrow--open' : ''}`}>
                                    ▸
                                </span>
                            </button>

                            {isExpanded && (
                                <ul className="critic__items">
                                    {items.map((item, i) => {
                                        const sevMeta = SEVERITY_META[item.severity]
                                        return (
                                            <li key={i} className="critic__item">
                                                <span
                                                    className="critic__sev-dot"
                                                    style={{ background: sevMeta.color }}
                                                    title={sevMeta.label}
                                                />
                                                <p className="critic__text">{item.text}</p>
                                            </li>
                                        )
                                    })}
                                </ul>
                            )}
                        </div>
                    )
                })}
            </div>
        </div>
    )
}
