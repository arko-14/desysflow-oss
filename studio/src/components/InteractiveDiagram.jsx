import { useMemo } from 'react'
import dagre from 'dagre'
import ReactFlow, {
    Background,
    Controls,
    MiniMap,
    useNodesState,
    useEdgesState,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { parseMermaid } from '../utils/mermaidParser'
import MermaidDiagram from './MermaidDiagram'

/* ── Custom Node Component ──────────────────────────────────── */
const SHAPE_STYLES = {
    box: { borderRadius: '10px' },
    rounded: { borderRadius: '24px' },
    cylinder: { borderRadius: '10px', borderBottom: '3px solid var(--accent-cyan)' },
    circle: { borderRadius: '50%', width: 80, height: 80, padding: '8px' },
    diamond: { borderRadius: '4px', transform: 'rotate(0deg)' },
    flag: { borderRadius: '4px 16px 16px 4px' },
}

function compactLabel(label) {
    const text = String(label || '').replace(/\s+/g, ' ').trim()
    if (text.length <= 44) return text
    return `${text.slice(0, 41)}...`
}

function CustomNode({ data }) {
    const shapeStyle = SHAPE_STYLES[data.shape] || SHAPE_STYLES.box

    return (
        <div
            className="rf-custom-node"
            style={shapeStyle}
            title={data.label}
        >
            <span className="rf-custom-node__label">{compactLabel(data.label)}</span>
            {data.group && (
                <span className="rf-custom-node__group">{data.group}</span>
            )}
        </div>
    )
}

const nodeTypes = { custom: CustomNode }

/* ── Main Component ─────────────────────────────────────────── */
export default function InteractiveDiagram({ code }) {
    const { nodes: initialNodes, edges: initialEdges } = useMemo(() => {
        const parsed = parseMermaid(code)
        if (!parsed.nodes.length) return parsed

        const g = new dagre.graphlib.Graph()
        g.setGraph({ rankdir: 'TB', nodesep: 34, ranksep: 78, marginx: 16, marginy: 16 })
        g.setDefaultEdgeLabel(() => ({}))

        parsed.nodes.forEach((node) => {
            g.setNode(node.id, { width: 180, height: 64 })
        })
        parsed.edges.forEach((edge) => {
            g.setEdge(edge.source, edge.target)
        })

        dagre.layout(g)

        const laidOutNodes = parsed.nodes.map((node) => {
            const placed = g.node(node.id)
            if (!placed) return node
            return {
                ...node,
                position: {
                    x: placed.x - 90,
                    y: placed.y - 32,
                },
            }
        })

        return { nodes: laidOutNodes, edges: parsed.edges }
    }, [code])

    const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
    const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)

    // Reset when code changes
    useMemo(() => {
        setNodes(initialNodes)
        setEdges(initialEdges)
    }, [initialNodes, initialEdges])

    if (!code) {
        return (
            <div className="diagram-canvas">
                <p className="diagram-canvas__empty">No diagram code available.</p>
            </div>
        )
    }

    if (initialNodes.length === 0) {
        return (
            <div className="diagram-canvas">
                <p className="diagram-canvas__empty">
                    Could not parse diagram. The Mermaid syntax may need review.
                </p>
            </div>
        )
    }

    // If parser cannot recover any edge, use native Mermaid render fallback
    // so the user still sees the full connected diagram.
    if (initialEdges.length === 0) {
        return <MermaidDiagram code={code} />
    }

    return (
        <div className="interactive-diagram fade-in">
            <div className="interactive-diagram__header">
                <div className="section-header">
                    <div className="section-header__icon section-header__icon--purple">📊</div>
                    <div className="section-header__text">
                        <h3>System Architecture</h3>
                        <p>Interactive — drag nodes, scroll to zoom, pan the canvas</p>
                    </div>
                </div>
            </div>

            <div className="interactive-diagram__canvas">
                <ReactFlow
                    nodes={nodes}
                    edges={edges}
                    onNodesChange={onNodesChange}
                    onEdgesChange={onEdgesChange}
                    nodeTypes={nodeTypes}
                    fitView
                    fitViewOptions={{ padding: 0.3 }}
                    minZoom={0.2}
                    maxZoom={3}
                    defaultEdgeOptions={{
                        type: 'smoothstep',
                        animated: false,
                        style: { stroke: '#94a3b8', strokeWidth: 2 },
                    }}
                    proOptions={{ hideAttribution: true }}
                >
                    <Background
                        color="rgba(15, 23, 42, 0.08)"
                        gap={24}
                        size={1}
                    />
                    <Controls
                        showInteractive={false}
                        className="rf-controls"
                    />
                    <MiniMap
                        nodeColor={() => '#0284c7'}
                        maskColor="rgba(241, 245, 249, 0.6)"
                        className="rf-minimap"
                    />
                </ReactFlow>
            </div>
        </div>
    )
}
