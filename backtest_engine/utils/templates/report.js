        window.onerror = function(msg, source, lineno, colno, error) {
            const errDiv = document.getElementById('error-log');
            errDiv.style.display = 'block';
            errDiv.innerHTML += msg + ' at ' + lineno + ':' + colno + '<br>';
        };
        
        const topPane = document.getElementById('top-pane');
        const bottomPane = document.getElementById('bottom-pane');
        const returnsContainer = document.getElementById('returns-container');
        const tradesContainer = document.getElementById('trades-container');
        const returnsChartEl = document.getElementById('returns-chart');
        
        // Splitters logic
        const hSplitter = document.getElementById('h-splitter');
        let isResizingH = false;
        hSplitter.addEventListener('mousedown', () => { isResizingH = true; hSplitter.classList.add('active'); document.body.style.cursor = 'row-resize'; });
        window.addEventListener('mousemove', (e) => {
            if (!isResizingH) return;
            let h = (e.clientY / window.innerHeight) * 100;
            if (h < 10) h = 10; if (h > 90) h = 90;
            topPane.style.height = h + '%';
            bottomPane.style.height = `calc(${100 - h}% - 6px)`;
            chart.resize(topPane.clientWidth, document.getElementById('chart-main').clientHeight);
            if (indicatorChart) indicatorChart.resize(topPane.clientWidth, 180);
            returnsChart.resize(returnsChartEl.clientWidth, returnsChartEl.clientHeight);
        });
        window.addEventListener('mouseup', () => { isResizingH = false; hSplitter.classList.remove('active'); document.body.style.cursor = 'default'; });
        
        const vSplitter = document.getElementById('v-splitter');
        let isResizingV = false;
        vSplitter.addEventListener('mousedown', () => { isResizingV = true; vSplitter.classList.add('active'); document.body.style.cursor = 'col-resize'; });
        window.addEventListener('mousemove', (e) => {
            if (!isResizingV) return;
            let w = (e.clientX / window.innerWidth) * 100;
            if (w < 10) w = 10; if (w > 90) w = 90;
            returnsContainer.style.width = w + '%';
            tradesContainer.style.width = `calc(${100 - w}% - 6px)`;
            returnsChart.resize(returnsChartEl.clientWidth, returnsChartEl.clientHeight);
        });
        window.addEventListener('mouseup', () => { isResizingV = false; vSplitter.classList.remove('active'); document.body.style.cursor = 'default'; });

        // ------------- MAIN CHART -------------
        const chartProperties = {
            autoSize: true,
            layout: { background: { type: 'solid', color: '#131722' }, textColor: '#d1d4dc' },
            grid: { vertLines: { color: '#2B2B43' }, horzLines: { color: '#2B2B43' } },
            rightPriceScale: { borderColor: '#2B2B43' },
            timeScale: {
                borderColor: '#2B2B43',
                timeVisible: true,
                secondsVisible: false,
            },
            localization: {
                timeFormatter: (t) => {
                    const date = new Date((t + TZ_OFFSET) * 1000);
                    return date.toISOString().replace("T", " ").substring(0, 16);
                },
            }
        };

        const chart = LightweightCharts.createChart(document.getElementById('chart-main'), chartProperties);
        const candleSeries = chart.addCandlestickSeries({
            upColor: '#26a69a', downColor: '#ef5350', borderVisible: false, wickUpColor: '#26a69a', wickDownColor: '#ef5350'
        });

        const ohlcData = JSON_OHLC_DATA;
        candleSeries.setData(ohlcData);

        // Render Stop Line Segments
        try {
            const stopSegments = JSON_STOP_SEGMENTS;
            stopSegments.forEach(segment => {
                if (segment.length > 0) {
                    const slSeries = chart.addLineSeries({
                        color: '#ff5252', lineWidth: 2, lineStyle: 2, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false,
                    });
                    slSeries.setData(segment);
                }
            });
        } catch(e) {
            document.getElementById('error-log').style.display = 'block';
            document.getElementById('error-log').innerHTML += "StopSegment Error: " + e.message + "<br>";
        }
        
        // Render Trade Connector Lines
        try {
            const tradeLines = JSON_TRADE_LINES;
            tradeLines.forEach(tLine => {
                if (tLine.length === 2 && tLine[0].time !== tLine[1].time) {
                    const isWin = tLine[1].value > tLine[0].value;
                    const tlSeries = chart.addLineSeries({
                        color: isWin ? 'rgba(76, 175, 80, 0.7)' : 'rgba(244, 67, 54, 0.7)',
                        lineWidth: 2, lineStyle: 1, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false,
                    });
                    tlSeries.setData(tLine);
                }
            });
        } catch (e) {
            document.getElementById('error-log').style.display = 'block';
            document.getElementById('error-log').innerHTML += "TradeConnector Error: " + e.message + "<br>";
        }

        // Trade Markers
        try {
            const markersData = JSON_MARKERS_DATA;
            candleSeries.setMarkers(markersData);
        } catch(e) {
            document.getElementById('error-log').style.display = 'block';
            document.getElementById('error-log').innerHTML += "Marker Error: " + e.message + "<br>";
        }
        
        // ------------- INDICATOR CHART -------------
        let indicatorChart = null;
        const indicatorsData = JSON_INDICATORS_DATA;
        
        if (indicatorsData && indicatorsData.length > 0) {
            const indContainer = document.getElementById('chart-indicators');
            indContainer.style.display = 'block';
            
            const indProperties = {
                autoSize: true,
                layout: { background: { type: 'solid', color: '#131722' }, textColor: '#787B86' },
                grid: { vertLines: { color: '#2B2B43' }, horzLines: { color: '#2B2B43' } },
                rightPriceScale: { borderColor: '#2B2B43', scaleMargins: { top: 0.1, bottom: 0.1 } },
                timeScale: { borderColor: '#2B2B43', timeVisible: true, visible: false },
                localization: {
                    timeFormatter: (t) => {
                        const date = new Date((t + TZ_OFFSET) * 1000);
                        return date.toISOString().replace("T", " ").substring(0, 16);
                    },
                }
            };
            
            indicatorChart = LightweightCharts.createChart(indContainer, indProperties);
            
            indicatorsData.forEach(ind => {
                if (ind.type === 'oscillator') {
                    // Add Lines (e.g. MACD, Signal)
                    if (ind.lines) {
                        ind.lines.forEach(line => {
                            const series = indicatorChart.addLineSeries({
                                color: line.color || '#2962FF',
                                lineWidth: 1.5,
                                title: line.name
                            });
                            series.setData(line.data);
                        });
                    }
                    // Add Histogram
                    if (ind.histogram) {
                        const histSeries = indicatorChart.addHistogramSeries({
                            color: '#26a69a',
                            priceFormat: { type: 'volume' }
                        });
                        const hData = ind.histogram.data.map(d => ({
                            ...d,
                            color: d.value >= 0 ? 'rgba(38, 166, 154, 0.5)' : 'rgba(239, 83, 80, 0.5)'
                        }));
                        histSeries.setData(hData);
                    }
                }
            });
            
            // Sync Time Scales using Logical Range (more stable for indexing)
            let isSyncing = false;
            chart.timeScale().subscribeVisibleLogicalRangeChange(range => {
                if (isSyncing || !range) return;
                isSyncing = true;
                indicatorChart.timeScale().setVisibleLogicalRange(range);
                isSyncing = false;
            });
            indicatorChart.timeScale().subscribeVisibleLogicalRangeChange(range => {
                if (isSyncing || !range) return;
                isSyncing = true;
                chart.timeScale().setVisibleLogicalRange(range);
                isSyncing = false;
            });
        }

        // ------------- RETURNS CHART -------------
        const rChartProperties = {
            autoSize: true,
            layout: { background: { type: 'solid', color: '#181C27' }, textColor: '#787B86' },
            grid: { vertLines: { visible: false }, horzLines: { color: '#2B2B43' } },
            rightPriceScale: { borderColor: '#2B2B43' },
            timeScale: { 
                borderColor: '#2B2B43', timeVisible: true, borderVisible: false,
                fixLeftEdge: true, fixRightEdge: true 
            },
            localization: {
                timeFormatter: (t) => {
                    const date = new Date((t + TZ_OFFSET) * 1000);
                    return date.toISOString().replace("T", " ").substring(0, 16);
                },
            }
        };
        
        const returnsChart = LightweightCharts.createChart(returnsChartEl, rChartProperties);
        
        // Add Benchmark underneath first
        const benchSeries = returnsChart.addLineSeries({
            color: 'rgba(255, 152, 0, 0.4)', lineWidth: 1, lineStyle: 0, 
            crosshairMarkerVisible: false, lastValueVisible: true, priceLineVisible: false,
            priceFormat: { type: 'price', precision: 2, minMove: 0.01 }
        });
        
        const benchmarkData = JSON_BENCHMARK_DATA;
        if (benchmarkData.length > 0) {
            benchSeries.setData(benchmarkData);
        }
        
        // Add Strategy Area Series on top
        const areaSeries = returnsChart.addAreaSeries({
            lineColor: '#26a69a', 
            topColor: 'rgba(38, 166, 154, 0.4)', 
            bottomColor: 'rgba(38, 166, 154, 0.0)', 
            lineWidth: 3,
            priceFormat: { type: 'price', precision: 2, minMove: 0.01 }
        });
        areaSeries.applyOptions({
            lastValueVisible: true,
            priceLineVisible: false,
        });
        
        const returnsData = JSON_RETURNS_DATA;
        const multiReturnsData = JSON_MULTI_RETURNS;
        const tradesJson = JSON_TRADES_JSON;
        const mcData = JSON_MC_DATA;
        
        if (returnsData.length > 0) {
            areaSeries.setData(returnsData);
            
            // Add dots on equity curve
            const eqMarkers = [];
            for (let i = 1; i < returnsData.length; i++) { // skip the initial 0.0 point
                const d = returnsData[i];
                const prev = returnsData[i-1];
                const isWin = d.value > prev.value;
                eqMarkers.push({
                    time: d.time,
                    position: 'inBar',
                    color: isWin ? '#26a69a' : '#ef5350',
                    shape: 'circle',
                    size: 1
                });
            }
            areaSeries.setMarkers(eqMarkers);
        }

        // Add Individual Strategy curves
        const colors = ['#2196F3', '#00BCD4', '#009688', '#FFEB3B', '#FF9800', '#FF5722', '#9C27B0', '#673AB7'];
        multiReturnsData.forEach((sData, idx) => {
            const sSeries = returnsChart.addLineSeries({
                color: colors[idx % colors.length],
                lineWidth: 1,
                lineStyle: 1,
                lastValueVisible: true,
                priceLineVisible: false,
                title: sData.label
            });
            sSeries.setData(sData.data);
        });

        setTimeout(() => { returnsChart.timeScale().fitContent(); }, 100);
        
        window.addEventListener('resize', () => {
            setTimeout(() => { returnsChart.timeScale().fitContent(); }, 50);
        });

        // Jump to logic for Returns Chart clicks
        returnsChart.subscribeClick(param => {
            if (param.time) {
                // Find matching trade exit time
                const clickedTrade = tradesJson.find(t => t.exit_ts === param.time);
                let targetTs = param.time;
                if (clickedTrade) {
                    targetTs = clickedTrade.entry_ts; // Prefer jumping to entry of the selected trade
                }
                const idx = ohlcData.findIndex(d => d.time === targetTs);
                if (idx !== -1) {
                    const viewWidth = 60;
                    chart.timeScale().setVisibleLogicalRange({ from: idx - viewWidth/3, to: idx + viewWidth*2/3 });
                }
            }
        });

        // Table Sort & Resize Logic
        let currentSort = 'entry_ts';
        let sortAsc = true;
        const tbody = document.getElementById('trades-tbody');
        
        function renderTable() {
            tbody.innerHTML = '';
            
            const sorted = [...tradesJson].sort((a, b) => {
                let vA = a[currentSort];
                let vB = b[currentSort];
                if (vA < vB) return sortAsc ? -1 : 1;
                if (vA > vB) return sortAsc ? 1 : -1;
                return 0;
            });
            
            sorted.forEach(t => {
                const tr = document.createElement('tr');
                tr.onclick = () => {
                    const idx = ohlcData.findIndex(d => d.time === t.entry_ts);
                    if (idx !== -1) {
                        const viewWidth = 60; 
                        chart.timeScale().setVisibleLogicalRange({ from: idx - viewWidth/3, to: idx + viewWidth*2/3 });
                    }
                };
                
                const cClass = t.is_win ? 'win' : 'loss';
                tr.innerHTML = `
                    <td class="label-cell">${t.strategy}</td>
                    <td>${t.entry_time}</td>
                    <td>${t.exit_time}</td>
                    <td>${t.entry_price}</td>
                    <td>${t.exit_price}</td>
                    <td class="${cClass}">${t.pnl > 0 ? '+' : ''}${t.pnl}</td>
                    <td class="${cClass}">${t.return_pct > 0 ? '+' : ''}${t.return_pct}%</td>
                `;
                tbody.appendChild(tr);
            });
            
            // update icons
            document.querySelectorAll('#trades-container th').forEach(th => {
                const icon = th.querySelector('.sort-icon');
                if (icon) {
                    if (th.dataset.sort === currentSort) {
                        icon.innerHTML = sortAsc ? ' ▲' : ' ▼';
                    } else {
                        icon.innerHTML = '';
                    }
                }
            });
        }
        
        document.querySelectorAll('#trades-container th').forEach(th => {
            // Add column resizer
            const resizer = document.createElement('div');
            resizer.className = 'resizer';
            th.appendChild(resizer);
            
            resizer.addEventListener('mousedown', function(e) {
                const startX = e.pageX;
                const startWidth = th.offsetWidth;
                function onMouseMove(moveEvent) {
                    const newWidth = startWidth + (moveEvent.pageX - startX);
                    th.style.width = newWidth + 'px';
                    th.style.minWidth = newWidth + 'px';
                    th.style.maxWidth = newWidth + 'px';
                }
                function onMouseUp() {
                    document.removeEventListener('mousemove', onMouseMove);
                    document.removeEventListener('mouseup', onMouseUp);
                }
                document.addEventListener('mousemove', onMouseMove);
                document.addEventListener('mouseup', onMouseUp);
                e.stopPropagation(); // prevent sorting click
            });
            
            // Add sort click
            if (th.dataset.sort) {
                th.addEventListener('click', (e) => {
                    if (e.target.classList.contains('resizer')) return;
                    if (currentSort === th.dataset.sort) {
                        sortAsc = !sortAsc;
                    } else {
                        currentSort = th.dataset.sort;
                        sortAsc = true;
                    }
                    renderTable();
                });
            }
        });
        
        renderTable();

        // ------------- MONTE CARLO HISTOGRAMS -------------
        function drawMCHistogram(canvasId, data, actualValue, isLoss) {
            const canvas = document.getElementById(canvasId);
            if (!canvas || !data || data.length === 0) return;
            const ctx = canvas.getContext('2d');
            const W = canvas.width, H = canvas.height;
            const pad = { top: 10, right: 8, bottom: 22, left: 30 };
            const cW = W - pad.left - pad.right;
            const cH = H - pad.top - pad.bottom;

            const N_BINS = 35;
            const minV = Math.min(...data);
            const maxV = Math.max(...data);
            const range = maxV - minV || 1;
            const binW = range / N_BINS;
            const bins = new Array(N_BINS).fill(0);
            data.forEach(v => {
                let idx = Math.min(N_BINS - 1, Math.floor((v - minV) / binW));
                bins[idx]++;
            });
            const maxCount = Math.max(...bins);

            // Background
            ctx.fillStyle = '#1E222D';
            ctx.fillRect(0, 0, W, H);

            // Bars
            const bw = cW / N_BINS;
            bins.forEach((count, i) => {
                if (count === 0) return;
                const x = pad.left + i * bw;
                const bh = (count / maxCount) * cH;
                const y = pad.top + cH - bh;
                const binCenter = minV + (i + 0.5) * binW;
                const isPastActual = isLoss ? (binCenter > actualValue) : (binCenter < actualValue);
                ctx.fillStyle = isPastActual
                    ? (isLoss ? 'rgba(239,83,80,0.65)' : 'rgba(120,123,134,0.3)')
                    : (isLoss ? 'rgba(120,123,134,0.3)' : 'rgba(76,175,80,0.65)');
                ctx.fillRect(x + 0.5, y, Math.max(bw - 1, 1), bh);
            });

            // Actual value vertical line (gold)
            const ax = pad.left + ((actualValue - minV) / range) * cW;
            ctx.strokeStyle = '#FFD700';
            ctx.lineWidth = 1.5;
            ctx.setLineDash([3, 3]);
            ctx.beginPath();
            ctx.moveTo(ax, pad.top);
            ctx.lineTo(ax, pad.top + cH);
            ctx.stroke();
            ctx.setLineDash([]);

            // Label above the actual line
            ctx.fillStyle = '#FFD700';
            ctx.font = 'bold 9px monospace';
            ctx.textAlign = ax > W * 0.6 ? 'right' : 'left';
            ctx.fillText((actualValue >= 0 && !isLoss ? '+' : '') + actualValue.toFixed(1) + '%',
                         ax + (ax > W * 0.6 ? -4 : 4), pad.top + 9);

            // X-axis ticks
            ctx.fillStyle = '#787B86';
            ctx.font = '8px monospace';
            ctx.textAlign = 'left';  ctx.fillText(minV.toFixed(0) + '%', pad.left, H - 4);
            ctx.textAlign = 'right'; ctx.fillText(maxV.toFixed(0) + '%', W - pad.right, H - 4);
            ctx.textAlign = 'center'; ctx.fillText(((minV + maxV) / 2).toFixed(0) + '%', W / 2, H - 4);
        }

        if (mcData) {
            setTimeout(() => {
                drawMCHistogram('mc-mdd-canvas', mcData.max_drawdowns, mcData.actual_mdd, true);
            }, 200);
        }
