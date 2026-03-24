import { useState, useEffect } from 'react';

export function useUrlParams(key: string, defaultValue: string) {
    const [value, setValue] = useState(() => {
        const params = new URLSearchParams(window.location.search);
        return params.get(key) || defaultValue;
    });

    useEffect(() => {
        const url = new URL(window.location.href);
        url.searchParams.set(key, value);
        window.history.replaceState(null, '', url.toString());
    }, [key, value]);

    return [value, setValue] as const;
}
