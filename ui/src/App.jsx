import { useEffect, useRef, useState } from 'react'
import {
  checkHealth,
  deleteConversation,
  getConversation,
  getOperationStatus,
  listConversations,
  startDesignAsync,
  startFollowUpAsync,
} from './api'
import LoadingState from './components/LoadingState'
import MermaidDiagram from './components/MermaidDiagram'
import NonTechnicalDoc from './components/NonTechnicalDoc'
import TechDocument from './components/TechDocument'

const ARTIFACT_TABS = [
  { key: 'diagram', label: 'Diagram' },
  { key: 'technical', label: 'Technical Doc' },
  { key: 'nontechnical', label: 'Non-Tech Doc' },
]

const SAMPLE_PROMPTS = [
  'Design a local-first product that turns code into architecture docs for small engineering teams.',
  'Design a collaborative workflow system for internal operations with audit trails and approvals.',
  'Design an event-driven support platform that balances reliability, cost, and operator clarity.',
]

function buildArtifacts(source) {
  const payload = source?.latest_result || source || {}
  return {
    mermaidCode: payload.mermaid_code || '',
    technicalDoc: payload.system_design_doc || {},
    nonTechnicalDoc: payload.non_technical_doc || {},
    warnings: payload.warnings || [],
  }
}

function hasOutputData(artifacts) {
  return Boolean(
    artifacts.mermaidCode ||
      Object.keys(artifacts.technicalDoc || {}).length ||
      Object.keys(artifacts.nonTechnicalDoc || {}).length,
  )
}

function buildRequestPrompt({
  prompt,
  preferredLanguage,
  diagramStyle,
  reportStyle,
  cloudTarget,
  searchMode,
}) {
  return [
    prompt,
    '',
    'Workspace preferences:',
    `- Preferred implementation language: ${preferredLanguage}`,
    `- Diagram style: ${diagramStyle}`,
    `- Report depth: ${reportStyle}`,
    `- Cloud target: ${cloudTarget}`,
    `- Web search mode: ${searchMode}`,
    '- Product rule: return one clean technical document and one non-technical project brief.',
    '- Product rule: avoid splitting the UI into repeated HLD and LLD views.',
  ].join('\n')
}

function ConversationMessage({ item }) {
  const roleLabel = item.role === 'user' ? 'You' : 'DesysFlow'
  return (
    <article className={`message-card message-card--${item.role}`}>
      <div className="message-card__meta">
        <span className="message-card__role">{roleLabel}</span>
      </div>
      <p className="message-card__content">{item.content}</p>
    </article>
  )
}

