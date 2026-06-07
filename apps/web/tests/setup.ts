import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, beforeEach } from 'vitest';

beforeEach(() => {
    localStorage.clear();
    document.documentElement.dataset.theme = 'paper';
    document.documentElement.dataset.density = 'comfortable';
});

afterEach(() => {
    cleanup();
});
