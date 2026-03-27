import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import logging
from squeeze.data.downloader import download_market_data

logger = logging.getLogger(__name__)

TRACKING_COLUMNS = [
    'date', 'ticker', 'name', 'entry_price', 'signal',
    'current_price', 'return_pct', 'strategy_return_pct', 'days_tracked',
    'last_updated', 'status', 'type', 'pattern', 'momentum',
    'prev_momentum', 'energy_level', 'squeeze_on', 'fired',
    'market_regime', 'benchmark_ticker', 'value_score'
]


def normalize_tracking_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=TRACKING_COLUMNS)

    normalized = df.copy()
    defaults = {
        'strategy_return_pct': None,
        'type': 'buy',
        'pattern': 'squeeze',
        'momentum': 0.0,
        'prev_momentum': 0.0,
        'energy_level': 0,
        'squeeze_on': False,
        'fired': False,
        'market_regime': 'unknown',
        'benchmark_ticker': '000300.SS',
        'value_score': None,
    }
    for column in TRACKING_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = defaults.get(column, None)

    normalized['return_pct'] = pd.to_numeric(normalized['return_pct'], errors='coerce').fillna(0.0)
    normalized['strategy_return_pct'] = pd.to_numeric(normalized['strategy_return_pct'], errors='coerce')
    missing_strategy = normalized['strategy_return_pct'].isna()
    normalized.loc[missing_strategy, 'strategy_return_pct'] = normalized.loc[missing_strategy].apply(
        lambda row: -row['return_pct'] if row.get('type') == 'sell' else row['return_pct'],
        axis=1,
    )
    normalized['days_tracked'] = pd.to_numeric(normalized['days_tracked'], errors='coerce').fillna(0).astype(int)
    normalized['momentum'] = pd.to_numeric(normalized['momentum'], errors='coerce').fillna(0.0)
    normalized['prev_momentum'] = pd.to_numeric(normalized['prev_momentum'], errors='coerce').fillna(0.0)
    normalized['energy_level'] = pd.to_numeric(normalized['energy_level'], errors='coerce').fillna(0).astype(int)
    normalized['squeeze_on'] = normalized['squeeze_on'].apply(lambda value: bool(value) if pd.notna(value) else False)
    normalized['fired'] = normalized['fired'].apply(lambda value: bool(value) if pd.notna(value) else False)
    return normalized[TRACKING_COLUMNS]


