/**
 * API client for Finance Copilot backend.
 * In dev, Next.js rewrites /v1/* to http://localhost:8000/v1/*
 */

export interface AgentResponse {
    status: string;
    data: Record<string, unknown>;
    confidence?: number;
    next_suggested_actions: string[];
    ui_type?: string;
    card_payload?: Record<string, unknown>;
}

export interface ChatApiResponse {
    response: AgentResponse;
    conversation_id: string;
}

export interface LoginResponse {
    id: string;
    email: string;
}

export interface ChatSession {
    id: string;
    title: string;
    created_at: string;
    updated_at: string;
}

export interface ChatMessageEntity {
    id: string;
    session_id: string;
    role: string;
    text: string;
    agent_response: Record<string, unknown>;
    created_at: string;
}

export interface Account {
    id: string;
    account_type: string;
    name: string;
    institution?: string;
    created_at: string;
}

export interface Transaction {
    id: string;
    amount: number;
    transaction_date: string;
    merchant?: string;
    category?: string;
    source: string;
}

export interface NormalizedRow {
    amount: number;
    date: string;
    merchant?: string;
    raw_description?: string;
    reference?: string;
    confidence?: number;
    is_duplicate: boolean;
    fingerprint?: string;
    suggested_category?: string;
}

export interface ImportResponse {
    rows: NormalizedRow[];
    account_id: string;
}

export interface ImportConfirmResponse {
    inserted: number;
    errors: string[];
}

const BASE = ''; // empty = same-origin (Next.js rewrites handle proxying in dev)

async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...(init?.headers as Record<string, string> ?? {}),
    };

    try {
        const stored = localStorage.getItem('finance_user');
        if (stored) {
            const u = JSON.parse(stored);
            if (u.email) headers['X-User-Email'] = u.email;
        }
    } catch (e) { }

    const res = await fetch(BASE + path, {
        ...init,
        headers,
    });
    if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `HTTP ${res.status}`);
    }
    return res.json() as Promise<T>;
}

export async function login(email: string): Promise<LoginResponse> {
    return request<LoginResponse>('/v1/login', {
        method: 'POST',
        body: JSON.stringify({ email }),
    });
}

export async function sendChat(
    message: string,
    conversationId?: string
): Promise<ChatApiResponse> {
    return request<ChatApiResponse>('/v1/chat', {
        method: 'POST',
        body: JSON.stringify({ message, conversation_id: conversationId }),
    });
}

export async function getChatSessions(): Promise<ChatSession[]> {
    return request<ChatSession[]>('/v1/chat/sessions');
}

export async function getChatSessionMessages(sessionId: string): Promise<ChatMessageEntity[]> {
    return request<ChatMessageEntity[]>(`/v1/chat/sessions/${sessionId}`);
}

export async function getAccounts(): Promise<Account[]> {
    return request<Account[]>('/v1/accounts');
}

export async function getTransactions(): Promise<Transaction[]> {
    return request<Transaction[]>('/v1/transactions');
}

export async function uploadImport(file: File, accountId?: string): Promise<ImportResponse> {
    const fd = new FormData();
    fd.append('file', file);
    if (accountId) fd.append('account_id', accountId);

    const headers: Record<string, string> = {};
    try {
        const stored = localStorage.getItem('finance_user');
        if (stored) {
            const u = JSON.parse(stored);
            if (u.email) headers['X-User-Email'] = u.email;
        }
    } catch (e) { }

    const res = await fetch('/v1/import', { method: 'POST', body: fd, headers });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
}

export async function confirmImport(
    accountId: string,
    rows: NormalizedRow[]
): Promise<ImportConfirmResponse> {
    return request<ImportConfirmResponse>('/v1/import/confirm', {
        method: 'POST',
        body: JSON.stringify({ account_id: accountId, rows }),
    });
}
