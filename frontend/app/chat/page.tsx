'use client';
import { useRef, useEffect, useState } from 'react';
import { useMachine } from '@xstate/react';
import { chatMachine, type ChatMessage } from '@/lib/chatMachine';
import { sendChat, getChatSessions, getChatSessionMessages, type ChatSession } from '@/lib/api';
import CardRenderer from '@/components/cards/CardRenderer';
import styles from './Chat.module.css';

export default function ChatPage() {
    const [state, send] = useMachine(chatMachine);
    const [input, setInput] = useState('');
    const [sessions, setSessions] = useState<ChatSession[]>([]);
    const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
    const scrollRef = useRef<HTMLDivElement>(null);

    const loadSessions = async () => {
        try {
            const data = await getChatSessions();
            setSessions(data);
        } catch (e) {
            console.error('Failed to load sessions', e);
        }
    };

    useEffect(() => {
        loadSessions();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const handleLoadSession = async (id: string) => {
        setActiveSessionId(id);
        setInput('');
        try {
            const history = await getChatSessionMessages(id);
            const messages: ChatMessage[] = history.map(h => ({
                id: h.id,
                role: h.role as 'user' | 'assistant',
                text: h.text,
                agentResponse: h.agent_response ? (h.agent_response as any) : undefined
            }));
            send({ type: 'LOAD_HISTORY', messages, conversationId: id });
        } catch (e) {
            console.error('Failed to load chat history', e);
        }
    };

    const handleNewChat = () => {
        setActiveSessionId(null);
        send({ type: 'RESET' });
    };

    useEffect(() => {
        scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
    }, [state.context.messages]);

    const handleSend = async (text: string) => {
        const trimmed = text.trim();
        if (!trimmed) return;
        setInput('');
        send({ type: 'SEND', message: trimmed });

        try {
            const result = await sendChat(trimmed, state.context.conversationId);
            send({
                type: 'RECEIVE',
                response: result.response,
                conversationId: result.conversation_id,
                userMessage: trimmed,
            });
            // Refresh sessions to get updated titles or newly created sessions
            loadSessions();
            if (result.conversation_id && activeSessionId !== result.conversation_id) {
                setActiveSessionId(result.conversation_id);
            }
        } catch (err: unknown) {
            send({ type: 'ERROR', error: err instanceof Error ? err.message : String(err) });
        }
    };

    const isSending = state.matches('sending');

    const HINTS = [
        'add 500 for Swiggy',
        'what\'s my net worth?',
        'where did I spend this month?',
        'can I afford a ₹12L car?',
    ];

    return (
        <div className={styles.chatContainer}>
            <div className={styles.historySidebar}>
                <button onClick={handleNewChat} className={styles.newChatBtn}>+ New Chat</button>
                <div className={styles.historyList}>
                    {sessions.map(s => (
                        <button
                            key={s.id}
                            className={`${styles.historyItem} ${activeSessionId === s.id ? styles.active : ''}`}
                            onClick={() => handleLoadSession(s.id)}
                        >
                            {s.title || 'New Chat'}
                        </button>
                    ))}
                </div>
            </div>

            <div className={styles.chatPage}>
                <div className={styles.chatHeader}>
                    <h1 className={styles.chatTitle}>Finance Copilot</h1>
                    <p className={styles.chatSubtitle}>Ask me to add expenses, check net worth, or analyse spending</p>
                </div>

                <div className={styles.chatLog} ref={scrollRef}>
                    {state.context.messages.length === 0 ? (
                        <div className={styles.emptyState}>
                            <div className={styles.emptyIcon}>₹</div>
                            <h2>Your AI finance assistant</h2>
                            <p>Try one of these to get started:</p>
                            <div className={styles.hints}>
                                {HINTS.map(h => (
                                    <button key={h} className={`btn btn-ghost ${styles.hintBtn}`} onClick={() => handleSend(h)}>
                                        {h}
                                    </button>
                                ))}
                            </div>
                        </div>
                    ) : (
                        state.context.messages.map((msg: ChatMessage, i: number) => (
                            <div key={msg.id} className={`${styles.message} ${styles[msg.role]}`} style={{ animationDelay: `${i * 0.02}s` }}>
                                {msg.role === 'user' ? (
                                    <div className={styles.userBubble}>{msg.text}</div>
                                ) : (
                                    <div className={styles.assistantMessage}>
                                        <div className={styles.assistantAvatar}>₹</div>
                                        <div className={styles.assistantContent}>
                                            {msg.text && <p className={styles.messageText}>{msg.text}</p>}
                                            {msg.agentResponse && (
                                                <>
                                                    <CardRenderer
                                                        response={msg.agentResponse}
                                                        onAccept={() => send({ type: 'ACCEPT' })}
                                                        onReject={() => {
                                                            send({ type: 'REJECT' });
                                                            if (msg.agentResponse?.ui_type === 'transaction_confirm') {
                                                                handleSend('Add an expense');
                                                            }
                                                        }}
                                                    />
                                                    {msg.agentResponse.next_suggested_actions?.length > 0 && (
                                                        <div className={styles.suggestedActions}>
                                                            {msg.agentResponse.next_suggested_actions.map(action => (
                                                                <button
                                                                    key={action}
                                                                    className={`btn btn-ghost ${styles.actionChip}`}
                                                                    onClick={() => handleSend(action)}
                                                                    disabled={isSending}
                                                                >
                                                                    {action}
                                                                </button>
                                                            ))}
                                                        </div>
                                                    )}
                                                </>
                                            )}
                                        </div>
                                    </div>
                                )}
                            </div>
                        ))
                    )}

                    {isSending && (
                        <div className={`${styles.message} ${styles.assistant}`}>
                            <div className={styles.assistantMessage}>
                                <div className={styles.assistantAvatar}>₹</div>
                                <div className={styles.typingIndicator}>
                                    <span /><span /><span />
                                </div>
                            </div>
                        </div>
                    )}

                    {state.matches('error') && state.context.error && (
                        <div className={styles.errorBanner}>
                            ⚠ {state.context.error}
                        </div>
                    )}
                </div>

                <div className={styles.inputArea}>
                    <div className={styles.inputWrapper}>
                        <input
                            type="text"
                            className={styles.chatInput}
                            placeholder="Add 450 for Swiggy, what's my net worth…"
                            value={input}
                            onChange={e => setInput(e.target.value)}
                            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(input); } }}
                            disabled={isSending}
                            autoFocus
                            id="chat-input"
                        />
                        <button
                            className={`btn btn-primary ${styles.sendBtn}`}
                            onClick={() => handleSend(input)}
                            disabled={isSending || !input.trim()}
                            id="chat-send"
                        >
                            {isSending ? <span className="spinner" style={{ width: 16, height: 16 }} /> : '↑'}
                        </button>
                    </div>
                    <p className={styles.inputHint}>
                        Press <kbd>Enter</kbd> to send · Powered by Finance Copilot
                    </p>
                </div>
            </div>
        </div>
    );
}
