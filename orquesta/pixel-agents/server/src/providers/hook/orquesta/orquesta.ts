import type { AgentEvent, HookProvider } from '../../../provider.js';

function formatToolStatus(toolName: string, input?: unknown): string {
  const inp = (input ?? {}) as Record<string, unknown>;
  const description =
    typeof inp.description === 'string'
      ? inp.description
      : typeof inp.objective === 'string'
        ? inp.objective
        : typeof inp.summary === 'string'
          ? inp.summary
          : '';

  switch (toolName) {
    case 'Plan':
      return description || 'Planificando frente';
    case 'Think':
      return description || 'Razonando';
    case 'Delegate':
      return description || 'Delegando trabajo';
    case 'Analyze':
      return description || 'Analizando';
    case 'Inspect':
      return description || 'Inspeccionando';
    case 'Report':
      return description || 'Reportando hallazgos';
    case 'Remember':
      return description || 'Escribiendo memoria';
    default:
      return description || `Usando ${toolName}`;
  }
}

function normalizeHookEvent(
  raw: Record<string, unknown>,
): { sessionId: string; event: AgentEvent } | null {
  const eventName = raw.hook_event_name;
  const sessionId = raw.session_id;
  if (typeof eventName !== 'string' || typeof sessionId !== 'string') return null;

  switch (eventName) {
    case 'SessionStart':
      return {
        sessionId,
        event: {
          kind: 'sessionStart',
          source: typeof raw.source === 'string' ? raw.source : 'orquesta',
        },
      };
    case 'SessionEnd':
      return {
        sessionId,
        event: {
          kind: 'sessionEnd',
          reason: typeof raw.reason === 'string' ? raw.reason : 'completed',
        },
      };
    case 'PreToolUse': {
      const toolName = typeof raw.tool_name === 'string' ? raw.tool_name : 'Think';
      const toolInput =
        typeof raw.tool_input === 'object' && raw.tool_input !== null
          ? (raw.tool_input as Record<string, unknown>)
          : {};
      return {
        sessionId,
        event: {
          kind: 'toolStart',
          toolId: `hook-${Date.now()}`,
          toolName,
          input: toolInput,
        },
      };
    }
    case 'PostToolUse':
    case 'PostToolUseFailure':
      return { sessionId, event: { kind: 'toolEnd', toolId: 'current' } };
    case 'Stop':
      return { sessionId, event: { kind: 'turnEnd' } };
    case 'PermissionRequest':
      return { sessionId, event: { kind: 'permissionRequest' } };
    case 'UserPromptSubmit':
      return { sessionId, event: { kind: 'userTurn' } };
    default:
      return null;
  }
}

async function installHooks(_serverUrl: string, _authToken: string): Promise<void> {
  // Orquesta posts directly to Pixel Agents over HTTP. No local hook script install needed.
}

async function uninstallHooks(): Promise<void> {
  // No-op for the local orquesta bridge provider.
}

async function areHooksInstalled(): Promise<boolean> {
  return true;
}

export const orquestaProvider: HookProvider = {
  kind: 'hook',
  id: 'orquesta',
  displayName: 'Orquesta Local',
  normalizeHookEvent,
  installHooks,
  uninstallHooks,
  areHooksInstalled,
  formatToolStatus,
  permissionExemptTools: new Set(['Report', 'Remember']),
  subagentToolNames: new Set(),
};
