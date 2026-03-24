import { Api } from './Api';
import { API_BASE_URL } from '../config';

/**
 * Singleton API client shared across all hooks.
 * Prevents multiple Axios instances from being created per hook.
 */
export const apiClient = new Api({ baseURL: API_BASE_URL });
