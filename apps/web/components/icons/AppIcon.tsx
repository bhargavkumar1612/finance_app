'use client';

import type { LucideIcon } from 'lucide-react';

interface AppIconProps {
    icon: LucideIcon;
    size?: number;
    className?: string;
    color?: string;
    strokeWidth?: number;
    'aria-hidden'?: boolean;
    'aria-label'?: string;
}

export default function AppIcon({
    icon: Icon,
    size = 18,
    className,
    color,
    strokeWidth = 2,
    'aria-hidden': ariaHidden = true,
    'aria-label': ariaLabel,
}: AppIconProps) {
    return (
        <Icon
            size={size}
            className={className}
            color={color}
            strokeWidth={strokeWidth}
            aria-hidden={ariaHidden}
            aria-label={ariaLabel}
        />
    );
}
