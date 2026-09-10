"""SQLite persistence for locally cached historical candles."""

import sqlite3
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

from data.models import Candle, HistoricalQuery


class SQLiteCandleCache:
    """Cache complete historical query results in a local SQLite database."""

    def __init__(self, database_path: str | Path) -> None:
        """Create the cache database and its schema if they do not exist."""
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    def _connect(self) -> sqlite3.Connection:
        """Open a connection configured to return rows by column name."""
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize_schema(self) -> None:
        """Create cache tables with uniqueness guarantees."""
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS candles (
                    instrument_key TEXT NOT NULL,
                    interval TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume INTEGER NOT NULL,
                    open_interest INTEGER,
                    PRIMARY KEY (instrument_key, interval, timestamp)
                );
                CREATE TABLE IF NOT EXISTS candle_ranges (
                    instrument_key TEXT NOT NULL,
                    interval TEXT NOT NULL,
                    from_date TEXT NOT NULL,
                    to_date TEXT NOT NULL,
                    PRIMARY KEY (instrument_key, interval, from_date, to_date)
                );
                """
            )

    def get(self, query: HistoricalQuery) -> list[Candle] | None:
        """Return candles for an exact cached query, if present."""
        with self._connect() as connection:
            range_row = connection.execute(
                """
                SELECT 1 FROM candle_ranges
                WHERE instrument_key = ? AND interval = ?
                  AND from_date = ? AND to_date = ?
                """,
                (query.instrument_key, query.interval, query.from_date.isoformat(), query.to_date.isoformat()),
            ).fetchone()
            if range_row is None:
                return None

            rows = connection.execute(
                """
                SELECT timestamp, open, high, low, close, volume, open_interest
                FROM candles
                WHERE instrument_key = ? AND interval = ?
                  AND timestamp >= ? AND timestamp < ?
                ORDER BY timestamp ASC
                """,
                (
                    query.instrument_key,
                    query.interval,
                    _date_start(query.from_date),
                    _date_start(query.to_date, inclusive_end=True),
                ),
            ).fetchall()

        return [
            Candle(
                timestamp=datetime.fromisoformat(row["timestamp"]),
                open=row["open"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                volume=row["volume"],
                open_interest=row["open_interest"],
            )
            for row in rows
        ]

    def put(self, query: HistoricalQuery, candles: Sequence[Candle]) -> None:
        """Persist candles and mark the exact requested range as cached."""
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT OR REPLACE INTO candles
                    (instrument_key, interval, timestamp, open, high, low, close,
                     volume, open_interest)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        query.instrument_key,
                        query.interval,
                        candle.timestamp.astimezone(timezone.utc).isoformat(),
                        candle.open,
                        candle.high,
                        candle.low,
                        candle.close,
                        candle.volume,
                        candle.open_interest,
                    )
                    for candle in candles
                ],
            )
            connection.execute(
                """
                INSERT OR REPLACE INTO candle_ranges
                    (instrument_key, interval, from_date, to_date)
                VALUES (?, ?, ?, ?)
                """,
                (query.instrument_key, query.interval, query.from_date.isoformat(), query.to_date.isoformat()),
            )


def _date_start(value, inclusive_end: bool = False) -> str:
    """Return an ISO UTC boundary for SQLite's lexicographic timestamp query."""
    from datetime import datetime, time, timedelta

    boundary_date = value + timedelta(days=1) if inclusive_end else value
    return datetime.combine(boundary_date, time.min, tzinfo=timezone.utc).isoformat()