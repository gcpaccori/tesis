import { buildAppUrl, fetchJsonWithFallback } from './appUrls.js';

interface SwarmAgent {
  id: number;
  session_id: string;
  role_key: string;
  display_name: string;
  team_name: string;
  agent_name?: string;
  is_team_lead?: boolean;
  folder_name: string;
  default_tool_name: string;
  default_status: string;
}

interface SwarmBlueprint {
  team_name: string;
  mission_prompt: string;
  agents: SwarmAgent[];
  architecture?: Record<string, unknown>;
}

interface SwarmMessage {
  id: string;
  timestamp: string;
  speaker: string;
  role: string;
  body: string;
  audience: 'user' | 'public' | 'internal' | 'system';
  channel: string;
  cellId?: string;
  speakerAgentId?: number;
}

interface SwarmCellState {
  id: string;
  label: string;
  division: string;
  supervisor: string;
  phase: string;
  headline: string;
  progress: number;
  blockers: string[];
  lastUpdate: string;
  focus?: string;
}

interface SwarmToolEvent {
  agent_id: number;
  tool_name: string;
  status: string;
  state: 'active' | 'waiting' | 'idle';
}

interface SwarmBootstrapPayload {
  session_id: string;
  backend_mode: string;
  director_model: string;
  agents: SwarmAgent[];
  architecture: Record<string, unknown>;
  messages: SwarmMessage[];
  cell_states: SwarmCellState[];
  tool_events: SwarmToolEvent[];
}

interface SwarmChatPayload {
  session_id: string;
  backend_mode: string;
  director_model: string;
  director_reply: SwarmMessage;
  messages: SwarmMessage[];
  cell_states: SwarmCellState[];
  tool_events: SwarmToolEvent[];
  selected_cells: string[];
  memory_write: Record<string, unknown>;
}

type DispatchFn = (payload: Record<string, unknown>) => void;

interface BrowserCommand {
  type?: string;
  id?: number;
  description?: string;
}

let blueprint: SwarmBlueprint | null = null;
let dispatchFn: DispatchFn | null = null;
let apiBase: string | null = null;
let sessionId = '';
let bootstrapPayload: SwarmBootstrapPayload | null = null;

function emit(payload: Record<string, unknown>): void {
  dispatchFn?.(payload);
}

function randomSessionId(): string {
  return `pixel-${Math.random().toString(36).slice(2, 10)}`;
}

function ensureSessionId(): string {
  if (sessionId) return sessionId;
  const stored = window.localStorage.getItem('orquesta.sessionId');
  sessionId = stored || randomSessionId();
  window.localStorage.setItem('orquesta.sessionId', sessionId);
  return sessionId;
}

function getApiCandidates(baseUrl: string): string[] {
  const explicit = window.localStorage.getItem('orquesta.apiBase') || '';
  const localOrigin = `${window.location.protocol}//${window.location.hostname}:8310`;
  return [
    explicit,
    buildAppUrl(baseUrl, 'orquesta-api'),
    'http://127.0.0.1:8310',
    'http://localhost:8310',
    localOrigin,
  ].filter((value, index, list) => value && list.indexOf(value) === index);
}

async function tryBootstrap(candidate: string, activeSessionId: string): Promise<SwarmBootstrapPayload | null> {
  try {
    const response = await fetch(
      `${candidate.replace(/\/$/, '')}/swarm/bootstrap?session_id=${encodeURIComponent(activeSessionId)}`,
    );
    if (!response.ok) return null;
    const contentType = response.headers.get('content-type') ?? '';
    if (!contentType.includes('application/json')) return null;
    return (await response.json()) as SwarmBootstrapPayload;
  } catch {
    return null;
  }
}

async function discoverApiBase(baseUrl: string, activeSessionId: string): Promise<void> {
  const candidates = getApiCandidates(baseUrl);
  for (const candidate of candidates) {
    const payload = await tryBootstrap(candidate, activeSessionId);
    if (payload) {
      apiBase = candidate.replace(/\/$/, '');
      bootstrapPayload = payload;
      window.localStorage.setItem('orquesta.apiBase', apiBase);
      return;
    }
  }
  apiBase = null;
  bootstrapPayload = null;
}

function seedAgents(agents: SwarmAgent[]): void {
  for (const agent of agents) {
    emit({
      type: 'agentCreated',
      id: agent.id,
      folderName: agent.folder_name,
    });
    emit({
      type: 'agentTeamInfo',
      id: agent.id,
      teamName: agent.team_name,
      agentName: agent.agent_name,
      isTeamLead: agent.is_team_lead ?? false,
    });
  }
}

function applyMessages(messages: SwarmMessage[]): void {
  for (const entry of messages) {
    emit({
      type: 'orquestaChatMessage',
      entry,
    });
  }
}

function applyCellStates(cellStates: SwarmCellState[]): void {
  for (const cell of cellStates) {
    emit({
      type: 'orquestaCellState',
      cell,
    });
  }
}

