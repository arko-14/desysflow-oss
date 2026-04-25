import { useMemo } from 'react'
import ReactFlow, { Background, Controls } from 'reactflow'
import 'reactflow/dist/style.css'
import MermaidDiagram from './MermaidDiagram'

function compactLabel(label) {
    const text = String(label || '').replace(/\s+/g, ' ').trim()
    if (text.length <= 40) return text
    return `${text.slice(0, 37)}...`
}

function nodeStyle(kind) {
    const base = {
        border: '1px solid rgba(15, 23, 42, 0.24)',
        borderRadius: 10,
        background: '#ffffff',
        color: '#0f172a',
        fontSize: 12,
        fontWeight: 600,
        padding: 8,
        width: 180,
        whiteSpace: 'normal',
        lineHeight: 1.3,
    }
    if (kind === 'client') return { ...base, background: '#effaf7', borderColor: 'rgba(15, 118, 110, 0.35)' }
    if (kind === 'edge') return { ...base, background: '#eef6ff', borderColor: 'rgba(2, 132, 199, 0.38)' }
    if (kind === 'data') return { ...base, background: '#fff8ef', borderColor: 'rgba(217, 119, 6, 0.4)' }
    if (kind === 'cache') return { ...base, background: '#f5f3ff', borderColor: 'rgba(109, 40, 217, 0.35)' }
    if (kind === 'async') return { ...base, background: '#f0fdf4', borderColor: 'rgba(22, 163, 74, 0.35)' }
    return base
}

export default function ExcalidrawLikeDiagram({ spec, fallbackMermaid }) {
    const hasNodes = Array.isArray(spec?.nodes) && spec.nodes.length > 0
    const hasEdges = Array.isArray(spec?.edges) && spec.edges.length > 0

    const { nodes, edges } = useMemo(() => {
        if (!hasNodes) return { nodes: [], edges: [] }

        const sourceNodes = spec.nodes.slice(0, 20)
        const rfNodes = sourceNodes.map((node, idx) => ({
            id: String(node.id || `n${idx + 1}`),
            data: { label: compactLabel(node.label || node.id || `Node ${idx + 1}`) },
            position: {
                x: 80 + (idx % 4) * 260,
                y: 70 + Math.floor(idx / 4) * 150,
            },
            style: nodeStyle(String(node.kind || 'service')),
        }))

        const ids = new Set(rfNodes.map((n) => n.id))
        const rfEdges = (Array.isArray(spec.edges) ? spec.edges : [])
            .slice(0, 30)
            .filter((e) => ids.has(String(e.from)) && ids.has(String(e.to)))
            .map((edge, idx) => ({
                id: `e-${idx}`,
                source: String(edge.from),
                target: String(edge.to),
                label: edge.label ? String(edge.label) : undefined,
                type: 'smoothstep',
                style: { stroke: '#64748b', strokeWidth: 2 },
            }))

        return { nodes: rfNodes, edges: rfEdges }
    }, [spec, hasNodes])

    if (!hasNodes || !hasEdges) {
        return <MermaidDiagram code={fallbackMermaid} />
    }

    return (
        <div className="excalidraw-like">
            <ReactFlow
                nodes={nodes}
                edges={edges}
                fitView
                fitViewOptions={{ padding: 0.3 }}
                minZoom={0.35}
                maxZoom={2}
                proOptions={{ hideAttribution: true }}
            >
                <Background gap={24} color="rgba(15,23,42,0.07)" />
                <Controls showInteractive={false} />
            </ReactFlow>
        </div>
    )
}
