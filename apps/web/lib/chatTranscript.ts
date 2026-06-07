import type { AgentResponse } from '@/lib/api';
import type { ChatMessage } from '@/lib/chatMachine';

function formatAgentMeta(response?: AgentResponse): string {
    if (!response) return '';
    const parts: string[] = [];
    if (response.ui_type) parts.push(`ui=${response.ui_type}`);
    const trace = response.data?.agent_trace as Record<string, unknown> | undefined;
    if (trace?.route) parts.push(`route=${String(trace.route)}`);
    if (trace?.tool) parts.push(`tool=${String(trace.tool)}`);
    if (trace?.intent) parts.push(`intent=${String(trace.intent)}`);
    if (trace?.model) parts.push(`model=${String(trace.model)}`);
    return parts.length ? ` (${parts.join(' · ')})` : '';
}

function formatCardSummary(response?: AgentResponse): string | null {
    if (!response?.ui_type || response.ui_type === 'message_only') return null;
    const payload = response.card_payload ?? {};
    const message = typeof payload.message === 'string' ? payload.message : null;
    if (message) return `[Card: ${response.ui_type}] ${message}`;
    return `[Card: ${response.ui_type}]`;
}

function formatTraceThinking(response?: AgentResponse): string | null {
    const trace = response?.data?.agent_trace as Record<string, unknown> | undefined;
    const thinking = trace?.thinking;
    if (typeof thinking !== 'string' || !thinking.trim()) return null;
    return `[Thinking]\n${thinking.trim()}`;
}

export function formatChatTranscript(
    messages: ChatMessage[],
    options?: { conversationId?: string; title?: string },
): string {
    const lines: string[] = [
        'Finance Copilot — Chat transcript',
        `Exported: ${new Date().toISOString()}`,
    ];
    if (options?.conversationId) {
        lines.push(`Conversation: ${options.conversationId}`);
    }
    if (options?.title) {
        lines.push(`Title: ${options.title}`);
    }
    lines.push('', '---', '');

    for (const msg of messages) {
        const role = msg.role === 'user' ? 'User' : 'Assistant';
        lines.push(`[${role}]${msg.role === 'assistant' ? formatAgentMeta(msg.agentResponse) : ''}`);
        if (msg.text?.trim()) {
            lines.push(msg.text.trim());
        }
        const thinking = formatTraceThinking(msg.agentResponse);
        if (thinking) {
            lines.push(thinking);
        }
        const card = formatCardSummary(msg.agentResponse);
        if (card) {
            lines.push(card);
        }
        lines.push('');
    }

    return lines.join('\n').trimEnd() + '\n';
}
