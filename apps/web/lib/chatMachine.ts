/**
 * XState v5 conversation state machine.
 */
import { setup, assign } from 'xstate';
import type { AgentResponse } from '@/lib/api';

export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant';
    text: string;
    agentResponse?: AgentResponse;
}

export interface ChatContext {
    messages: ChatMessage[];
    conversationId?: string;
    currentResponse?: AgentResponse;
    error?: string;
    suggestedActions: string[];
}

export type ChatEvent =
    | { type: 'SEND'; message: string }
    | { type: 'RECEIVE'; response: AgentResponse; conversationId: string; userMessage: string }
    | { type: 'ERROR'; error: string }
    | { type: 'ACCEPT' }
    | { type: 'REJECT' }
    | { type: 'RESET' }
    | { type: 'LOAD_HISTORY'; messages: ChatMessage[]; conversationId: string };

import chatMachineConfig from './chatMachineConfig.json';

export const chatMachine = setup({
    types: {
        context: {} as ChatContext,
        events: {} as ChatEvent,
    },
    actions: {
        assignHistory: assign(({ event }) => {
            if (event.type !== 'LOAD_HISTORY') return {};
            // Pick suggested actions from the last assistant message in history
            const lastAssistant = [...event.messages].reverse().find(m => m.role === 'assistant');
            const suggestedActions = lastAssistant?.agentResponse?.next_suggested_actions ?? [];
            return {
                messages: event.messages,
                conversationId: event.conversationId,
                currentResponse: undefined,
                error: undefined,
                suggestedActions,
            };
        }),
        assignUserMessage: assign(({ context, event }) => {
            if (event.type !== 'SEND') return {};
            return {
                messages: [
                    ...context.messages,
                    {
                        id: crypto.randomUUID(),
                        role: 'user' as const,
                        text: event.message,
                    }
                ]
            };
        }),
        assignResponse: assign(({ context, event }) => {
            if (event.type !== 'RECEIVE') return {};
            return {
                conversationId: event.conversationId,
                currentResponse: event.response,
                suggestedActions: event.response.next_suggested_actions ?? [],
                messages: [
                    ...context.messages,
                    {
                        id: crypto.randomUUID(),
                        role: 'assistant' as const,
                        text: event.response.data?.message as string ?? '',
                        agentResponse: event.response,
                    },
                ],
            };
        }),
        assignError: assign(({ context, event }) => {
            if (event.type !== 'ERROR') return {};
            return {
                error: undefined,
                messages: [
                    ...context.messages,
                    {
                        id: crypto.randomUUID(),
                        role: 'assistant' as const,
                        text: `⚠ Error: ${event.error}`
                    }
                ]
            };
        }),
        resetContext: assign({ messages: [], currentResponse: undefined, error: undefined, suggestedActions: [] })
    },
    guards: {
        isConfirmation: ({ event }) => {
            if (event.type === 'RECEIVE') {
                return (
                    event.response.ui_type === 'transaction_confirm'
                    && (event.response.status === 'confirm' || event.response.card_payload?.preview === true)
                );
            }
            return false;
        }
    }
}).createMachine({
    ...chatMachineConfig,
    context: {
        messages: [],
        conversationId: undefined,
        currentResponse: undefined,
        error: undefined,
        suggestedActions: [],
    }
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
} as any);
