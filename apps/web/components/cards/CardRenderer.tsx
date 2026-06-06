import type { AgentResponse } from '@/lib/api';
import TransactionConfirmCard from './TransactionConfirmCard';
import MonthlySummaryCard from './MonthlySummaryCard';
import NetWorthBreakdownCard from './NetWorthBreakdownCard';
import AffordabilityCard from './AffordabilityCard';
import MessageOnlyCard from './MessageOnlyCard';

// Phase 4 Analytics Cards
import CategoryDrilldownCard from './CategoryDrilldownCard';
import SubscriptionListCard from './SubscriptionListCard';
import CashFlowSummaryCard from './CashFlowSummaryCard';
import TopExpensesListCard from './TopExpensesListCard';
import BudgetComparisonCard from './BudgetComparisonCard';
import FutureBalanceProjectionCard from './FutureBalanceProjectionCard';
import DebtPayoffPlanCard from './DebtPayoffPlanCard';
import InvestmentPieChartCard from './InvestmentPieChartCard';
import SpendingDashboardCard from './SpendingDashboardCard';
import VendorHistoryCard from './VendorHistoryCard';
import AnomalyAlertCard from './AnomalyAlertCard';
import AccountListCard from './AccountListCard';

// Dynamic card registry: maps ui_type → React component
const REGISTRY: Record<string, React.ComponentType<{ payload: Record<string, unknown>; onAccept?: () => void; onReject?: () => void }>> = {
    transaction_confirm: TransactionConfirmCard,
    monthly_summary: MonthlySummaryCard,
    spending_dashboard: SpendingDashboardCard,
    net_worth_breakdown: NetWorthBreakdownCard,
    affordability_result: AffordabilityCard,
    message_only: MessageOnlyCard,

    // Phase 4 Tools
    category_drilldown: CategoryDrilldownCard,
    subscription_list: SubscriptionListCard,
    recurring_bill_list: SubscriptionListCard,
    cash_flow_summary: CashFlowSummaryCard,
    top_expenses_list: TopExpensesListCard,
    budget_comparison: BudgetComparisonCard,
    future_balance_projection: FutureBalanceProjectionCard,
    debt_payoff_plan: DebtPayoffPlanCard,
    investment_pie_chart: InvestmentPieChartCard,
    vendor_history: VendorHistoryCard,
    anomaly_alert: AnomalyAlertCard,
    account_list: AccountListCard,
};

interface CardProps {
    response: AgentResponse;
    onAccept?: () => void;
    onReject?: () => void;
}

export default function CardRenderer({ response, onAccept, onReject }: CardProps) {
    const uiType = response.ui_type ?? 'message_only';
    const Component = REGISTRY[uiType] ?? MessageOnlyCard;
    const payload = response.card_payload ?? {};
    return <Component payload={payload} onAccept={onAccept} onReject={onReject} />;
}
