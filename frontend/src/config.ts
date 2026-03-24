export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.trim() || '';
export const WS_BASE_URL = API_BASE_URL ? API_BASE_URL.replace(/^http/, 'ws') : '';
