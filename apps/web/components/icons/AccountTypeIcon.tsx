'use client';

import { getAccountTypeVisual } from '@/lib/themes/accountTypes';
import AppIcon from './AppIcon';
import styles from './AccountTypeIcon.module.css';

interface AccountTypeIconProps {
    type: string;
    loanType?: string | null;
    size?: number;
    showBadge?: boolean;
    className?: string;
}

export default function AccountTypeIcon({
    type,
    loanType,
    size = 18,
    showBadge = true,
    className,
}: AccountTypeIconProps) {
    const visual = getAccountTypeVisual(type, loanType);

    if (!showBadge) {
        return (
            <AppIcon
                icon={visual.icon}
                size={size}
                color={visual.colorVar}
                className={className}
            />
        );
    }

    return (
        <span
            className={`${styles.badge} ${className ?? ''}`}
            style={{
                ['--type-color' as string]: visual.colorVar,
            }}
            aria-hidden
        >
            <AppIcon icon={visual.icon} size={size} color={visual.colorVar} />
        </span>
    );
}
