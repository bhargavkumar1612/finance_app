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

export type AccountType = 'bank' | 'credit_card' | 'wallet' | 'cash';

export interface Account {
    id: string;
    user_id?: string;
    account_type: AccountType;
    name: string;
    institution?: string | null;
    credit_limit?: number | null;
    currency?: string;
    parent_account_id?: string | null;
    transaction_count?: number;
    created_at?: string;
}

export interface CreateAccountRequest {
    account_type: AccountType;
    name: string;
    institution?: string;
    credit_limit?: number;
    currency?: string;
    parent_account_id?: string;
}

export interface UpdateAccountRequest {
    name?: string;
    institution?: string | null;
    account_type?: AccountType;
    credit_limit?: number | null;
    currency?: string;
    parent_account_id?: string | null;
}

export interface Transaction {
    id: string;
    amount: number;
    transaction_date: string;
    account_id: string;
    account_name?: string;
    account_type?: string;
    currency?: string;
    merchant?: string;
    category?: string;
    subcategory?: string;
    raw_description?: string;
    source: string;
    nw_impact?: string;
}

export interface CreateTransactionRequest {
    amount: number;
    transaction_date: string;
    account_id: string;
    currency?: string;
    merchant?: string;
    category?: string;
    raw_description?: string;
}

export interface UpdateTransactionRequest {
    amount?: number;
    transaction_date?: string;
    merchant?: string;
    category?: string;
    raw_description?: string;
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
    suggested_nw_impact?: string;
    nw_impact?: string;
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

function authHeaders(extra?: Record<string, string>): Record<string, string> {
    const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...extra,
    };
    try {
        const stored = localStorage.getItem('finance_user');
        if (stored) {
            const u = JSON.parse(stored);
            if (u.email) headers['X-User-Email'] = u.email;
        }
    } catch {
        /* ignore */
    }
    return headers;
}

function formatApiError(status: number, text: string): string {
    if (
        status === 500 &&
        (!text || text === 'Internal Server Error' || text.includes('Internal Server Error'))
    ) {
        return 'Backend is unavailable. Start the full stack: docker compose up -d';
    }
    try {
        const parsed = JSON.parse(text) as { detail?: string | unknown };
        if (typeof parsed.detail === 'string') return parsed.detail;
        if (parsed.detail) return JSON.stringify(parsed.detail);
    } catch {
        /* plain text body */
    }
    return text || `HTTP ${status}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
    let res: Response;
    try {
        res = await fetch(BASE + path, {
            ...init,
            headers: authHeaders(init?.headers as Record<string, string> | undefined),
        });
    } catch {
        throw new Error('Cannot reach the API. Run: docker compose up -d');
    }
    if (!res.ok) {
        const text = await res.text();
        throw new Error(formatApiError(res.status, text));
    }
    if (res.status === 204) {
        return undefined as T;
    }
    const text = await res.text();
    if (!text) {
        return undefined as T;
    }
    return JSON.parse(text) as T;
}

export async function checkApiHealth(): Promise<boolean> {
    try {
        const res = await fetch(BASE + '/health');
        return res.ok;
    } catch {
        return false;
    }
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

export async function renameChatSession(sessionId: string, title: string): Promise<ChatSession> {
    return request<ChatSession>(`/v1/chat/sessions/${sessionId}`, {
        method: 'PATCH',
        body: JSON.stringify({ title }),
    });
}

export async function deleteChatSession(sessionId: string): Promise<void> {
    await request<void>(`/v1/chat/sessions/${sessionId}`, { method: 'DELETE' });
}

export async function getAccounts(): Promise<Account[]> {
    return request<Account[]>('/v1/accounts');
}

export async function createAccount(data: CreateAccountRequest): Promise<Account> {
    return request<Account>('/v1/accounts', {
        method: 'POST',
        body: JSON.stringify(data),
    });
}

export async function updateAccount(id: string, data: UpdateAccountRequest): Promise<Account> {
    return request<Account>(`/v1/accounts/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
    });
}

export async function deleteAccount(id: string): Promise<void> {
    await request<void>(`/v1/accounts/${id}`, { method: 'DELETE' });
}

export async function getTransactions(limit = 500): Promise<Transaction[]> {
    return request<Transaction[]>(`/v1/transactions?limit=${limit}`);
}

export async function deleteTransaction(id: string): Promise<void> {
    await request<void>(`/v1/transactions/${id}`, { method: 'DELETE' });
}

export interface BulkDeleteTransactionsResponse {
    deleted: number;
    not_found: string[];
}

export async function bulkDeleteTransactions(ids: string[]): Promise<BulkDeleteTransactionsResponse> {
    return request<BulkDeleteTransactionsResponse>('/v1/transactions/bulk-delete', {
        method: 'POST',
        body: JSON.stringify({ ids }),
    });
}

export interface DeleteAllTransactionsResponse {
    deleted: number;
}

export async function deleteAllTransactions(): Promise<DeleteAllTransactionsResponse> {
    return request<DeleteAllTransactionsResponse>('/v1/transactions/delete-all', {
        method: 'POST',
        body: JSON.stringify({}),
    });
}

export async function createTransaction(data: CreateTransactionRequest): Promise<Transaction> {
    return request<Transaction>('/v1/transactions', {
        method: 'POST',
        body: JSON.stringify(data),
    });
}

export async function updateTransaction(id: string, data: UpdateTransactionRequest): Promise<Transaction> {
    return request<Transaction>(`/v1/transactions/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
    });
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

    let res: Response;
    try {
        res = await fetch('/v1/import', { method: 'POST', body: fd, headers });
    } catch {
        throw new Error('Cannot reach the API. Run: docker compose up -d');
    }
    if (!res.ok) {
        const text = await res.text();
        throw new Error(formatApiError(res.status, text));
    }
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
