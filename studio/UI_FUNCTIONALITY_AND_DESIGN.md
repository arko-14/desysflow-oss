# Archagent UI: Functionality and Design Spec

## 1. Purpose
The UI provides a workspace to:
- Capture system design prompts.
- Run architecture generation workflows.
- Visualize system architecture diagrams.
- Review generated artifacts (HLD, LLD, requirements, critic results).
- Continue the design through follow-up chat prompts.

## 2. Primary User Flows
1. User starts a new chat.
2. User enters a system design request in the composer.
3. UI sends async request and shows workflow loading state.
4. UI renders a clean artifact panel with Diagram, Technical Doc, and Non-Tech Doc.
5. User asks follow-up questions in the same session.
6. User runs critic and cloud redesign refinements.

## 3. Current Functionalities

### 3.1 Conversation Management
- `New chat` resets active session and output state.
- Sidebar lists previous conversations.
- Selecting a conversation loads:
  - chat history
  - preferred language
  - diagram style
  - latest generated artifacts
- Delete removes the active conversation.
- Backend also writes a readable session note in `./desysflow/sessions/<session_id>.md`.

### 3.2 Composer and Prompting
- Multi-line textarea for prompt input.
- Enter sends request.
- Shift+Enter creates newline.
- Prompt is enriched with context constraints:
  - preferred language
  - cloud preference
  - design tone
  - search mode
- Optional document upload (`.txt`, `.md`) included as reference context.

### 3.3 Generation + Async Polling
- New design and follow-up both run asynchronously.
- UI polls operation status until complete/failed.
- Loading states supported:
  - design
  - followup
  - critic
  - cloud
- Errors are shown in the top error banner.

### 3.4 Artifact Workspace
When results exist, UI exposes tabbed sections:
- Diagram
- Technical Doc
- Non-Tech Doc

### 3.5 Diagram Experience
- Mermaid diagram rendering.
- Pan interaction by dragging within viewport.
- Zoom controls: `+`, `-`, `Reset`.
- Scrollable viewport for large diagrams.
- Render error fallback for invalid Mermaid syntax.

### 3.6 Chat Thread Panel
- Right-side conversation pane shows chat history.
- Message roles:
  - User -> "You"
  - Assistant -> "Archagent"
- Auto-scroll to latest message.
- Empty state shown when no visible messages.

### 3.7 Critic + Cloud Actions
- `Run Critic` evaluates current design artifacts.
- Cloud provider switch can trigger cloud redesign.
- Provider options:
  - AWS
  - GCP
  - Azure
  - DigitalOcean
  - On-Prem

## 4. Layout and Structural Design

### 4.1 Global Shell
- App uses two-column shell:
  - Left: collapsible sidebar (conversations)
  - Right: main workspace

### 4.2 Main Workspace
- Topbar: title, sidebar toggle, action buttons.
- Content area:
  - Left: artifact tabs + active tab content
- Right: artifact panel
- Bottom dock: composer + controls

### 4.3 Composer Controls
Inline controls include:
- preferred language
- cloud provider
- tone/role
- search mode
- diagram style
- document upload

## 5. Visual Design System (Current)
- Font: Manrope
- Theme: light, soft blue/cyan accents
- Surfaces:
  - white and light-blue panels
  - rounded cards and chips
- Message bubbles:
  - user bubble (`--bubble-user`)
  - assistant bubble (`--bubble-assistant`)
- Diagram canvas:
  - bordered light background
  - subtle inset lines

## 6. Responsive Behavior
- Desktop: full split layout (sidebar + workspace + chat pane).
- Tablet/mobile:
  - sidebar behaves like overlay drawer
  - workspace remains scrollable
  - composer remains docked

## 7. UX/Quality Expectations
The UI should feel:
- balanced (content and chat proportions are stable)
- navigable (important actions visible without hunting)
- readable (clean spacing and typographic hierarchy)
- explorable (large diagrams must be pannable/zoomable)
- conversational (chat panel and input should feel like AI chat)

## 8. Known UX Pain Points to Fix Next
- Composer should be visually cleaner and less crowded by controls.
- Chat panel hierarchy can be improved with stronger visual grouping.
- Diagram tool area can use better discoverability (tooltips/hints).
- Mobile spacing and sticky footer behavior need polish.

## 9. Proposed Target UI Design (Next Iteration)

### 9.1 Composer Redesign
- Convert to chat-first input dock:
  - single prominent text input region
  - compact secondary controls in collapsible "Advanced" row
  - inline send button/icon
- Keep structured prompt helper text optional/toggleable.

### 9.2 Workspace Balance
- Use consistent split ratio:
  - 65% artifact pane
  - 35% chat pane
- Keep chat always visible during generation.

### 9.3 Diagram UX
- Add `Fit`, `100%`, and `Fullscreen` controls.
- Provide "drag to pan" and "scroll to zoom" tips only once.

### 9.4 Chat Experience
- Keep markdown rendering for assistant answers.
- Add timestamps and status (running/completed).
- Add retry action for failed prompts.

## 10. Component-Level Ownership
Core files:
- `studio/src/App.jsx`: shell, state, data flow, layout composition.
- `studio/src/App.css`: global styling, layout and responsive behavior.
- `studio/src/components/MermaidDiagram.jsx`: Mermaid rendering and diagram interactions.
- `studio/src/components/LoadingState.jsx`: async progress and operation feedback.
- `studio/src/components/*`: artifact-specific views.

## 11. Functional Acceptance Checklist
- Can start new design and follow-up from same composer.
- Can switch conversations and restore prior artifacts.
- Can see chat and artifact output side-by-side.
- Can pan/zoom/scroll large architecture diagrams.
- Can run critic and cloud redesign without breaking session.
- Can upload reference text documents.
- Can recover gracefully from API/rendering errors.

## 12. Implementation Notes
- All API actions are async and session-scoped.
- Workspace relies on `chat_history` and `latest_result` payloads.
- `buildArtifacts()` normalizes payload shape for rendering.
- Output tabs are shown only when artifact data exists.
- Structured session memory includes repo context, workflow summaries, errors/corrections, and worklog notes.
