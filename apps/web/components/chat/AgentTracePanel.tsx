'use client';

import styles from './AgentTracePanel.module.css';

export interface AgentTrace {
    route?: string;
    intent?: string;
    tool?: string;
    semantic_match?: string;
    thinking?: string;
    model?: string;
    note?: string;
}

const ROUTE_LABELS: Record<string, string> = {
    keyword: 'Keyword',
    semantic: 'Semantic + LLM',
    llm_tool: 'LLM tool',
    llm_context: 'LLM context',
    llm_message: 'LLM chat',
    fallback: 'Fallback',
};

interface Props {
    trace: AgentTrace;
}

export default function AgentTracePanel({ trace }: Props) {
    const routeLabel = ROUTE_LABELS[trace.route ?? ''] ?? trace.route ?? 'Unknown';
    const toolLabel = trace.tool ?? trace.semantic_match ?? '—';

    return (
        <div className={styles.tracePanel} aria-label="Agent routing trace">
            <div className={styles.traceHeader}>
                <span className={styles.traceTitle}>Agent trace</span>
                <div className={styles.badges}>
                    <span className={styles.badgeRoute}>{routeLabel}</span>
                    {trace.tool && <span className={styles.badgeTool}>Tool: {trace.tool}</span>}
                    {!trace.tool && trace.semantic_match && (
                        <span className={styles.badgeTool}>Match: {trace.semantic_match}</span>
                    )}
                    {trace.intent && trace.intent !== 'unknown' && (
                        <span className={styles.badgeIntent}>{trace.intent}</span>
                    )}
                </div>
            </div>

            {(trace.model || trace.note) && (
                <dl className={styles.traceMeta}>
                    {trace.model && (
                        <div className={styles.traceRow}>
                            <dt>Model</dt>
                            <dd>{trace.model}</dd>
                        </div>
                    )}
                    {trace.note && (
                        <div className={styles.traceRow}>
                            <dt>Note</dt>
                            <dd>{trace.note}</dd>
                        </div>
                    )}
                </dl>
            )}

            {trace.thinking ? (
                <details className={styles.thinkingPanel} open>
                    <summary className={styles.thinkingSummary}>Thinking</summary>
                    <pre className={styles.thinkingText}>{trace.thinking}</pre>
                </details>
            ) : (
                (trace.route === 'llm_tool' || trace.route === 'llm_context' || trace.route === 'llm_message' || trace.route === 'semantic') && (
                    <p className={styles.thinkingHint}>
                        No reasoning text from this model. Use a reasoning model in OpenRouter settings to see thinking here.
                    </p>
                )
            )}
        </div>
    );
}
