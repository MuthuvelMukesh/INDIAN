# Data Layer

The provider is intentionally read-only. It exposes historical candle retrieval
only; there is no order endpoint, order scope, or live execution path here.

Use exchange-qualified Upstox instrument keys, for example
`NSE_EQ|INE002A01018`, rather than relying on display symbols alone.