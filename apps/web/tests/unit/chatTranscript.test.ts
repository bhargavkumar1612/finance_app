import { describe, expect, it } from 'vitest';

import { formatChatTranscript } from '@/lib/chatTranscript';
import type { ChatMessage } from '@/lib/chatMachine';

describe('formatChatTranscript', () => {
    it('formats user and assistant turns with trace metadata', () => {
        const messages: ChatMessage[] = [
            { id: '1', role: 'user', text: 'Can I afford an emi of 20k' },
            {
                id: '2',
                role: 'assistant',
                text: 'Safe EMI estimate ready.',
                agentResponse: {
                    status: 'success',
                    data: {
                        message: 'Safe EMI estimate ready.',
                        agent_trace: {
                            route: 'keyword',
                            tool: 'compute_affordability',
                            intent: 'affordability_check',
                        },
                    },
                    next_suggested_actions: [],
                    ui_type: 'affordability_result',
                    card_payload: { message: 'Safe EMI estimate ready.' },
                },
            },
        ];

        const out = formatChatTranscript(messages, { conversationId: 'abc-123' });
        expect(out).toContain('Conversation: abc-123');
        expect(out).toContain('[User]');
        expect(out).toContain('Can I afford an emi of 20k');
        expect(out).toContain('[Assistant]');
        expect(out).toContain('route=keyword');
        expect(out).toContain('tool=compute_affordability');
        expect(out).toContain('[Card: affordability_result]');
    });
});
