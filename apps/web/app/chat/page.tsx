'use client';
import { useRef, useEffect, useState } from 'react';
import { useMachine } from '@xstate/react';
import { Pencil, Send, Sparkles, Trash2, X } from 'lucide-react';
import { chatMachine, type ChatMessage } from '@/lib/chatMachine';
import {
    sendChat,
    getChatSessions,
    getChatSessionMessages,
    renameChatSession,
    deleteChatSession,
    checkApiHealth,
    type ChatSession,
} from '@/lib/api';
import { useLayout } from '@/lib/LayoutContext';
import { useIsMobileLayout } from '@/lib/useIsMobileLayout';
import CardRenderer from '@/components/cards/CardRenderer';
import AppIcon from '@/components/icons/AppIcon';
import styles from './Chat.module.css';

export default function ChatPage() {
    const [state, send] = useMachine(chatMachine);
    const [input, setInput] = useState('');
    const [sessions, setSessions] = useState<ChatSession[]>([]);
    const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
    const [sessionsError, setSessionsError] = useState<string | null>(null);
    const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
    const [editTitle, setEditTitle] = useState('');
    const [deleteTarget, setDeleteTarget] = useState<ChatSession | null>(null);
    const [sessionActionError, setSessionActionError] = useState<string | null>(null);
    const [sessionBusy, setSessionBusy] = useState(false);
    const [sessionsOpen, setSessionsOpen] = useState(false);
    const scrollRef = useRef<HTMLDivElement>(null);
    const renameInputRef = useRef<HTMLInputElement>(null);
    const isMobile = useIsMobileLayout();
    const { closeAppNav } = useLayout();

    const closeSessions = () => setSessionsOpen(false);

    const openSessions = () => {
        closeAppNav();
        setSessionsOpen(true);
    };

    const toggleSessions = () => {
        if (sessionsOpen) {
            closeSessions();
        } else {
            openSessions();
        }
    };

    const loadSessions = async () => {
        setSessionsError(null);
        const healthy = await checkApiHealth();
        if (!healthy) {
            setSessions([]);
            setSessionsError('Backend is offline. Run: docker compose up -d');
            return;
        }
        try {
            const data = await getChatSessions();
            setSessions(data);
        } catch (e) {
            setSessions([]);
            setSessionsError(e instanceof Error ? e.message : 'Could not load chat history');
        }
    };

    useEffect(() => {
        loadSessions();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const handleLoadSession = async (id: string) => {
        setActiveSessionId(id);
        setInput('');
        if (isMobile) closeSessions();
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
        setEditingSessionId(null);
        send({ type: 'RESET' });
        if (isMobile) closeSessions();
    };

    const startRename = (s: ChatSession, e: React.MouseEvent) => {
        e.stopPropagation();
        setEditingSessionId(s.id);
        setEditTitle(s.title || 'New Chat');
        setSessionActionError(null);
    };

    useEffect(() => {
        if (editingSessionId) {
            renameInputRef.current?.focus();
            renameInputRef.current?.select();
        }
    }, [editingSessionId]);

    const commitRename = async (sessionId: string) => {
        const title = editTitle.trim();
        if (!title) {
            setSessionActionError('Title cannot be empty');
            return;
        }
        setSessionBusy(true);
        setSessionActionError(null);
        try {
            await renameChatSession(sessionId, title);
            setEditingSessionId(null);
            await loadSessions();
        } catch (err) {
            setSessionActionError(err instanceof Error ? err.message : 'Rename failed');
        } finally {
            setSessionBusy(false);
        }
    };

    const cancelRename = () => {
        setEditingSessionId(null);
        setEditTitle('');
    };

    const runDeleteSession = async () => {
        if (!deleteTarget) return;
        setSessionBusy(true);
        setSessionActionError(null);
        try {
            await deleteChatSession(deleteTarget.id);
            if (activeSessionId === deleteTarget.id) {
                handleNewChat();
            }
            setDeleteTarget(null);
            await loadSessions();
        } catch (err) {
            setSessionActionError(err instanceof Error ? err.message : 'Delete failed');
            setDeleteTarget(null);
        } finally {
            setSessionBusy(false);
        }
    };

    useEffect(() => {
        if (!sessionsOpen) return;
        const onKeyDown = (event: KeyboardEvent) => {
            if (event.key === 'Escape') closeSessions();
        };
        document.addEventListener('keydown', onKeyDown);
        return () => document.removeEventListener('keydown', onKeyDown);
    }, [sessionsOpen]);

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
        'summarise my last year spending with a pie chart',
        'can I afford a ₹12L car?',
    ];

    return (
        <div className={styles.chatContainer}>
            {isMobile && sessionsOpen && (
                <button
                    type="button"
                    className={styles.sessionsBackdrop}
                    aria-label="Close chat sessions"
                    onClick={closeSessions}
                />
            )}
            <div
                id="chat-sessions-drawer"
                className={`${styles.historySidebar} ${isMobile && sessionsOpen ? styles.historySidebarOpen : ''}`}
                aria-hidden={isMobile && !sessionsOpen ? true : undefined}
            >
                <button type="button" onClick={handleNewChat} className={styles.newChatBtn}>+ New Chat</button>
                {sessionsError && (
                    <div className={styles.sessionsError}>
                        <p>{sessionsError}</p>
                        <button type="button" className={styles.retryBtn} onClick={() => loadSessions()}>
                            Retry
                        </button>
                    </div>
                )}
                {sessionActionError && (
                    <p className={styles.sessionActionError}>{sessionActionError}</p>
                )}
                <div className={styles.historyList}>
                    {sessions.map(s => (
                        <div
                            key={s.id}
                            className={`${styles.historyRow} ${activeSessionId === s.id ? styles.active : ''}`}
                        >
                            {editingSessionId === s.id ? (
                                <input
                                    ref={renameInputRef}
                                    className={styles.renameInput}
                                    value={editTitle}
                                    disabled={sessionBusy}
                                    onChange={(e) => setEditTitle(e.target.value)}
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter') {
                                            e.preventDefault();
                                            void commitRename(s.id);
                                        }
                                        if (e.key === 'Escape') cancelRename();
                                    }}
                                    onBlur={() => {
                                        if (editTitle.trim()) void commitRename(s.id);
                                        else cancelRename();
                                    }}
                                />
                            ) : (
                                <>
                                    <button
                                        type="button"
                                        className={styles.historyItem}
                                        onClick={() => handleLoadSession(s.id)}
                                    >
                                        {s.title || 'New Chat'}
                                    </button>
                                    <div className={styles.historyActions}>
                                        <button
                                            type="button"
                                            className={styles.iconBtn}
                                            title="Rename"
                                            aria-label="Rename chat"
                                            disabled={sessionBusy}
                                            onClick={(e) => startRename(s, e)}
                                        >
                                            <AppIcon icon={Pencil} size={14} />
                                        </button>
                                        <button
                                            type="button"
                                            className={`${styles.iconBtn} ${styles.iconBtnDanger}`}
                                            title="Delete"
                                            aria-label="Delete chat"
                                            disabled={sessionBusy}
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                setDeleteTarget(s);
                                                setSessionActionError(null);
                                            }}
                                        >
                                            <AppIcon icon={Trash2} size={14} />
                                        </button>
                                    </div>
                                </>
                            )}
                        </div>
                    ))}
                </div>
            </div>

            {deleteTarget && (
                <div className={styles.modalBackdrop} role="dialog" aria-modal="true">
                    <div className={styles.modal}>
                        <h2 className={styles.modalTitle}>Delete chat?</h2>
                        <p className={styles.modalText}>
                            “{deleteTarget.title || 'New Chat'}” and all its messages will be removed permanently.
                        </p>
                        <div className={styles.modalActions}>
                            <button
                                type="button"
                                className="btn btn-ghost"
                                disabled={sessionBusy}
                                onClick={() => setDeleteTarget(null)}
                            >
                                Cancel
                            </button>
                            <button
                                type="button"
                                className="btn btn-primary"
                                style={{ background: 'var(--danger, #dc2626)' }}
                                disabled={sessionBusy}
                                onClick={() => void runDeleteSession()}
                            >
                                {sessionBusy ? 'Deleting…' : 'Delete'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            <div className={styles.chatPage}>
                <div className={styles.chatHeader}>
                    <div className={styles.chatHeaderRow}>
                        {isMobile && (
                            <button
                                id="chat-sessions-toggle"
                                type="button"
                                className={styles.sessionsToggleBtn}
                                aria-label="Open chat sessions"
                                aria-expanded={sessionsOpen}
                                aria-controls="chat-sessions-drawer"
                                onClick={toggleSessions}
                            >
                                Sessions
                            </button>
                        )}
                        <div className={styles.chatHeaderText}>
                            <h1 className={styles.chatTitle}>Finance Copilot</h1>
                            <p className={styles.chatSubtitle}>Ask me to add expenses, check net worth, or analyse spending</p>
                        </div>
                    </div>
                </div>

                <div className={styles.chatLog} ref={scrollRef}>
                    {state.context.messages.length === 0 ? (
                        <div className={styles.emptyState}>
                            <div className={styles.emptyIcon}>
                                <AppIcon icon={Sparkles} size={28} color="var(--accent)" />
                            </div>
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
                                        <div className={styles.assistantAvatar}>
                                            <AppIcon icon={Sparkles} size={16} color="white" />
                                        </div>
                                        <div className={styles.assistantContent}>
                                            {msg.text && <p className={styles.messageText}>{msg.text}</p>}
                                            {msg.agentResponse && (
                                                <CardRenderer
                                                    response={msg.agentResponse}
                                                    onAccept={() => handleSend('confirm')}
                                                    onReject={() => handleSend('cancel')}
                                                />
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
                                <div className={styles.assistantAvatar}>
                                    <AppIcon icon={Sparkles} size={16} color="white" />
                                </div>
                                <div className={styles.typingIndicator}>
                                    <span /><span /><span />
                                </div>
                            </div>
                        </div>
                    )}


                </div>

                {/* Contextual Quick-Action Chips */}
                <div className={styles.suggestionTray}>
                    {(state.context.suggestedActions?.length > 0 ? state.context.suggestedActions : HINTS).map(action => (
                        <button
                            key={action}
                            className={styles.suggestionChip}
                            onClick={() => handleSend(action)}
                            disabled={isSending}
                        >
                            {action}
                        </button>
                    ))}
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
                            {isSending ? (
                                <span className="spinner" style={{ width: 16, height: 16 }} />
                            ) : (
                                <AppIcon icon={Send} size={16} color="white" />
                            )}
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
