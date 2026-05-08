import { useEffect, useState } from 'react';

import type { OfficeState } from '../office/engine/officeState.js';
import { vscode } from '../vscodeApi.js';
import { Button } from './ui/Button.js';

interface AgentConsoleProps {
  officeState: OfficeState;
  agents: number[];
  selectedAgent: number | null;
  providerId: string;
}

function getAgentLabel(officeState: OfficeState, agentId: number): string {
  const character = officeState.characters.get(agentId);
  if (!character) return `Agente ${agentId}`;
  if (character.isTeamLead) return 'Director Liquido';
  if (character.agentName) return character.agentName;
  return `Agente ${agentId}`;
}

export function AgentConsole({
  officeState,
  agents,
  selectedAgent,
  providerId,
}: AgentConsoleProps) {
  const [targetAgentId, setTargetAgentId] = useState<number | null>(selectedAgent);
  const [taskText, setTaskText] = useState('');

  useEffect(() => {
    if (selectedAgent !== null) {
      setTargetAgentId(selectedAgent);
    } else if (agents.length > 0 && targetAgentId === null) {
      setTargetAgentId(agents[0]);
    }
  }, [agents, selectedAgent, targetAgentId]);

  if (providerId !== 'orquesta') return null;

  const sortedAgents = [...agents].sort((a, b) => a - b);
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
    <div className="absolute top-10 right-10 z-20 pixel-panel p-6 w-[360px] flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <span className="text-sm uppercase tracking-wide text-text-muted">Consola Orquesta</span>
        <span className="text-xs text-text-muted">
          Selecciona un agente y mandale trabajo directo desde el panel.
        </span>
      </div>

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
        className="bg-btn-bg border-2 border-border text-text px-3 py-2 min-h-[84px] resize-y"
        placeholder="Ejemplo: revisa la arquitectura y propon el primer frente de trabajo"
        value={taskText}
        onChange={(event) => setTaskText(event.target.value)}
      />

      <div className="flex gap-2 flex-wrap">
        <Button
          size="sm"
          onClick={() =>
            setTaskText(
              'Coordina GitHub, QA, backend, frontend, base de datos, bibliotecario y grafos hasta cerrar puntos pendientes',
            )
          }
        >
          Cargar integracion
        </Button>
        <Button
          size="sm"
          onClick={() =>
            setTaskText('Dame estado, bloqueos y una nueva lectura si alguien se demora demasiado')
          }
        >
          Pedir estado
        </Button>
      </div>

      <div className="flex gap-3 flex-wrap">
        <Button variant="accent" size="md" onClick={sendTask} disabled={!canSendTask}>
          Mandar tarea
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
          onClick={() => canControlAgent && vscode.postMessage({ type: 'orquestaIdle', id: targetAgentId })}
          disabled={!canControlAgent}
        >
          Idle
        </Button>
        <Button
          size="md"
          onClick={() => canControlAgent && vscode.postMessage({ type: 'orquestaClose', id: targetAgentId })}
          disabled={!canControlAgent}
        >
          Cerrar
        </Button>
      </div>
    </div>
  );
}
