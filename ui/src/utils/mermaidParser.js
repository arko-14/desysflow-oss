/**
 * Mermaid Flowchart → ReactFlow parser
 *
 * Parses Mermaid `flowchart TD/LR` syntax into
 * ReactFlow-compatible { nodes, edges } objects.
 */

// ── Node shape patterns ──────────────────────────────────────────────
// Matches:  A[Label]  A[(DB)]  A{Decision}  A([Rounded])  A((Circle))  A>Flag]
const NODE_SHAPES = [
    { re: /\(\[(.+?)\]\)/, shape: 'rounded' },
    { re: /\[\((.+?)\)\]/, shape: 'cylinder' },
    { re: /\(\((.+?)\)\)/, shape: 'circle' },
    { re: /\{(.+?)\}/, shape: 'diamond' },
    { re: /\[(.+?)\]/, shape: 'box' },
    { re: />(.+?)\]/, shape: 'flag' },
];

const NODE_ID_RE = '[A-Za-z][A-Za-z0-9_-]*';

// ── Edge patterns ────────────────────────────────────────────────────
// Supports:
// A -->|label| B
// A -.-> B
// A ==> B
// A -- text --> B
const EDGE_RE =
    /^(.+?)\s+(-{1,3}|={1,3}|\.{1,2}-{1,2}\.)>\s*(?:\|(.+?)\|\s*)?(.+?)\s*$/;
const EDGE_LABEL_BEFORE =
    /^(.+?)\s+--\s*(.+?)\s*-->\s*(.+?)\s*$/;

// ── Subgraph ─────────────────────────────────────────────────────────
const SUBGRAPH_RE = /^subgraph\s+(.+)$/i;
const SUBGRAPH_END_RE = /^end$/i;

/**
 * Extract a node declaration from a line fragment.
 * Returns { id, label, shape } or null.
 */