export default function App() {
  const [model, setModel] = useState('loading')
  const [sessionId, setSessionId] = useState('')
  const [prompt, setPrompt] = useState('')
  const [preferredLanguage, setPreferredLanguage] = useState('Python')
  const [diagramStyle, setDiagramStyle] = useState('balanced')
  const [reportStyle, setReportStyle] = useState('balanced')
  const [cloudTarget, setCloudTarget] = useState('local')
  const [searchMode, setSearchMode] = useState('auto')
  const [chatHistory, setChatHistory] = useState([])
  const [artifacts, setArtifacts] = useState(buildArtifacts(null))
  const [activeArtifact, setActiveArtifact] = useState('diagram')
  const [loading, setLoading] = useState(false)
  const [loadingMode, setLoadingMode] = useState('design')
  const [error, setError] = useState('')
  const [operationId, setOperationId] = useState('')
  const [operationStatus, setOperationStatus] = useState(null)
  const [conversations, setConversations] = useState([])
  const [loadingConversationId, setLoadingConversationId] = useState('')
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const textareaRef = useRef(null)
  const messageListRef = useRef(null)

  const hasOutput = hasOutputData(artifacts)

  useEffect(() => {
    if (!messageListRef.current) return
    messageListRef.current.scrollTop = messageListRef.current.scrollHeight
  }, [chatHistory, loading])

  const refreshConversations = async (nextSessionId = '') => {
    const data = await listConversations()
    const items = data?.conversations || []
    setConversations(items)
    if (nextSessionId && !items.some((item) => item.session_id === nextSessionId) && sessionId === nextSessionId) {
      handleReset()
    }
  }

  const loadConversation = async (nextSessionId) => {
    if (!nextSessionId || loadingConversationId === nextSessionId) return
    setError('')
    setLoadingConversationId(nextSessionId)
    try {
      const detail = await getConversation(nextSessionId)
      const payload = detail?.payload || {}
      setSessionId(detail.session_id || nextSessionId)
      setChatHistory(detail.chat_history || [])
      setPreferredLanguage(payload.preferred_language || 'Python')
      setDiagramStyle(payload.diagram_style || 'balanced')
      setArtifacts(buildArtifacts(payload))
      setActiveArtifact('diagram')
    } catch (err) {
      setError(err.message || 'Failed to load conversation.')
    } finally {
      setLoadingConversationId('')
    }
  }

  const handleReset = () => {
    setSessionId('')
    setPrompt('')
    setChatHistory([])
    setArtifacts(buildArtifacts(null))
    setActiveArtifact('diagram')
    setError('')
    setOperationId('')
    setOperationStatus(null)
    setLoading(false)
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleDeleteConversation = async (targetSessionId) => {
    if (!targetSessionId) return
    setError('')
    try {
      await deleteConversation(targetSessionId)
      if (targetSessionId === sessionId) {
        handleReset()
      }
      await refreshConversations(targetSessionId)
    } catch (err) {
      setError(err.message || 'Failed to delete conversation.')
    }
  }

  useEffect(() => {
    checkHealth()
      .then((data) => setModel([data.llm_provider, data.llm_model].filter(Boolean).join(' / ') || 'unknown'))
      .catch(() => setModel('unavailable'))

    listConversations()
      .then((data) => setConversations(data?.conversations || []))
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (!operationId) return undefined

    let cancelled = false
    let busy = false

    const poll = async () => {
      if (cancelled || busy) return
      busy = true
      try {
        const status = await getOperationStatus(operationId)
        if (cancelled) return
        setOperationStatus(status)

        if (status.status === 'completed' && status.result) {
          const result = status.result
          const nextSessionId = result.session_id || sessionId
          setSessionId(nextSessionId)
          setChatHistory(result.chat_history || [])
          setArtifacts(buildArtifacts(result))
          setActiveArtifact('diagram')
          setLoading(false)
          setOperationId('')
          setOperationStatus(null)
          await refreshConversations(nextSessionId)
        } else if (status.status === 'failed') {
          setError(status.error || 'Design generation failed.')
          setLoading(false)
          setOperationId('')
          setOperationStatus(null)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || 'Operation polling failed.')
          setLoading(false)
          setOperationId('')
          setOperationStatus(null)
        }
      } finally {
        busy = false
      }
    }

    poll()
    const timer = setInterval(poll, 900)
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [operationId, sessionId])

  const handleTextareaInput = (event) => {
    setPrompt(event.target.value)
    const el = event.target
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 220)}px`
  }

  const handleSubmit = async () => {
    const trimmed = prompt.trim()
    if (!trimmed || loading) return

    setError('')
    setLoading(true)
    setLoadingMode(sessionId ? 'followup' : 'design')

    const requestPrompt = buildRequestPrompt({
      prompt: trimmed,
      preferredLanguage,
      diagramStyle,
      reportStyle,
      cloudTarget,
      searchMode,
    })

    try {
      if (sessionId) {
        const operation = await startFollowUpAsync(sessionId, requestPrompt, preferredLanguage, diagramStyle, true)
        setOperationId(operation.operation_id || '')
      } else {
        const operation = await startDesignAsync(requestPrompt, preferredLanguage, diagramStyle)
        setOperationId(operation.operation_id || '')
      }
      setPrompt('')
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto'
      }
    } catch (err) {
      setError(err.message || 'Request failed.')
      setLoading(false)
    }
  }

  const renderArtifact = () => {
    if (activeArtifact === 'technical') {
      return <TechDocument data={artifacts.technicalDoc} />
    }
    if (activeArtifact === 'nontechnical') {
      return <NonTechnicalDoc data={artifacts.nonTechnicalDoc} />
    }
    return <MermaidDiagram code={artifacts.mermaidCode} />
  }

  return (
    <div className="app-shell">
      <aside className={`sidebar ${sidebarOpen ? 'sidebar--open' : 'sidebar--collapsed'}`}>
        <div className="sidebar__header">
          <div>
            <p className="sidebar__eyebrow">DesysFlow OSS</p>
            <h1 className="sidebar__title">Workspace</h1>
          </div>
          <button className="ghost-button" type="button" onClick={() => setSidebarOpen((value) => !value)}>
            {sidebarOpen ? 'Hide' : 'Show'}
          </button>
        </div>

        {sidebarOpen && (
          <>
            <button className="primary-button primary-button--full" type="button" onClick={handleReset} disabled={loading}>
              New chat
            </button>
            <div className="sidebar__section">
              <div className="sidebar__section-head">
                <h2>Sessions</h2>
                <span>{conversations.length}</span>
              </div>
              <div className="session-list">
                {conversations.length === 0 ? (
                  <p className="sidebar__empty">No saved sessions yet.</p>
                ) : (
                  conversations.map((item) => (
                    <button
                      key={item.session_id}
                      className={`session-item ${sessionId === item.session_id ? 'session-item--active' : ''}`}
                      onClick={() => loadConversation(item.session_id)}
                      disabled={loadingConversationId === item.session_id}
                    >
                      <span className="session-item__title">{item.title || 'Untitled session'}</span>
                      <span className="session-item__preview">{item.preview || 'Open saved conversation'}</span>
                    </button>
                  ))
                )}
              </div>
            </div>
            <div className="sidebar__meta">
              <div className="meta-card">
                <span className="meta-card__label">Model</span>
                <span className="meta-card__value">{model}</span>
              </div>
              <div className="meta-card">
                <span className="meta-card__label">Mode</span>
                <span className="meta-card__value">{sessionId ? 'Follow-up' : 'Fresh design'}</span>
              </div>
            </div>
          </>
        )}
      </aside>

      <main className="workspace-shell">
        <section className="chat-column">
          <header className="workspace-topbar">
            <div>
              <p className="workspace-topbar__eyebrow">Local design assistant</p>
              <h2>{sessionId ? 'Continue the same design thread' : 'Start with a product or system prompt'}</h2>
            </div>
            {sessionId && (
              <button className="ghost-button ghost-button--danger" type="button" onClick={() => handleDeleteConversation(sessionId)}>
                Delete session
              </button>
            )}
          </header>

          {error && <div className="notice notice--error">{error}</div>}
          {artifacts.warnings.length > 0 && <div className="notice notice--warning">{artifacts.warnings.join(' ')}</div>}

          <div className="sample-row">
            {SAMPLE_PROMPTS.map((sample) => (
              <button key={sample} className="sample-chip" type="button" onClick={() => setPrompt(sample)}>
                {sample}
              </button>
            ))}
          </div>

          <div className="message-list" ref={messageListRef}>
            {chatHistory.length === 0 && !loading ? (
              <div className="empty-chat">
                <h3>No conversation yet</h3>
                <p>Describe the product, constraints, users, scale, or business goal. DesysFlow will keep the thread local and version-aware.</p>
              </div>
            ) : (
              chatHistory
                .filter((item) => item?.content?.trim() && item.role !== 'system')
                .map((item, index) => <ConversationMessage key={`${item.role}-${index}`} item={item} />)
            )}
            {loading && <LoadingState mode={loadingMode} operation={operationStatus} />}
          </div>

          <div className="composer-panel">
            <div className="composer-controls">
              <label>
                <span>Language</span>
                <select value={preferredLanguage} onChange={(event) => setPreferredLanguage(event.target.value)}>
                  <option>Python</option>
                  <option>TypeScript</option>
                  <option>Go</option>
                  <option>Java</option>
                </select>
              </label>
              <label>
                <span>Diagram</span>
                <select value={diagramStyle} onChange={(event) => setDiagramStyle(event.target.value)}>
                  <option value="minimal">Minimal</option>
                  <option value="balanced">Balanced</option>
                  <option value="detailed">Detailed</option>
                </select>
              </label>
              <label>
                <span>Depth</span>
                <select value={reportStyle} onChange={(event) => setReportStyle(event.target.value)}>
                  <option value="minimal">Minimal</option>
                  <option value="balanced">Balanced</option>
                  <option value="detailed">Detailed</option>
                </select>
              </label>
              <label>
                <span>Cloud</span>
                <select value={cloudTarget} onChange={(event) => setCloudTarget(event.target.value)}>
                  <option value="local">Local</option>
                  <option value="aws">AWS</option>
                  <option value="gcp">GCP</option>
                  <option value="azure">Azure</option>
                  <option value="hybrid">Hybrid</option>
                </select>
              </label>
              <label>
                <span>Search</span>
                <select value={searchMode} onChange={(event) => setSearchMode(event.target.value)}>
                  <option value="auto">Auto</option>
                  <option value="on">On</option>
                  <option value="off">Off</option>
                </select>
              </label>
            </div>

            <div className="composer-box">
              <textarea
                ref={textareaRef}
                value={prompt}
                onChange={handleTextareaInput}
                placeholder="Ask for a new design or refine the current one with product, business, and technical constraints."
              />
              <button className="primary-button" type="button" onClick={handleSubmit} disabled={!prompt.trim() || loading}>
                {loading ? 'Running...' : sessionId ? 'Refine' : 'Generate'}
              </button>
            </div>
          </div>
        </section>

        <section className="artifact-column">
          <div className="artifact-header">
            <div>
              <p className="workspace-topbar__eyebrow">Artifacts</p>
              <h3>{hasOutput ? 'One clean output surface' : 'Artifacts will appear here'}</h3>
            </div>
            <div className="artifact-tabs">
              {ARTIFACT_TABS.map((tab) => (
                <button
                  key={tab.key}
                  type="button"
                  className={`artifact-tab ${activeArtifact === tab.key ? 'artifact-tab--active' : ''}`}
                  onClick={() => setActiveArtifact(tab.key)}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          <div className="artifact-surface">
            {!hasOutput && !loading ? (
              <div className="artifact-empty">
                <h4>Generate once, refine many times</h4>
                <p>The artifact panel keeps the diagram, one technical document, and one non-technical brief without duplicating HLD and LLD screens.</p>
              </div>
            ) : (
              renderArtifact()
            )}
          </div>
        </section>
      </main>
    </div>
  )
}
