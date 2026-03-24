import React, { useEffect, useState, useCallback } from 'react';
import { createPortal } from 'react-dom';
import './Modal.css';

interface ModalProps {
    isOpen: boolean;
    title: string;
    message?: string;
    type?: 'info' | 'error' | 'confirm';
    onClose: () => void;
    onConfirm?: () => void;
    children?: React.ReactNode;
    confirmText?: string;
    cancelText?: string;
}

export const Modal: React.FC<ModalProps> = ({
    isOpen, title, message, type = 'info',
    onClose, onConfirm, children,
    confirmText = 'Confirm', cancelText = 'Cancel'
}) => {
    const [isVisible, setIsVisible] = useState(false);

    const handleEscape = useCallback((e: KeyboardEvent) => {
        if (e.key === 'Escape') onClose();
    }, [onClose]);

    useEffect(() => {
        if (isOpen) {
            setIsVisible(true);
            document.addEventListener('keydown', handleEscape);
        } else {
            const timer = setTimeout(() => setIsVisible(false), 200);
            document.removeEventListener('keydown', handleEscape);
            return () => {
                clearTimeout(timer);
                document.removeEventListener('keydown', handleEscape);
            };
        }
    }, [isOpen, handleEscape]);

    if (!isVisible && !isOpen) return null;

    const modalContent = (
        <div className={`modal-overlay ${isOpen ? 'open' : ''}`}>
            <div className="modal-container" onClick={e => e.stopPropagation()}>
                {/* Header */}
                <div className="modal-header">
                    <h3 className={`modal-title ${type}`}>
                        {title}
                    </h3>
                    <button className="modal-close-btn" onClick={onClose}>✕</button>
                </div>

                {/* Body */}
                <div className="modal-body">
                    {children || message}
                </div>

                {/* Footer */}
                {type === 'confirm' ? (
                    <div className="modal-footer">
                        <button className="btn-base btn-secondary" onClick={onClose}>
                            {cancelText}
                        </button>
                        <button
                            className="btn-base btn-primary"
                            onClick={() => { onConfirm?.(); onClose(); }}
                        >
                            {confirmText}
                        </button>
                    </div>
                ) : (
                    /* Default info behavior - hide footer if children provided (external buttons) */
                    !children && (
                        <div className="modal-footer">
                            <button
                                className="btn-base btn-primary"
                                style={type === 'error' ? { background: '#ef5350' } : {}}
                                onClick={onClose}
                            >
                                OK
                            </button>
                        </div>
                    )
                )}
            </div>
        </div>
    );

    return createPortal(modalContent, document.body);
};
