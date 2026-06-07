import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import UserMenu from '@/components/UserMenu';

const pushMock = vi.fn();

vi.mock('next/navigation', () => ({
    useRouter: () => ({ push: pushMock }),
}));

describe('UserMenu', () => {
    it('opens menu and shows Settings and Log out', async () => {
        const user = userEvent.setup();
        const onLogout = vi.fn();

        render(
            <UserMenu
                username="testuser"
                initial="T"
                onLogout={onLogout}
            />,
        );

        expect(screen.queryByRole('menu')).not.toBeInTheDocument();

        await user.click(document.getElementById('user-menu-trigger')!);

        expect(screen.getByRole('menu')).toBeInTheDocument();
        expect(screen.getByRole('menuitem', { name: 'Settings' })).toBeInTheDocument();
        expect(screen.getByRole('menuitem', { name: 'Log out' })).toBeInTheDocument();
    });

    it('navigates to settings from menu', async () => {
        const user = userEvent.setup();
        pushMock.mockClear();

        render(
            <UserMenu
                username="testuser"
                initial="T"
                onLogout={vi.fn()}
            />,
        );

        await user.click(document.getElementById('user-menu-trigger')!);
        await user.click(screen.getByRole('menuitem', { name: 'Settings' }));

        expect(pushMock).toHaveBeenCalledWith('/settings');
    });

    it('calls onLogout from menu', async () => {
        const user = userEvent.setup();
        const onLogout = vi.fn();

        render(
            <UserMenu
                username="testuser"
                initial="T"
                onLogout={onLogout}
            />,
        );

        await user.click(document.getElementById('user-menu-trigger')!);
        await user.click(screen.getByRole('menuitem', { name: 'Log out' }));

        expect(onLogout).toHaveBeenCalled();
    });
});
