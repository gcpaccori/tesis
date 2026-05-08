import * as vscode from 'vscode';

import { COMMAND_EXPORT_DEFAULT_LAYOUT, COMMAND_SHOW_PANEL, VIEW_ID } from './constants.js';
import { PixelAgentsViewProvider } from './PixelAgentsViewProvider.js';

let providerInstance: PixelAgentsViewProvider | undefined;

export function activate(context: vscode.ExtensionContext) {
  console.log(`[Pixel Agents] PIXEL_AGENTS_DEBUG=${process.env.PIXEL_AGENTS_DEBUG ?? 'not set'}`);
  const provider = new PixelAgentsViewProvider(context);
  providerInstance = provider;

  context.subscriptions.push(vscode.window.registerWebviewViewProvider(VIEW_ID, provider));

  context.subscriptions.push(
    vscode.commands.registerCommand(COMMAND_SHOW_PANEL, () => {
      vscode.commands.executeCommand(`${VIEW_ID}.focus`);
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand(COMMAND_EXPORT_DEFAULT_LAYOUT, () => {
      provider.exportDefaultLayout();
    }),
  );

  if (process.env.PIXEL_AGENTS_AUTO_OPEN === '1') {
    const revealOffice = () => {
      void vscode.commands.executeCommand('workbench.view.extension.pixel-agents-panel');
      void vscode.commands.executeCommand(COMMAND_SHOW_PANEL);
      void vscode.commands.executeCommand(`${VIEW_ID}.focus`);
    };

    setTimeout(revealOffice, 600);
    setTimeout(revealOffice, 1800);
    setTimeout(revealOffice, 3200);
  }
}

export function deactivate() {
  providerInstance?.dispose();
}