class PerformanceTracker:
    """
    Tracks Buy and Sell recommendations daily for 14 days.
    """
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _get_china_now(self) -> datetime:
        return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))

    def _init_db(self):
        if not self.db_path.exists():
            df = pd.DataFrame(columns=TRACKING_COLUMNS)
            df.to_csv(self.db_path, index=False)

    def _load_db(self) -> pd.DataFrame:
        try:
            df = pd.read_csv(self.db_path)
        except Exception:
            self._init_db()
            df = pd.read_csv(self.db_path)
        return normalize_tracking_df(df)

    def _infer_market_context(self, benchmark_ticker: str = "000300.SS") -> Dict[str, Any]:
        try:
            benchmark_data = download_market_data([benchmark_ticker], period="1y")
            if benchmark_data.empty:
                raise ValueError("empty benchmark data")

            if isinstance(benchmark_data.columns, pd.MultiIndex):
                benchmark_df = benchmark_data[benchmark_ticker].dropna(subset=['Close'])
            else:
                benchmark_df = benchmark_data.dropna(subset=['Close'])

            if benchmark_df.empty or len(benchmark_df) < 30:
                raise ValueError("insufficient benchmark data")

            closes = benchmark_df['Close']
            close_now = float(closes.iloc[-1])
            sma50 = float(closes.rolling(50).mean().iloc[-1]) if len(closes) >= 50 else close_now
            sma200 = float(closes.rolling(200).mean().iloc[-1]) if len(closes) >= 200 else sma50
            return_20d = ((close_now / float(closes.iloc[-21])) - 1.0) * 100 if len(closes) >= 21 else 0.0

            if close_now > sma50 > sma200 and return_20d > 0:
                regime = "bull_trend"
            elif close_now < sma50 < sma200 and return_20d < 0:
                regime = "bear_trend"
            else:
                regime = "range_bound"

            return {
                "market_regime": regime,
                "benchmark_ticker": benchmark_ticker,
            }
        except Exception as exc:
            logger.warning(f"Unable to infer market regime from {benchmark_ticker}: {exc}")
            return {
                "market_regime": "unknown",
                "benchmark_ticker": benchmark_ticker,
            }

    def record_recommendations(
        self,
        results: List[Dict[str, Any]],
        rec_type: str = 'buy',
        market_context: Optional[Dict[str, Any]] = None,
    ):
        """
        Records top 10 recommendations of a specific type.
        rec_type: 'buy' or 'sell'
        """
        if not results:
            return

        context = market_context.copy() if market_context else self._infer_market_context()

        # Sort and take top 10
        if rec_type == 'buy':
            # Highest momentum first
            sorted_results = sorted(results, key=lambda x: x.get('momentum', 0), reverse=True)[:10]
        else:
            # Lowest momentum first (most negative)
            sorted_results = sorted(results, key=lambda x: x.get('momentum', 0), reverse=False)[:10]

        now_str = self._get_china_now().strftime("%Y-%m-%d")
        new_records = []
        
        for r in sorted_results:
            new_records.append({
                'date': now_str,
                'ticker': r.get('ticker'),
                'name': r.get('name'),
                'entry_price': r.get('Close'),
                'signal': r.get('Signal'),
                'current_price': r.get('Close'),
                'return_pct': 0.0,
                'strategy_return_pct': 0.0,
                'days_tracked': 0,
                'last_updated': now_str,
                'status': 'tracking',
                'type': rec_type,
                'pattern': context.get('pattern', 'squeeze'),
                'momentum': r.get('momentum', 0.0),
                'prev_momentum': r.get('prev_momentum', 0.0),
                'energy_level': r.get('energy_level', 0),
                'squeeze_on': r.get('is_squeezed', r.get('squeeze_on', False)),
                'fired': r.get('fired', False),
                'market_regime': context.get('market_regime', 'unknown'),
                'benchmark_ticker': context.get('benchmark_ticker', '000300.SS'),
                'value_score': r.get('value_score'),
            })
        
        df_new = pd.DataFrame(new_records)
        df_old = self._load_db()
        if df_old.empty:
            df_combined = df_new.copy()
        else:
            df_combined = pd.concat([df_old, df_new], ignore_index=True)
        df_combined = df_combined.drop_duplicates(
            subset=['date', 'ticker', 'type', 'pattern'],
            keep='last',
        )
        df_combined['date_dt'] = pd.to_datetime(df_combined['date'], errors='coerce')
        active = df_combined[df_combined['status'] == 'tracking'].sort_values(
            by=['date_dt', 'ticker'],
            ascending=[False, True],
        )
        completed = df_combined[df_combined['status'] != 'tracking']
        active = active.head(25)
        df_combined = pd.concat([active, completed], ignore_index=True)
        df_combined = df_combined.sort_values(by=['date_dt', 'ticker'], ascending=[False, True]).drop(columns=['date_dt'])
        df_combined = normalize_tracking_df(df_combined)
        df_combined.to_csv(self.db_path, index=False)
        logger.info(f"Recorded {len(new_records)} {rec_type} signals to {self.db_path} (Active list limited to 25, completed history preserved)")

    def update_daily_performance(self) -> List[Dict[str, Any]]:
        """
        Updates performance for all active tracking items.
        """
        df = self._load_db()
        if df.empty:
            return []

        # Find entries still in 'tracking' status
        active = df[df['status'] == 'tracking'].copy()
        if active.empty:
            return []

        now = self._get_china_now()
        now_str = now.strftime("%Y-%m-%d")
        
        # Don't update if already updated today
        active = active[active['last_updated'] != now_str]
        if active.empty:
            return []

        tickers = active['ticker'].unique().tolist()
        logger.info(f"Updating performance for {len(tickers)} active trackers...")
        
        current_data = download_market_data(tickers, period="1d")
        if current_data.empty:
            return []
        
        results = []
        for index, row in active.iterrows():
            ticker = row['ticker']
            try:
                if len(tickers) == 1:
                    price_now = current_data['Close'].iloc[-1]
                else:
                    if ticker in current_data.columns.get_level_values(0):
                        price_now = current_data[ticker]['Close'].iloc[-1]
                    else:
                        continue
                
                entry_price = float(row['entry_price'])
                return_pct = ((price_now - entry_price) / entry_price) * 100
                strategy_return_pct = -return_pct if row.get('type') == 'sell' else return_pct
                
                rec_date = datetime.strptime(row['date'], "%Y-%m-%d").replace(tzinfo=timezone(timedelta(hours=8)))
                days_passed = (now - rec_date).days
                
                df.at[index, 'current_price'] = price_now
                df.at[index, 'return_pct'] = return_pct
                df.at[index, 'strategy_return_pct'] = strategy_return_pct
                df.at[index, 'days_tracked'] = days_passed
                df.at[index, 'last_updated'] = now_str
                
                if days_passed >= 14:
                    df.at[index, 'status'] = 'completed'
                
                results.append(df.loc[index].to_dict())
            except Exception as e:
                logger.error(f"Error updating {ticker}: {e}")

        df.to_csv(self.db_path, index=False)
        return results

    def get_active_tracking_list(self, rec_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns currently tracking recommendations filtered by type."""
        df = self._load_db()
        if df.empty:
            return []
        
        mask = df['status'] == 'tracking'
        if rec_type:
            # Handle legacy data without 'type' column
            if 'type' in df.columns:
                mask = mask & (df['type'] == rec_type)
            elif rec_type == 'buy':
                pass # all legacy is buy
            else:
                return []
                
        active = df[mask].sort_values(by='date', ascending=False).head(25)
        return active.to_dict('records')
