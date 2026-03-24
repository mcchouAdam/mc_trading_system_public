export const formatToLocal = (utcStr: string) => {
    if (!utcStr) return '-';
    const iso = utcStr.includes('T') ? utcStr : (utcStr.replace(' ', 'T') + 'Z');
    const date = new Date(iso);
    if (isNaN(date.getTime())) return utcStr;

    return date.toLocaleString('zh-TW', {
        timeZone: 'Asia/Taipei',
        hour12: false,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    }).replace(/\//g, '-');
};

export const parseToUnix = (utcStr: string): number => {
    if (!utcStr) return 0;
    const iso = utcStr.includes('T') ? utcStr : (utcStr.replace(' ', 'T') + 'Z');
    const date = new Date(iso);
    return isNaN(date.getTime()) ? 0 : Math.floor(date.getTime() / 1000);
};

export const getLocalDateString = (date: Date = new Date()) => {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
};

export const getLocalMonth1stString = (date: Date = new Date()) => {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    return `${year}-${month}-01`;
};
export const getLocalMonthEndString = (date: Date = new Date()) => {
    const end = new Date(date.getFullYear(), date.getMonth() + 1, 0);
    return getLocalDateString(end);
};
