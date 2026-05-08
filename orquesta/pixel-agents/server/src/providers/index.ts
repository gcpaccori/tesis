/**
 * Provider registry: re-exports all bundled providers.
 *
 * Adding a new CLI provider:
 *   1. Create `server/src/providers/hook/<cli>/<cli>.ts` implementing HookProvider.
 *      (File-based and stream-based provider types will land when the first such
 *       provider ships.)
 *   2. Add an export line below.
 *
 * The adapter (VS Code extension, standalone CLI, etc.) imports from here rather
 * than reaching into each provider directory directly.
 */

import type { HookProvider } from '../provider.js';

import { claudeProvider } from './hook/claude/claude.js';
import { orquestaProvider } from './hook/orquesta/orquesta.js';

export { claudeProvider, orquestaProvider };

const providersById: Record<string, HookProvider> = {
  [orquestaProvider.id]: orquestaProvider,
  [claudeProvider.id]: claudeProvider,
};

const defaultProviderId = process.env.PIXEL_AGENTS_PROVIDER || orquestaProvider.id;

export function getProviderById(providerId: string): HookProvider {
  return providersById[providerId] ?? orquestaProvider;
}

export function getDefaultProvider(): HookProvider {
  return getProviderById(defaultProviderId);
}
