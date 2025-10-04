export enum BotType {
  SIMPLE_REVERSE = 'simple-reverse',
  TURTLE_REVERSE = 'turtle-reverse',
  HYBRID_STRATEGY = 'hybrid-strategy'
}

export enum BotStatus {
  RUNNING = 'running',
  STOPPED = 'stopped',
  ERROR = 'error',
  PAUSED = 'paused'
}

export enum TradeType {
  OPEN_LONG = 'open_long',
  OPEN_SHORT = 'open_short',
  CLOSE_LONG = 'close_long',
  CLOSE_SHORT = 'close_short'
}

export enum MarketType {
  SPOT = 'spot',
  SWAP = 'swap',
  FUTURES = 'futures'
}