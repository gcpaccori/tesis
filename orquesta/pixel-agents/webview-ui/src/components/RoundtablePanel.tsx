import { useEffect, useMemo, useRef, useState } from 'react';

import type { RoundtableMessage, SwarmCellState } from '../hooks/useExtensionMessages.js';
import type { OfficeState } from '../office/engine/officeState.js';
import { vscode } from '../vscodeApi.js';
import { Button } from './ui/Button.js';

interface RoundtablePanelProps {
  officeState: OfficeState;
  agents: number[];
  selectedAgent: number | null;
  providerId: string;
  chatMessages: RoundtableMessage[];
  cellStates: Record<string, SwarmCellState>;
}

type MessageFilter = 'all' | 'public' | 'internal';

function getAgentLabel(officeState: OfficeState, agentId: number): string {
  const character = officeState.characters.get(agentId);
  if (!character) return `Agente ${agentId}`;
  if (character.isTeamLead) return 'Director Liquido';
  if (character.agentName) return character.agentName;
  return `Agente ${agentId}`;
}

function formatStamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '--:--:--';
  return date.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function getAudienceLabel(audience: RoundtableMessage['audience']): string {
  if (audience === 'public') return 'PUBLICO';
  if (audience === 'internal') return 'INTERNO';
  if (audience === 'user') return 'USUARIO';
  return 'SISTEMA';
}

function getAudienceClasses(audience: RoundtableMessage['audience']): string {
  if (audience === 'user') return 'border-accent bg-active-bg';
  if (audience === 'internal') return 'border-border bg-bg-dark/90';
  if (audience === 'system') return 'border-border bg-btn-bg/70';
  return 'border-border bg-bg/90';
}

function getThreadLabel(channel: string, firstMessage: RoundtableMessage): string {
  if (channel === 'director-directo') return 'Director';
  if (channel.startsWith('manager-')) return firstMessage.speaker;
  if (channel.startsWith('avatar-')) return firstMessage.speaker;
  if (channel.startsWith('support-')) return firstMessage.speaker;
  if (firstMessage.cellId) return firstMessage.cellId;
  return channel;
}

