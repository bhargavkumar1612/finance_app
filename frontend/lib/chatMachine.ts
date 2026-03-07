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
            return {
                messages: event.messages,
                conversationId: event.conversationId,
                currentResponse: undefined,
                error: undefined,
            };
        }),
        assignResponse: assign(({ context, event }) => {
            if (event.type !== 'RECEIVE') return {};
            return {
                conversationId: event.conversationId,
                currentResponse: event.response,
                messages: [
                    ...context.messages,
                    {
                        id: crypto.randomUUID(),
                        role: 'user' as const,
                        text: event.userMessage,
                    },
                    {
                        id: crypto.randomUUID(),
                        role: 'assistant' as const,
                        text: event.response.data?.message as string ?? '',
                        agentResponse: event.response,
                    },
                ],
            };
        }),
        assignError: assign(({ event }) => {
            if (event.type !== 'ERROR') return {};
            return { error: event.error };
        }),
        resetContext: assign({ messages: [], currentResponse: undefined, error: undefined })
    },
    guards: {
        isConfirmation: ({ event }) => {
            if (event.type === 'RECEIVE') {
                return event.response.ui_type === 'transaction_confirm';
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
    }
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
} as any);