function applyToolEvents(toolEvents: SwarmToolEvent[]): void {
  for (const event of toolEvents) {
    if (event.state === 'idle') {
      emit({ type: 'agentToolsClear', id: event.agent_id });
      emit({ type: 'agentStatus', id: event.agent_id, status: 'waiting' });
      continue;
    }

    emit({ type: 'agentToolsClear', id: event.agent_id });
    emit({
      type: 'agentToolStart',
      id: event.agent_id,
      toolId: `api-${event.agent_id}-${Date.now()}`,
      toolName: event.tool_name,
      status: event.status,
    });
    emit({
      type: 'agentStatus',
      id: event.agent_id,
      status: event.state === 'waiting' ? 'waiting' : 'active',
    });
  }
}

function getSeedAgents(): SwarmAgent[] {
  return bootstrapPayload?.agents ?? blueprint?.agents ?? [];
}

function selectLead(agents: SwarmAgent[]): void {
  const lead = agents.find((agent) => agent.is_team_lead);
  if (lead) {
    emit({ type: 'agentSelected', id: lead.id });
  }
}

function emitBackendWarning(): void {
  applyMessages([
    {
      id: `warning-${Date.now()}`,
      timestamp: new Date().toISOString(),
      speaker: 'Sistema',
      role: 'Bus de Eventos',
      body: 'No encuentro la API real de la orquesta en el puerto 8310. La UI queda lista, pero el chat real necesita que levantes el backend.',
      audience: 'system',
      channel: 'system',
    },
  ]);
}

async function postJson<T>(path: string, payload: Record<string, unknown>): Promise<T | null> {
  if (!apiBase) return null;
  try {
    const response = await fetch(`${apiBase}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!response.ok) return null;
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

async function sendTask(agentId: number, description: string): Promise<void> {
  const payload = await postJson<SwarmChatPayload>('/swarm/chat', {
    message: description,
    session_id: ensureSessionId(),
    target_agent_id: agentId,
  });
  if (!payload) {
    emitBackendWarning();
    return;
  }

  applyMessages(payload.messages);
  applyCellStates(payload.cell_states);
  applyToolEvents(payload.tool_events);
}

function handlePermission(agentId: number): void {
  emit({ type: 'agentToolPermission', id: agentId });
  applyMessages([
    {
      id: `perm-${agentId}-${Date.now()}`,
      timestamp: new Date().toISOString(),
      speaker: 'Sistema',
      role: 'Control',
      body: `Se marcó una petición de permiso para el agente ${agentId}.`,
      audience: 'system',
      channel: 'control',
      speakerAgentId: agentId,
    },
  ]);
}

function handleIdle(agentId: number): void {
  emit({ type: 'agentToolsClear', id: agentId });
  emit({ type: 'agentStatus', id: agentId, status: 'waiting' });
  applyMessages([
    {
      id: `idle-${agentId}-${Date.now()}`,
      timestamp: new Date().toISOString(),
      speaker: 'Sistema',
      role: 'Control',
      body: `El agente ${agentId} quedó en idle por orden tuya.`,
      audience: 'system',
      channel: 'control',
      speakerAgentId: agentId,
    },
  ]);
}

function handleClose(agentId: number): void {
  emit({ type: 'agentClosed', id: agentId });
  applyMessages([
    {
      id: `close-${agentId}-${Date.now()}`,
      timestamp: new Date().toISOString(),
      speaker: 'Sistema',
      role: 'Control',
      body: `El agente ${agentId} fue cerrado desde la mesa.`,
      audience: 'system',
      channel: 'control',
      speakerAgentId: agentId,
    },
  ]);
}

function handleBrowserCommand(event: Event): void {
  const command = (event as CustomEvent<BrowserCommand>).detail;
  if (!command?.type) return;

  if (command.type === 'orquestaAssignTask') {
    if (!command.id || !command.description) return;
    void sendTask(command.id, command.description);
    return;
  }

  if (command.type === 'orquestaPermission' && command.id) {
    handlePermission(command.id);
    return;
  }

  if (command.type === 'orquestaIdle' && command.id) {
    handleIdle(command.id);
    return;
  }

  if (command.type === 'orquestaClose' && command.id) {
    handleClose(command.id);
  }
}

export async function initBrowserSwarm(baseUrl: string): Promise<void> {
  blueprint = await fetchJsonWithFallback<SwarmBlueprint>(baseUrl, 'mock/enjambre_blueprint.json');
  await discoverApiBase(baseUrl, ensureSessionId());
  window.addEventListener('browser-post-message', handleBrowserCommand as EventListener);
}

export function seedBrowserSwarm(dispatch: DispatchFn): void {
  dispatchFn = dispatch;
  const agents = getSeedAgents();
  seedAgents(agents);
  selectLead(agents);

  if (bootstrapPayload) {
    applyMessages(bootstrapPayload.messages);
    applyCellStates(bootstrapPayload.cell_states);
    applyToolEvents(bootstrapPayload.tool_events);
    return;
  }

  emitBackendWarning();
}
