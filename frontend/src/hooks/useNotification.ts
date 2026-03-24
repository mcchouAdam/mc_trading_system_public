import { useState } from 'react';

export type ModalType = 'info' | 'error' | 'confirm';

export interface ModalState {
    open: boolean;
    title: string;
    message: string;
    type: ModalType;
    onConfirm?: () => void;
}

export function useNotification() {
    const [modal, setModal] = useState<ModalState | null>(null);

    const notify = (title: string, message: string, type: ModalType = 'info', onConfirm?: () => void) => {
        setModal({ open: true, title, message, type, onConfirm });
    };

    const closeNotification = () => {
        setModal(prev => prev ? { ...prev, open: false } : null);
    };

    return { modal, setModal, notify, closeNotification };
}
