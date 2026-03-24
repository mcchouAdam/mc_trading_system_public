import json
import os
import redis
import threading
from trade_manager.models import TradeSignal, Actions, HistoryBarDTO
from trade_manager.capital_client import CapitalClient
from trade_manager.trade_repository import TradeRepository
from trade_manager.trade_service import TradeService

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
SIGNAL_CHANNEL = "TRADE_SIGNALS"

def handle_history_requests(r_client: redis.Redis, client: CapitalClient, repo: TradeRepository):
    """Background worker for historical bar requests from C++ engine."""
    from datetime import datetime, timedelta
    print(f"[*] History Request Handler started.")
    while True:
        try:
            req_raw = r_client.blpop("CHANNEL_HISTORY_REQUEST", timeout=5)
            if not req_raw: continue
            
            request = json.loads(req_raw[1])
            epic = request.get("epic")
            res = request.get("resolution", "MINUTE")
            req_id = request.get("request_id", "default")
            limit = request.get("limit", 200)
            
            # Try DB first
            df_db = repo.get_latest_candles(epic, res, count=limit)
            
            # Check if DB data is stale (e.g., more than 10 minutes old)
            needs_api = False
            if df_db.empty:
                needs_api = True
            else:
                last_time = df_db.index[-1]
                if (datetime.now() - last_time).total_seconds() > 600:
                    needs_api = True

            final_bars = []
            if needs_api:
                print(f"[HISTORY] DB empty/stale for {epic}. Fetching from API...")
                prices = client.get_prices(epic, res, count=limit)
                for p in prices:
                    dto = HistoryBarDTO(
                        time=p["snapshotTimeUTC"],
                        open_price=float(p["openPrice"].get("bid", 0) if isinstance(p["openPrice"], dict) else p["openPrice"]),
                        high_price=float(p["highPrice"].get("bid", 0) if isinstance(p["highPrice"], dict) else p["highPrice"]),
                        low_price=float(p["lowPrice"].get("bid", 0) if isinstance(p["lowPrice"], dict) else p["lowPrice"]),
                        close_price=float(p["closePrice"].get("bid", 0) if isinstance(p["closePrice"], dict) else p["closePrice"]),
                        volume=float(p.get("lastTradedVolume", 0))
                    )
                    final_bars.append(dto.to_dict())
            else:
                for t, row in df_db.iterrows():
                    dto = HistoryBarDTO(
                        time=t.isoformat(),
                        open_price=float(row['open']),
                        high_price=float(row['high']),
                        low_price=float(row['low']),
                        close_price=float(row['close']),
                        volume=float(row['volume'])
                    )
                    final_bars.append(dto.to_dict())

            response = {"epic": epic, "resolution": res, "request_id": req_id, "data": final_bars}
            r_client.setex(f"HISTORY_RESPONSE:{req_id}", 60, json.dumps(response))
            r_client.publish(f"HISTORY_READY:{req_id}", "READY")

        except Exception as e:
            print(f"[HISTORY ERROR] {e}")

def main():
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, decode_responses=True)
    repo = TradeRepository()
    client = CapitalClient(redis_client=r)
    
    try:
        from backtest_engine.core.ml_handler import MLInferenceHandler
        ml = MLInferenceHandler()
    except Exception as e:
        print(f"[WARN] ML Handler failed to load: {e}")
        ml = None

    service = TradeService(api_client=client, repository=repo, redis_client=r, ml_handler=ml)
    service.sync_positions_to_redis()

    hist_thread = threading.Thread(target=handle_history_requests, args=(r, client, repo), daemon=True)
    hist_thread.start()

    pubsub = r.pubsub()
    pubsub.subscribe(SIGNAL_CHANNEL)

    print(f"[*] Order Executor (Refactored) started.")
    print(f"[*] Listening on Redis channel: {SIGNAL_CHANNEL}")

    try:
        for message in pubsub.listen():
            if message["type"] != "message":
                continue
            
            try:
                data = json.loads(message["data"])
                signal = TradeSignal.from_dict(data)

                service.process_signal(signal)
                
            except json.JSONDecodeError:
                print(f"[ERROR] Invalid JSON: {message['data']}")
            except Exception as e:
                print(f"[ERROR] Processing failure: {e}")
                
    except KeyboardInterrupt:
        print("\n[!] Shutting down...")
    finally:
        pubsub.close()

if __name__ == "__main__":
    main()
