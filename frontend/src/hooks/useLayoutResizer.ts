import { useState, useRef, useCallback, useEffect } from 'react';

export function useLayoutResizer() {
    const [topHeight, setTopHeight] = useState(65);
    const [sidebarWidth, setSidebarWidth] = useState(280);
    const [sidebarSplit, setSidebarSplit] = useState(40);
    const [openWidth, setOpenWidth] = useState(55);
    const [activeResizer, setActiveResizer] = useState<string | null>(null);

    const isResizingTop = useRef(false);
    const isResizingSidebarV = useRef(false);
    const isResizingSidebarH = useRef(false);
    const isResizingOpenPane = useRef(false);

    const handleMouseDownTop = useCallback(() => {
        isResizingTop.current = true;
        setActiveResizer('top-bottom');
        document.body.style.cursor = 'row-resize';
    }, []);

    const handleMouseDownSidebarV = useCallback(() => {
        isResizingSidebarV.current = true;
        setActiveResizer('sidebar-v');
        document.body.style.cursor = 'row-resize';
    }, []);

    const handleMouseDownSidebarH = useCallback(() => {
        isResizingSidebarH.current = true;
        setActiveResizer('sidebar-h');
        document.body.style.cursor = 'col-resize';
    }, []);

    const handleMouseDownOpen = useCallback(() => {
        isResizingOpenPane.current = true;
        setActiveResizer('open-closed');
        document.body.style.cursor = 'col-resize';
    }, []);

    const handleMouseMove = useCallback((e: MouseEvent) => {
        if (isResizingTop.current) {
            let h = (e.clientY / window.innerHeight) * 100;
            setTopHeight(Math.max(10, Math.min(90, h)));
        }
        if (isResizingSidebarV.current) {
            const watchlist = document.querySelector('.watchlist-pane');
            if (watchlist) {
                const rect = watchlist.getBoundingClientRect();
                const offsetP = ((e.clientY - rect.top) / rect.height) * 100;
                setSidebarSplit(Math.max(10, Math.min(90, offsetP)));
            }
        }
        if (isResizingSidebarH.current) {
            setSidebarWidth(Math.max(200, Math.min(600, e.clientX)));
        }
        if (isResizingOpenPane.current) {
            const tableContainer = document.querySelector('.trades-container');
            if (tableContainer) {
                const rect = tableContainer.getBoundingClientRect();
                const offsetP = ((e.clientX - rect.left) / rect.width) * 100;
                setOpenWidth(Math.max(10, Math.min(90, offsetP)));
            }
        }
    }, []);

    const handleMouseUp = useCallback(() => {
        isResizingTop.current = false;
        isResizingSidebarV.current = false;
        isResizingSidebarH.current = false;
        isResizingOpenPane.current = false;
        setActiveResizer(null);
        document.body.style.cursor = 'default';
    }, []);

    useEffect(() => {
        window.addEventListener('mousemove', handleMouseMove);
        window.addEventListener('mouseup', handleMouseUp);
        return () => {
            window.removeEventListener('mousemove', handleMouseMove);
            window.removeEventListener('mouseup', handleMouseUp);
        };
    }, [handleMouseMove, handleMouseUp]);

    return {
        topHeight, sidebarWidth, sidebarSplit, openWidth, activeResizer,
        handleMouseDownTop, handleMouseDownSidebarV, handleMouseDownSidebarH, handleMouseDownOpen
    };
}