function parseNodeDecl(fragment) {
    const trimmed = fragment.trim();
    if (!trimmed) return null;

    for (const { re, shape } of NODE_SHAPES) {
        // id + shape
        const m = trimmed.match(new RegExp(`^(${NODE_ID_RE})${re.source}$`));
        if (m) {
            return { id: m[1], label: m[2].replace(/"/g, ''), shape };
        }
    }

    // Bare id (no shape) — e.g.  A
    if (new RegExp(`^${NODE_ID_RE}$`).test(trimmed)) {
        return { id: trimmed, label: trimmed, shape: 'box' };
    }
    return null;
}

/**
 * Determine edge style from the arrow string.
 */
function edgeStyle(arrow) {
    if (arrow.includes('=')) return 'thick';
    if (arrow.includes('.')) return 'dotted';
    return 'default';
}

/**
 * Main parser: Mermaid flowchart string → { nodes, edges }
 *
 * @param {string} code  Mermaid flowchart code
 * @returns {{ nodes: Array, edges: Array }}
 */
export function parseMermaid(code) {
    if (!code) return { nodes: [], edges: [] };

    const lines = code
        .split('\n')
        .flatMap((l) => l.split(';'))
        .map((l) => l.trim())
        .filter(Boolean);
    const nodesMap = new Map();  // id → { id, label, shape, group }
    const edges = [];
    let currentGroup = null;

    for (const line of lines) {
        // Skip the header
        if (/^flowchart\s/i.test(line) || /^graph\s/i.test(line)) continue;

        // Comments
        if (line.startsWith('%%')) continue;

        // Style / classDef / class lines — skip
        if (/^style\s/i.test(line) || /^classDef\s/i.test(line) || /^class\s/i.test(line)) continue;

        // Subgraph start
        const sg = line.match(SUBGRAPH_RE);
        if (sg) {
            currentGroup = sg[1].trim().replace(/["']/g, '');
            continue;
        }

        // Subgraph end
        if (SUBGRAPH_END_RE.test(line)) {
            currentGroup = null;
            continue;
        }

        // Try edge with label-before pattern:  A -- text --> B
        const eBefore = line.match(EDGE_LABEL_BEFORE);
        if (eBefore) {
            const [, src, label, tgt] = eBefore;
            registerNode(src, nodesMap, currentGroup);
            registerNode(tgt, nodesMap, currentGroup);
            edges.push({ source: cleanId(src), target: cleanId(tgt), label, style: 'default' });
            continue;
        }

        // Try standard edge:  A -->|label| B   or   A --> B
        const eMatch = line.match(EDGE_RE);
        if (eMatch) {
            const [, srcRaw, arrow, label, tgtRaw] = eMatch;
            // Mermaid fan-out syntax: A --> B & C
            const fanTargets = tgtRaw.includes('&')
                ? tgtRaw.split('&').map((t) => t.trim()).filter(Boolean)
                : [tgtRaw];

            registerNode(srcRaw, nodesMap, currentGroup);
            for (const target of fanTargets) {
                registerNode(target, nodesMap, currentGroup);
                edges.push({
                    source: cleanId(srcRaw),
                    target: cleanId(target),
                    label: label || '',
                    style: edgeStyle(arrow),
                });
            }
            continue;
        }

        // Try chained edges:  A --> B --> C
        const chainParts = line.split(/\s+(-->|==>|-.->)\s+/);
        if (chainParts.length >= 3) {
            const items = [];
            for (let i = 0; i < chainParts.length; i += 2) {
                items.push(chainParts[i]);
            }
            const arrows = [];
            for (let i = 1; i < chainParts.length; i += 2) {
                arrows.push(chainParts[i]);
            }
            if (items.length >= 2) {
                for (const item of items) {
                    registerNode(item, nodesMap, currentGroup);
                }
                for (let i = 0; i < items.length - 1; i++) {
                    edges.push({
                        source: cleanId(items[i]),
                        target: cleanId(items[i + 1]),
                        label: '',
                        style: edgeStyle(arrows[i] || '-->'),
                    });
                }
                continue;
            }
        }

        // Standalone node declaration
        const nd = parseNodeDecl(line);
        if (nd) {
            if (!nodesMap.has(nd.id)) {
                nodesMap.set(nd.id, { ...nd, group: currentGroup });
            }
        }
    }

    // ── Layout: arrange nodes in a grid ──────────────────────────────
    const nodeList = Array.from(nodesMap.values());
    const cols = Math.max(3, Math.ceil(Math.sqrt(nodeList.length)));
    const NODE_W = 200;
    const NODE_H = 100;
    const GAP_X = 280;
    const GAP_Y = 140;

    // Try to do a simple topological layout based on edges
    const nodeIds = nodeList.map((n) => n.id);
    const levels = computeLevels(nodeIds, edges);

    const nodes = nodeList.map((n, idx) => {
        const level = levels.get(n.id) ?? idx;
        const nodesAtLevel = nodeList.filter((nn) => (levels.get(nn.id) ?? 0) === level);
        const indexInLevel = nodesAtLevel.indexOf(n);
        const totalAtLevel = nodesAtLevel.length;

        return {
            id: n.id,
            type: 'custom',
            position: {
                x: (indexInLevel - (totalAtLevel - 1) / 2) * GAP_X + 400,
                y: level * GAP_Y + 60,
            },
            data: {
                label: n.label,
                shape: n.shape,
                group: n.group,
            },
        };
    });

    const rfEdges = edges.map((e, i) => ({
        id: `e-${i}`,
        source: e.source,
        target: e.target,
        label: e.label || undefined,
        animated: e.style === 'dotted',
        style: e.style === 'thick' ? { strokeWidth: 3 } : undefined,
        type: 'smoothstep',
    }));

    return { nodes, edges: rfEdges };
}

/**
 * Register a node (which might include shape declaration inline with an edge).
 */
function registerNode(raw, nodesMap, group) {
    const nd = parseNodeDecl(raw);
    if (nd && !nodesMap.has(nd.id)) {
        nodesMap.set(nd.id, { ...nd, group });
    } else if (!nd) {
        const id = cleanId(raw);
        if (id && !nodesMap.has(id)) {
            nodesMap.set(id, { id, label: id, shape: 'box', group });
        }
    }
}

/**
 * Strip shape syntax to get bare ID.
 */
function cleanId(raw) {
    const trimmed = raw.trim();
    const m = trimmed.match(new RegExp(`^(${NODE_ID_RE})`));
    return m ? m[1] : trimmed;
}

/**
 * Simple BFS-based level assignment for top-down layout.
 */
function computeLevels(nodeIds, edges) {
    const levels = new Map();
    const adj = new Map();
    const inDegree = new Map();

    for (const id of nodeIds) {
        adj.set(id, []);
        inDegree.set(id, 0);
    }

    for (const e of edges) {
        if (adj.has(e.source)) {
            adj.get(e.source).push(e.target);
        }
        if (inDegree.has(e.target)) {
            inDegree.set(e.target, inDegree.get(e.target) + 1);
        }
    }

    // Start from nodes with no incoming edges
    const queue = [];
    for (const id of nodeIds) {
        if (inDegree.get(id) === 0) {
            queue.push(id);
            levels.set(id, 0);
        }
    }

    while (queue.length > 0) {
        const curr = queue.shift();
        const currLevel = levels.get(curr);
        for (const next of (adj.get(curr) || [])) {
            const newLevel = currLevel + 1;
            if (!levels.has(next) || levels.get(next) < newLevel) {
                levels.set(next, newLevel);
            }
            inDegree.set(next, inDegree.get(next) - 1);
            if (inDegree.get(next) === 0) {
                queue.push(next);
            }
        }
    }

    // Assign remaining nodes (cycles) to level 0
    for (const id of nodeIds) {
        if (!levels.has(id)) levels.set(id, 0);
    }

    return levels;
}
