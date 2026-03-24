import os
import requests
import redis
from datetime import datetime, timedelta, date
from typing import Optional, List, Dict, Any, Tuple
from trade_manager.models import TradeCostDTO

try:
    from dotenv import load_dotenv
    load_dotenv(override=False)
except ImportError:
    pass

DEFAULT_REST_URL = "https://demo-api-capital.backend-capital.com"
DEFAULT_REDIS_HOST = "localhost"
DEFAULT_REDIS_PORT = 6379
API_TIMEOUT = 10
HISTORY_API_TIMEOUT = 15
PRICE_PRECISION = 5

HEADER_API_KEY = "X-CAP-API-KEY"
HEADER_CST = "CST"
HEADER_SECURITY_TOKEN = "X-SECURITY-TOKEN"

REDIS_KEY_CST = "CAPITAL_CST"
REDIS_KEY_TOKEN = "CAPITAL_TOKEN"

COST_TYPES = {"SWAP", "TRADE_COMMISSION", "TRADE_COMMISSION_GSL"}

class CapitalClient:
    def __init__(self, rest_url: Optional[str] = None, redis_client: Optional[redis.Redis] = None):
        self.base_url = rest_url or os.getenv("CAPITAL_REST_URL") or DEFAULT_REST_URL
        self._redis = redis_client or self._init_redis()
        self.api_key = os.getenv("CAPITAL_API_KEY")

    def _init_redis(self) -> redis.Redis:
        host = os.getenv("REDIS_HOST", DEFAULT_REDIS_HOST)
        port = int(os.getenv("REDIS_PORT", DEFAULT_REDIS_PORT))
        pw   = os.getenv("REDIS_PASSWORD")
        if host == 'redis' and not os.path.exists('/.dockerenv'):
            host = 'localhost'
        return redis.Redis(host=host, port=port, password=pw, decode_responses=True)

    def _get_headers(self) -> dict:
        cst = self._redis.get(REDIS_KEY_CST)
        token = self._redis.get(REDIS_KEY_TOKEN)
        
        if not cst or not token:
            cst = cst or self._redis.get(REDIS_KEY_CST.lower())
            token = token or self._redis.get(REDIS_KEY_TOKEN.lower())
            
        if not cst or not token:
            raise RuntimeError("Session tokens missing in Redis. Run auth_manager.")
        
        return {
            HEADER_API_KEY: self.api_key,
            HEADER_CST: cst,
            HEADER_SECURITY_TOKEN: token,
            "Content-Type": "application/json",
        }

    def get_position_confirm(self, deal_reference: str) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/api/v1/confirms/{deal_reference}"
        try:
            resp = requests.get(url, headers=self._get_headers(), timeout=API_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"[ERROR] get_position_confirm: {e}")
            return None

    def open_position(self, epic: str, direction: str, size: float, 
                      stop_level: Optional[float] = None, 
                      profit_level: Optional[float] = None) -> Optional[str]:
        url = f"{self.base_url}/api/v1/positions"
        body = {"epic": epic, "direction": direction, "size": size}
        if stop_level:
            body["stopLevel"] = round(float(stop_level), PRICE_PRECISION)
        if profit_level:
            body["profitLevel"] = round(float(profit_level), PRICE_PRECISION)
        
        try:
            resp = requests.post(url, headers=self._get_headers(), json=body, timeout=API_TIMEOUT)
            resp.raise_for_status()
            return resp.json().get("dealReference")
        except Exception as e:
            print(f"[ERROR] open_position: {e}")
            return None

    def update_position(self, deal_id: str, stop_level: Optional[float] = None, 
                        profit_level: Optional[float] = None) -> bool:
        url = f"{self.base_url}/api/v1/positions/{deal_id}"
        body = {}
        if stop_level: body["stopLevel"] = round(float(stop_level), PRICE_PRECISION)
        if profit_level: body["profitLevel"] = round(float(profit_level), PRICE_PRECISION)
        
        if not body: return True
        try:
            resp = requests.put(url, headers=self._get_headers(), json=body, timeout=API_TIMEOUT)
            resp.raise_for_status()
            return True
        except Exception as e:
            print(f"[ERROR] update_position: {e}")
            return False

    def close_position(self, deal_id: str, size: Optional[float] = None) -> Optional[str]:
        url = f"{self.base_url}/api/v1/positions/{deal_id}"
        body = {"size": size} if size else {}
        try:
            resp = requests.delete(url, headers=self._get_headers(), json=body, timeout=API_TIMEOUT)
            resp.raise_for_status()
            return resp.json().get("dealReference")
        except Exception as e:
            print(f"[ERROR] close_position: {e}")
            return None

    def get_accounts(self) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/api/v1/accounts"
        try:
            resp = requests.get(url, headers=self._get_headers(), timeout=API_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"[ERROR] get_accounts: {e}")
            return None

    def get_prices(self, epic: str, resolution: str, count: int = 200) -> List[Dict[str, Any]]:
        """GET /api/v1/prices/{epic}"""
        url = f"{self.base_url}/api/v1/prices/{epic}"
        params = {"resolution": resolution, "max": count}
        try:
            resp = requests.get(url, headers=self._get_headers(), params=params, timeout=API_TIMEOUT)
            resp.raise_for_status()
            return resp.json().get("prices", [])
        except Exception as e:
            print(f"[ERROR] get_prices for {epic}: {e}")
            return []

    def fetch_transactions(self, from_dt: datetime, to_dt: datetime, type_filter: str = None) -> List[Dict[str, Any]]:
        results = []
        now_utc = datetime.utcnow()
        to_dt = min(to_dt, now_utc)

        current = from_dt
        while current < to_dt:
            next_dt = min(current + timedelta(days=1), to_dt)
            url = f"{self.base_url}/api/v1/history/transactions?from={current.strftime('%Y-%m-%dT%H:%M:%S')}&to={next_dt.strftime('%Y-%m-%dT%H:%M:%S')}&detailed=true"
            if type_filter: url += f"&type={type_filter}"
            
            try:
                resp = requests.get(url, headers=self._get_headers(), timeout=HISTORY_API_TIMEOUT)
                resp.raise_for_status()
                results.extend(resp.json().get("transactions", []))
            except Exception as e:
                print(f"[WARN] fetch_transactions: {e}")
            current = next_dt
        return results

    def fetch_costs_for_range(self, from_date: date, to_date: date) -> List[Dict[str, Any]]:
        """Fetch SWAP + COMMISSION transactions for a date range and return as DTO dicts."""
        from_dt = datetime(from_date.year, from_date.month, from_date.day, 0, 0, 0)
        to_dt   = datetime(to_date.year,   to_date.month,   to_date.day,   23, 59, 59)

        raw = self.fetch_transactions(from_dt, to_dt)

        records = []
        for tx in raw:
            tx_type = tx.get("transactionType", "")
            if tx_type not in COST_TYPES:
                continue
                
            tx_date_str = tx.get("dateUtc") or tx.get("date", "")
            try:
                tx_date = datetime.fromisoformat(tx_date_str.replace("Z", "+00:00")).date()
            except Exception:
                tx_date = from_date

            dto = TradeCostDTO(
                deal_id=tx.get("reference", ""),
                date=tx_date,
                type=tx_type,
                amount=float(tx.get("amount") or tx.get("size", 0)),
                currency=tx.get("currency", "USD"),
                epic=tx.get("instrumentName", "Unknown"),
                raw_reference=tx.get("reference", "")
            )
            records.append(dto.to_dict())
            
        return records