export function RoundtablePanel({
  officeState,
  agents,
  selectedAgent,
  providerId,
  chatMessages,
  cellStates,
}: RoundtablePanelProps) {
  const [targetAgentId, setTargetAgentId] = useState<number | null>(selectedAgent);
  const [taskText, setTaskText] = useState('');
  const [filter, setFilter] = useState<MessageFilter>('public');
  const feedRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (selectedAgent !== null) {
      setTargetAgentId(selectedAgent);
    } else if (agents.length > 0 && targetAgentId === null) {
      setTargetAgentId(agents[0]);
    }
  }, [agents, selectedAgent, targetAgentId]);

  useEffect(() => {
    const feed = feedRef.current;
    if (!feed) return;
    feed.scrollTop = feed.scrollHeight;
  }, [chatMessages, filter]);

  if (providerId !== 'orquesta') return null;

  const sortedAgents = [...agents].sort((a, b) => a - b);
  const sortedCells = Object.values(cellStates).sort((a, b) => a.label.localeCompare(b.label));

  const directMessages = useMemo(
    () =>
      chatMessages.filter(
        (entry) =>
          entry.audience === 'user' ||
          entry.audience === 'public' ||
          (filter === 'all' && entry.audience === 'system'),
      ),
    [chatMessages, filter],
  );

  const foldedThreads = useMemo(() => {
    const grouped = new Map<string, RoundtableMessage[]>();
    for (const entry of chatMessages) {
      if (entry.audience !== 'internal') continue;
      const key = entry.cellId || entry.channel;
      if (!grouped.has(key)) grouped.set(key, []);
      grouped.get(key)!.push(entry);
    }
    return [...grouped.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  }, [chatMessages]);

  const canSendTask = targetAgentId !== null && taskText.trim().length > 0;
  const canControlAgent = targetAgentId !== null;

  const sendTask = () => {
    if (!canSendTask || targetAgentId === null) return;
    vscode.postMessage({
      type: 'orquestaAssignTask',
      id: targetAgentId,
      description: taskText.trim(),
    });
    setTaskText('');
  };

  return (
    <div className="absolute top-10 right-10 z-20 w-[580px] h-[840px] pixel-panel p-6 flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <span className="text-sm uppercase tracking-wide text-text-muted">Mesa Redonda</span>
          <span className="text-xs text-text-muted">
            Dos vistas claras: lo que te responden a ti y lo que se dicen entre ellos.
          </span>
        </div>
        <div className="text-right text-2xs text-text-muted">
          <div>{chatMessages.length} mensajes</div>
          <div>{sortedCells.length} celulas</div>
        </div>
      </div>

      <div className="flex gap-2 flex-wrap">
        <Button size="sm" variant={filter === 'all' ? 'active' : 'default'} onClick={() => setFilter('all')}>
          Todo
        </Button>
        <Button
          size="sm"
          variant={filter === 'public' ? 'active' : 'default'}
          onClick={() => setFilter('public')}
        >
          Te Responden
        </Button>
        <Button
          size="sm"
          variant={filter === 'internal' ? 'active' : 'default'}
          onClick={() => setFilter('internal')}
        >
          Entre Ellos
        </Button>
      </div>

      <div className="flex gap-3 overflow-x-auto pb-1">
        {sortedCells.map((cell) => (
          <div key={cell.id} className="pixel-panel min-w-[200px] p-3 flex flex-col gap-2 bg-bg-dark/70">
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs text-accent-bright">{cell.label}</span>
              <span className="text-2xs text-text-muted">{cell.phase}</span>
            </div>
            <div className="text-2xs text-text-muted">{cell.supervisor}</div>
            <div className="text-xs leading-tight">{cell.headline}</div>
            <div className="w-full h-[6px] bg-btn-bg border border-border">
              <div
                className="h-full bg-accent"
                style={{ width: `${Math.max(4, Math.min(cell.progress, 100))}%` }}
              />
            </div>
            <div className="text-2xs text-text-muted leading-tight">
              {cell.blockers.length > 0 ? `Bloqueos: ${cell.blockers.join(', ')}` : 'Sin bloqueos duros'}
            </div>
          </div>
        ))}
      </div>

      <div ref={feedRef} className="flex-1 overflow-y-auto pixel-panel bg-bg-dark/70 p-4 flex flex-col gap-4">
        {filter !== 'internal' && (
          <div className="flex flex-col gap-2">
            <span className="text-xs text-accent-bright">Lo Que Te Responden</span>
            {directMessages.length === 0 ? (
              <div className="text-xs text-text-muted">Todavia no hay respuestas dirigidas a ti.</div>
            ) : (
              directMessages.map((entry) => (
                <div key={entry.id} className={`border-2 p-3 flex flex-col gap-1 ${getAudienceClasses(entry.audience)}`}>
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-accent-bright">{entry.speaker}</span>
                      <span className="text-2xs text-text-muted">
                        {entry.role} · {getAudienceLabel(entry.audience)}
                      </span>
                    </div>
                    <span className="text-2xs text-text-muted">{formatStamp(entry.timestamp)}</span>
                  </div>
                  <div className="text-sm leading-tight">{entry.body}</div>
                </div>
              ))
            )}
          </div>
        )}

        {filter !== 'public' && (
          <div className="flex flex-col gap-2">
            <span className="text-xs text-text-muted">Lo Que Hablan Entre Ellos</span>
            {foldedThreads.length === 0 ? (
              <div className="text-xs text-text-muted">Todavia no hay conversacion interna entre agentes.</div>
            ) : (
              foldedThreads.map(([threadKey, entries]) => {
                const first = entries[0];
                const latest = entries[entries.length - 1];
                return (
                  <details key={threadKey} className="pixel-panel p-3 bg-bg/60">
                    <summary className="cursor-pointer list-none flex items-center justify-between gap-4">
                      <div className="flex flex-col gap-1">
                        <span className="text-xs text-accent-bright">{getThreadLabel(threadKey, first)}</span>
                        <span className="text-2xs text-text-muted">
                          {entries.length} mensajes · ultimo {latest.speaker}
                        </span>
                      </div>
                      <span className="text-2xs text-text-muted">{formatStamp(latest.timestamp)}</span>
                    </summary>
                    <div className="mt-3 flex flex-col gap-3">
                      {entries.map((entry) => (
                        <div
                          key={entry.id}
                          className={`border-2 p-3 flex flex-col gap-1 ${getAudienceClasses(entry.audience)}`}
                        >
                          <div className="flex items-center justify-between gap-4">
                            <div className="flex items-center gap-3">
                              <span className="text-xs text-accent-bright">{entry.speaker}</span>
                              <span className="text-2xs text-text-muted">
                                {entry.role} · {getAudienceLabel(entry.audience)}
                              </span>
                            </div>
                            <span className="text-2xs text-text-muted">{formatStamp(entry.timestamp)}</span>
                          </div>
                          <div className="text-sm leading-tight">{entry.body}</div>
                          <div className="text-2xs text-text-muted">
                            {entry.channel}
                            {entry.cellId ? ` · ${entry.cellId}` : ''}
                          </div>
                        </div>
                      ))}
                    </div>
                  </details>
                );
              })
            )}
          </div>
        )}
      </div>

      <div className="grid grid-cols-[1fr] gap-3">
        <select
          className="bg-btn-bg border-2 border-border text-text px-3 py-2"
          value={targetAgentId ?? ''}
          onChange={(event) => setTargetAgentId(Number(event.target.value))}
        >
          {sortedAgents.map((agentId) => (
            <option key={agentId} value={agentId}>
              {getAgentLabel(officeState, agentId)}
            </option>
          ))}
        </select>

        <textarea
          className="bg-btn-bg border-2 border-border text-text px-3 py-2 min-h-[94px] resize-y"
          placeholder="Elige un agente. Ese frente te responde a ti; el resto de la mesa puede discutir internamente."
          value={taskText}
          onChange={(event) => setTaskText(event.target.value)}
        />

        <div className="flex gap-2 flex-wrap">
          <Button
            size="sm"
            onClick={() =>
              setTaskText(
                'Coordina el upgrade completo con Supervisor, Especialista, Secretario, Auditor y asistentes por celula sin romper el flujo del especialista.',
              )
            }
          >
            Upgrade celulas
          </Button>
          <Button
            size="sm"
            onClick={() =>
              setTaskText(
                'Dame el estado actual de cada celula, bloqueos, tiempo restante y que se estan diciendo entre ellos.',
              )
            }
          >
            Pedir estado
          </Button>
          <Button
            size="sm"
            onClick={() =>
              setTaskText(
                'Si alguien se demora demasiado, detenlo, reencuadra el enfoque y haz que el supervisor me lo explique.',
              )
            }
          >
            Reencuadrar
          </Button>
        </div>

        <div className="flex gap-3 flex-wrap">
          <Button variant="accent" size="md" onClick={sendTask} disabled={!canSendTask}>
            Enviar a la mesa
          </Button>
          <Button
            size="md"
            onClick={() =>
              canControlAgent &&
              vscode.postMessage({ type: 'orquestaPermission', id: targetAgentId })
            }
            disabled={!canControlAgent}
          >
            Permiso
          </Button>
          <Button
            size="md"
            onClick={() =>
              canControlAgent && vscode.postMessage({ type: 'orquestaIdle', id: targetAgentId })
            }
            disabled={!canControlAgent}
          >
            Idle
          </Button>
          <Button
            size="md"
            onClick={() =>
              canControlAgent && vscode.postMessage({ type: 'orquestaClose', id: targetAgentId })
            }
            disabled={!canControlAgent}
          >
            Cerrar
          </Button>
        </div>
      </div>
    </div>
  );
}
