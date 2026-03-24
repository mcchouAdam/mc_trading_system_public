import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import date, datetime
from typing import Optional, List, Dict, Any, Set
from trade_manager.models import TradeRecord

DEFAULT_DB_PORT = "5432"
DEFAULT_DB_NAME = "trading_db"
DEFAULT_CURRENCY = "USD"
DEFAULT_TRADE_SOURCE = "AUTO"

class TradeRepository:
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or self._build_db_url()

    def _build_db_url(self) -> str:
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            if db_url.startswith("Host="):
                return (db_url.replace("Host=", "host=").replace("Database=", "dbname=")
                              .replace("Username=", "user=").replace("Password=", "password=")
                              .replace(";", " "))
            return db_url

        host = os.getenv("POSTGRES_HOST")
        port = os.getenv("POSTGRES_PORT", DEFAULT_DB_PORT)
        user = os.getenv("POSTGRES_USER")
        pw = os.getenv("POSTGRES_PASSWORD")
        db = os.getenv("POSTGRES_DB", DEFAULT_DB_NAME)
        
        if host in ['postgres', 'mc-postgres'] and not os.path.exists('/.dockerenv'):
            host = 'localhost'
            
        return f"host={host} port={port} dbname={db} user={user} password={pw}"

    def _get_conn(self):
        try:
            return psycopg2.connect(self.db_url)
        except psycopg2.OperationalError as e:
            if "host=postgres" in self.db_url and not os.path.exists('/.dockerenv'):
                new_url = self.db_url.replace("host=postgres", "host=localhost")
                return psycopg2.connect(new_url)
            raise e

    def insert_trade_open(self, trade: TradeRecord):
        """Records a new open trade into the DB."""
        sql = """
        INSERT INTO trades
            (deal_id, deal_reference, epic, direction, size, entry_price,
             entry_time, resolution, strategy, source, leverage, currency,
             stop_loss, take_profit)
        VALUES
            (%(deal_id)s, %(deal_reference)s, %(epic)s, %(direction)s, %(size)s, %(entry_price)s,
             %(entry_time)s, %(resolution)s, %(strategy)s, %(source)s, %(leverage)s, %(currency)s,
             %(stop_loss)s, %(take_profit)s)
        ON CONFLICT (deal_id) DO NOTHING;
        """
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, trade.__dict__)
                if cur.rowcount > 0:
                    conn.commit()
                    print(f"[DB OK] Inserted open trade for {trade.deal_id}")

    def update_trade_close(
        self, 
        deal_id: str, 
        exit_price: float, 
        exit_time: datetime, 
        realized_pnl: float, 
        exit_type: str = "AUTO"
    ):
        """Updates an existing trade with exit details."""
        sql = """
        UPDATE trades
        SET exit_price   = %(exit_price)s,
            exit_time    = %(exit_time)s,
            realized_pnl = %(realized_pnl)s,
            exit_type    = %(exit_type)s,
            updated_at   = CURRENT_TIMESTAMP
        WHERE deal_id = %(deal_id)s;
        """
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, {
                    "deal_id": deal_id, "exit_price": exit_price,
                    "exit_time": exit_time, "realized_pnl": realized_pnl,
                    "exit_type": exit_type,
                })
                if cur.rowcount > 0:
                    conn.commit()
                    print(f"[DB OK] Updated close trade for {deal_id}")

    def update_trade_sl(self, deal_id: str, stop_loss: float):
        """Updates only the stop loss for a given deal_id."""
        sql = "UPDATE trades SET stop_loss = %(sl)s, updated_at = CURRENT_TIMESTAMP WHERE deal_id = %(id)s;"
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, {"sl": stop_loss, "id": deal_id})
                conn.commit()
                print(f"[DB OK] Updated SL in DB for {deal_id}")

    def upsert_trade_costs(self, records: List[Dict[str, Any]]):
        """Inserts SWAP or COMMISSION costs, avoiding duplicates."""
        if not records:
            return
        sql = """
        INSERT INTO trade_costs (date, deal_id, cost_type, amount, currency, epic, raw_reference)
        VALUES (%(date)s, %(deal_id)s, %(cost_type)s, %(amount)s, %(currency)s, %(epic)s, %(raw_reference)s)
        ON CONFLICT (date, raw_reference, cost_type) DO NOTHING;
        """
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.executemany(sql, records)
                conn.commit()

    def get_trades(self, **filters) -> List[Dict[str, Any]]:
        """Fetch trades with cost summary from the DB."""
        conditions = ["1=1"]
        params = {}
        
        mapping = {
            "strategy": "strategy = %(strategy)s",
            "epic": "epic = %(epic)s",
            "source": "source = %(source)s",
            "from_date": "entry_time >= %(from_date)s",
            "to_date": "entry_time <= %(to_date)s",
        }
        
        for key, cond in mapping.items():
            if filters.get(key):
                conditions.append(cond)
                params[key] = filters[key]
        
        if not filters.get("include_open", False):
            conditions.append("exit_time IS NOT NULL")

        where = " AND ".join(conditions)
        sql = f"SELECT * FROM trades_with_costs WHERE {where} ORDER BY entry_time ASC;"
        
        with self._get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params)
                return [dict(row) for row in cur.fetchall()]

    def get_covered_cost_dates(self, from_date: date, to_date: date) -> Set[date]:
        """Return set of dates that already have cost records in DB."""
        sql = "SELECT DISTINCT date FROM trade_costs WHERE date >= %(from_date)s AND date <= %(to_date)s;"
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, {"from_date": from_date, "to_date": to_date})
                return {row[0] for row in cur.fetchall()}

    def get_latest_candles(self, epic: str, resolution: str, count: int = 200) -> Any:
        """Fetch latest X candles from DB for ML feature extraction (SQL injection safe)."""
        import pandas as pd
        query = """
            SELECT time, open_price as open, high_price as high, 
                   low_price as low, close_price as close, volume 
            FROM market_candles 
            WHERE epic = %(epic)s AND resolution = %(res)s
            ORDER BY time DESC
            LIMIT %(limit)s
        """
        with self._get_conn() as conn:
            df = pd.read_sql(query, conn, params={"epic": epic, "res": resolution, "limit": count})
            if df.empty:
                return df
            df.set_index("time", inplace=True)
            df.index = pd.to_datetime(df.index)
            return df.sort_index()
