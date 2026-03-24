import { useState, useEffect } from 'react';
import { HubConnectionBuilder, LogLevel } from '@microsoft/signalr';
import { API_BASE_URL } from '../config';
import { HUB_EVENTS } from '../constants';

export function useAccountSocket(onUpdate: (data: any) => void) {
    const [isConnected, setIsConnected] = useState(false);

    useEffect(() => {
        const hubUrl = `${API_BASE_URL}/hub/trade`;
        const connection = new HubConnectionBuilder()
            .withUrl(hubUrl)
            .withAutomaticReconnect()
            .configureLogging(LogLevel.Information)
            .build();

        connection.on(HUB_EVENTS.ACCOUNT_INFO, (data: any) => {
            onUpdate(data);
        });

        const startConnection = async () => {
            try {
                await connection.start();
                console.log('[SignalR] Account connection established');
                setIsConnected(true);
            } catch (err) {
                console.error('[SignalR] Connection error:', err);
                setIsConnected(false);
            }
        };

        connection.onreconnecting(() => {
            setIsConnected(false);
            console.warn('[SignalR] Account connection lost. Reconnecting...');
        });

        connection.onreconnected(() => {
            setIsConnected(true);
            console.log('[SignalR] Account connection re-established');
        });

        startConnection();

        return () => {
            connection.stop();
        };
    }, [onUpdate]);

    return { isConnected };
}
