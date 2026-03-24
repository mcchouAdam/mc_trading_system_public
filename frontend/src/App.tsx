import { useState, useEffect } from 'react';
import './App.css';
import { useTradingSystem } from './hooks/useTradingSystem';
import { useLayoutResizer } from './hooks/useLayoutResizer';
import { useUrlParams } from './hooks/useUrlParams';
import { getLocalMonth1stString, getLocalMonthEndString } from './utils/dateUtils';

import { RiskPanel } from './components/RiskControl/RiskPanel';
import { Watchlist } from './components/Watchlist/Watchlist';
import { TradesTables } from './components/Trades/TradesTables';
import { TradingChart } from './components/Chart/TradingChart';
import { Modal } from './components/Common/Modal';

function App() {
  // 1. App State & URL Sync
  const [epic, setEpic] = useUrlParams('epic', 'BTCUSD');
  const [resolution, setResolution] = useUrlParams('res', 'MINUTE_5');
  const [selectedDealId, setSelectedDealId] = useState<string | null>(null);

  // 2. Date State
  const [fromDate, setFromDate] = useState(() => getLocalMonth1stString());
  const [toDate, setToDate] = useState(() => getLocalMonthEndString());

  // 3. Logic Orchestration Hook
  const trading = useTradingSystem(fromDate, toDate);

  // 4. Layout & Resizer Hook
  const layout = useLayoutResizer();

  // 5. Interactions
  useEffect(() => {
    trading.setSelectedHistoryTrade(null);
  }, [epic, resolution, trading.setSelectedHistoryTrade]);

  return (
    <div className={`dashboard-container ${layout.activeResizer ? 'resizing' : ''}`}>

      {/* Top Section */}
      <div className="top-pane" style={{ height: `${layout.topHeight}%` }}>
        <Watchlist
          width={`${layout.sidebarWidth}px`}
          sidebarSplit={layout.sidebarSplit}
          activeResizer={layout.activeResizer}
          onMouseDownV={layout.handleMouseDownSidebarV}

          currentEpic={epic}
          onSelectEpic={setEpic}
          activeEpics={trading.activeEpics}
          systemConfig={trading.systemConfig}
          onToggleStrategy={trading.toggleStrategyTarget}
          isHalted={!!trading.riskStatus?.is_halted}
          availableStrategies={trading.availableStrategies}
          supportedEpics={trading.supportedEpics}
          onAddStrategy={trading.addStrategy}
          onDeleteStrategy={trading.deleteStrategy}
          onUpdateStrategyParams={trading.updateStrategyParams}
          onToggleStrategyMl={trading.toggleStrategyMl}
        />

        <div
          className={`v-splitter-h ${layout.activeResizer === 'sidebar-h' ? 'active' : ''}`}
          onMouseDown={layout.handleMouseDownSidebarH}
        />

        <TradingChart
          epic={epic}
          resolution={resolution}
          onResolutionChange={setResolution}
          openTrades={trading.openTrades}
          selectedDealId={selectedDealId}
          selectedHistoryTrade={trading.selectedHistoryTrade}
          onRefresh={trading.fetchData}
          onNotify={trading.notify}
        />
      </div>

      {/* Main Horizontal Splitter */}
      <div
        className={`h-splitter ${layout.activeResizer === 'top-bottom' ? 'active' : ''}`}
        onMouseDown={layout.handleMouseDownTop}
      />

      {/* Bottom Section */}
      <div className="bottom-pane" style={{ height: `${100 - layout.topHeight}%` }}>
        <RiskPanel
          width={`${layout.sidebarWidth}px`}
          riskStatus={trading.riskStatus}
          onResume={trading.resumeTrade}
          onSaveLimits={trading.saveRiskLimits}
        />

        <div
          className={`v-splitter-h ${layout.activeResizer === 'sidebar-h' ? 'active' : ''}`}
          onMouseDown={layout.handleMouseDownSidebarH}
        />

        <TradesTables
          activeResizer={layout.activeResizer}
          currentEpic={epic}
          openTrades={trading.openTrades}
          openWidth={`${layout.openWidth}%`}
          onMouseDownOpen={layout.handleMouseDownOpen}
          closedTrades={trading.closedTrades}
          fromDate={fromDate}
          toDate={toDate}
          onClosePosition={trading.closePosition}
          closingDealIds={trading.closingDealIds}
          pendingSLDealIds={trading.pendingSLDealIds}
          pendingTPDealIds={trading.pendingTPDealIds}
          isFetchingClosed={trading.isFetchingClosed}
          closedTotalCount={trading.closedTotalCount}
          closedTotalPnL={trading.closedTotalPnL}
          currentPage={trading.currentPage}
          selectedDealId={selectedDealId}
          selectedHistoryTrade={trading.selectedHistoryTrade}
          onSelectTrade={setSelectedDealId}
          onSelectHistoryTrade={trading.setSelectedHistoryTrade}
          onJumpTo={undefined}
          onRefresh={trading.fetchData}
          onRefreshClosed={trading.fetchClosedData}
          onSearch={(from, to) => { setFromDate(from); setToDate(to); }}
          onUpdateOptimistically={trading.updateTradeOptimistically}
          onNotify={trading.notify}
        />
      </div>

      {/* Global Notifications */}
      {trading.modal && (
        <Modal
          isOpen={trading.modal.open}
          title={trading.modal.title}
          message={trading.modal.message}
          type={trading.modal.type}
          onClose={() => trading.setModal({ ...trading.modal!, open: false })}
          onConfirm={trading.modal.onConfirm}
        />
      )}
    </div>
  );
}

export default App;
