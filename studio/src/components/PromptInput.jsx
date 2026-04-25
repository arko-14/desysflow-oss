import { useEffect, useState } from 'react'

const EXAMPLES = [
    'Design a scalable messaging system for 5M users',
    'Design Twitter timeline architecture',
    'Design ML inference pipeline for 1M requests/day',
    'Design a real-time ad bidding platform',
]

const WORKFLOW_STAGES = [
    'Understanding requirements',
    'Reasoning about architecture',
    'Reviewing trade-offs and edge cases',
    'Generating diagram and documentation',
]

export default function PromptInput({ onSubmit, isLoading }) {
    const [prompt, setPrompt] = useState('')
    const [activeStage, setActiveStage] = useState(0)

    useEffect(() => {
        if (!isLoading) {
            setActiveStage(0)
            return
        }

        const interval = setInterval(() => {
            setActiveStage((prev) => (prev + 1) % WORKFLOW_STAGES.length)
        }, 2400)

        return () => clearInterval(interval)
    }, [isLoading])

    const handleSubmit = () => {
        const trimmed = prompt.trim()
        if (trimmed && !isLoading) {
            onSubmit(trimmed)
        }
    }

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
            handleSubmit()
        }
    }

    return (
        <div className="prompt-panel glass-card">
            <div className="prompt-panel__header">
                <div>
                    <p className="prompt-panel__label">System Brief</p>
                    <h2 className="prompt-panel__title">Architecture input</h2>
                    <p className="prompt-panel__hint">Add goals, scale, constraints, and critical requirements.</p>
                </div>
            </div>

            <div className="prompt-panel__composer">
                <textarea
                    id="design-prompt"
                    className="prompt-panel__textarea"
                    placeholder="Example: Design an X-style post recommendation system with fanout trade-offs, ranking, abuse prevention, and sub-200ms timeline reads."
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    onKeyDown={handleKeyDown}
                    disabled={isLoading}
                />

                <div className="prompt-panel__actions">
                    <button
                        id="generate-btn"
                        className="prompt-panel__btn"
                        onClick={handleSubmit}
                        disabled={!prompt.trim() || isLoading}
                    >
                        {isLoading ? 'Running Workflow...' : 'Run Architecture Workflow'}
                    </button>

                    {isLoading && (
                        <div className="prompt-panel__stage fade-in">
                            <p className="prompt-panel__stage-title">Current stage</p>
                            <p className="prompt-panel__stage-text">{WORKFLOW_STAGES[activeStage]}</p>
                        </div>
                    )}
                </div>
            </div>

            <div className="prompt-panel__examples">
                <p className="prompt-panel__examples-title">Example prompts</p>
                <div className="prompt-panel__example-list">
                    {EXAMPLES.map((ex) => (
                        <button
                            key={ex}
                            className="prompt-panel__example"
                            onClick={() => setPrompt(ex)}
                            disabled={isLoading}
                        >
                            {ex}
                        </button>
                    ))}
                </div>
            </div>
        </div>
    )
}
