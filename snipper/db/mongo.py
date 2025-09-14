"""MongoDB connection and trade repository."""

from typing import List, Optional

import pymongo
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from ..config import settings
from ..logging import get_logger
from ..models.trade import Trade, TradeFilter, TradeStats

logger = get_logger(__name__)


class MongoManager:
    """MongoDB connection manager with repository pattern."""
    
    def __init__(self):
        self._client: Optional[MongoClient] = None
        self._db: Optional[Database] = None
        self._collection: Optional[Collection] = None
    
    def connect(self) -> None:
        """Connect to MongoDB and ensure indexes."""
        try:
            self._client = MongoClient(settings.mongo_uri)
            self._db = self._client[settings.db_name]
            self._collection = self._db[settings.collection_name]
            
            # Test connection
            self._client.server_info()
            
            # Ensure indexes
            self._ensure_indexes()
            
            logger.info(
                "MongoDB connected successfully",
                extra={
                    'mongo_uri': settings.mongo_uri,
                    'db_name': settings.db_name,
                    'collection_name': settings.collection_name,
                    'event': 'mongo_connected'
                }
            )
            
        except Exception as e:
            logger.error(
                "Failed to connect to MongoDB",
                extra={
                    'mongo_uri': settings.mongo_uri,
                    'error': str(e),
                    'event': 'mongo_connection_failed'
                }
            )
            raise
    
    def _ensure_indexes(self) -> None:
        """Ensure required indexes exist."""
        if not self._collection:
            return
        
        indexes = [
            # Unique index on trade_id
            {'keys': [('trade_id', 1)], 'unique': True},
            # Index on created_at for time-based queries
            {'keys': [('created_at', -1)]},
            # Index on status for filtering
            {'keys': [('status', 1)]},
            # Index on token_mint for filtering
            {'keys': [('token_mint', 1)]},
            # Compound index for common queries
            {'keys': [('status', 1), ('created_at', -1)]},
            # Index on datetime fields
            {'keys': [('created_at_datetime', -1)]},
        ]
        
        for index in indexes:
            try:
                if 'unique' in index:
                    self._collection.create_index(
                        index['keys'], 
                        unique=index['unique']
                    )
                else:
                    self._collection.create_index(index['keys'])
            except pymongo.errors.OperationFailure:
                # Index might already exist
                pass
        
        logger.info("MongoDB indexes ensured", extra={'event': 'indexes_ensured'})
    
    @property
    def collection(self) -> Collection:
        """Get MongoDB collection."""
        if not self._collection:
            self.connect()
        return self._collection
    
    def close(self) -> None:
        """Close MongoDB connection."""
        if self._client:
            self._client.close()
            logger.info("MongoDB connection closed", extra={'event': 'mongo_closed'})


class TradeRepository:
    """Repository for trade data operations."""
    
    def __init__(self, mongo_manager: MongoManager):
        self.mongo = mongo_manager
    
    async def save_trade(self, trade: Trade) -> bool:
        """Save or update a trade."""
        try:
            collection = self.mongo.collection
            data = trade.to_mongo_dict()
            
            # Upsert based on trade_id
            result = collection.replace_one(
                {'trade_id': trade.trade_id},
                data,
                upsert=True
            )
            
            logger.info(
                "Trade saved to MongoDB",
                extra={
                    'trade_id': trade.trade_id,
                    'upserted': result.upserted_id is not None,
                    'modified': result.modified_count > 0,
                    'event': 'trade_saved'
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to save trade",
                extra={
                    'trade_id': trade.trade_id,
                    'error': str(e),
                    'event': 'trade_save_failed'
                }
            )
            return False
    
    async def get_trade(self, trade_id: str) -> Optional[Trade]:
        """Get a trade by ID."""
        try:
            collection = self.mongo.collection
            data = collection.find_one({'trade_id': trade_id})
            
            if data:
                # Remove MongoDB _id field
                data.pop('_id', None)
                return Trade.from_mongo_dict(data)
            
            return None
            
        except Exception as e:
            logger.error(
                "Failed to get trade",
                extra={
                    'trade_id': trade_id,
                    'error': str(e),
                    'event': 'trade_get_failed'
                }
            )
            return None
    
    async def get_trades(self, trade_filter: TradeFilter) -> List[Trade]:
        """Get trades based on filter criteria."""
        try:
            collection = self.mongo.collection
            query = {}
            
            # Build query from filter
            if trade_filter.status:
                query['status'] = trade_filter.status
            if trade_filter.token_mint:
                query['token_mint'] = trade_filter.token_mint
            if trade_filter.close_reason:
                query['close_reason'] = trade_filter.close_reason
            if trade_filter.min_pnl_percent is not None:
                query.setdefault('pnl_percent', {})['$gte'] = trade_filter.min_pnl_percent
            if trade_filter.max_pnl_percent is not None:
                query.setdefault('pnl_percent', {})['$lte'] = trade_filter.max_pnl_percent
            if trade_filter.start_date:
                query.setdefault('created_at_datetime', {})['$gte'] = trade_filter.start_date
            if trade_filter.end_date:
                query.setdefault('created_at_datetime', {})['$lte'] = trade_filter.end_date
            
            # Execute query with pagination
            cursor = collection.find(query).sort('created_at', -1).skip(trade_filter.offset).limit(trade_filter.limit)
            
            trades = []
            for data in cursor:
                data.pop('_id', None)
                trades.append(Trade.from_mongo_dict(data))
            
            logger.info(
                "Trades retrieved from MongoDB",
                extra={
                    'query': query,
                    'count': len(trades),
                    'event': 'trades_retrieved'
                }
            )
            
            return trades
            
        except Exception as e:
            logger.error(
                "Failed to get trades",
                extra={
                    'filter': trade_filter.model_dump(),
                    'error': str(e),
                    'event': 'trades_get_failed'
                }
            )
            return []
    
    async def get_trade_stats(self) -> TradeStats:
        """Get trade statistics."""
        try:
            collection = self.mongo.collection
            
            # Aggregate statistics
            pipeline = [
                {'$match': {'status': 'closed'}},
                {'$group': {
                    '_id': None,
                    'total_trades': {'$sum': 1},
                    'winning_trades': {'$sum': {'$cond': [{'$gt': ['$pnl_percent', 0]}, 1, 0]}},
                    'total_pnl': {'$sum': '$pnl_percent'},
                    'avg_hold_time': {'$avg': '$hold_time_minutes'},
                    'total_fees': {'$sum': '$total_fees_sol'},
                    'best_pnl': {'$max': '$pnl_percent'},
                    'worst_pnl': {'$min': '$pnl_percent'},
                }}
            ]
            
            result = list(collection.aggregate(pipeline))
            
            if result:
                data = result[0]
                total_trades = data['total_trades']
                winning_trades = data['winning_trades']
                
                stats = TradeStats(
                    total_trades=total_trades,
                    winning_trades=winning_trades,
                    losing_trades=total_trades - winning_trades,
                    win_rate=(winning_trades / total_trades * 100) if total_trades > 0 else 0,
                    total_pnl_percent=data.get('total_pnl', 0),
                    avg_hold_time_minutes=data.get('avg_hold_time', 0),
                    total_fees_sol=data.get('total_fees', 0),
                    best_trade_pnl=data.get('best_pnl'),
                    worst_trade_pnl=data.get('worst_pnl'),
                )
            else:
                stats = TradeStats(
                    total_trades=0,
                    winning_trades=0,
                    losing_trades=0,
                    win_rate=0,
                    total_pnl_percent=0,
                    avg_hold_time_minutes=0,
                    total_fees_sol=0,
                )
            
            logger.info(
                "Trade statistics calculated",
                extra={
                    'stats': stats.model_dump(),
                    'event': 'trade_stats_calculated'
                }
            )
            
            return stats
            
        except Exception as e:
            logger.error(
                "Failed to calculate trade stats",
                extra={
                    'error': str(e),
                    'event': 'trade_stats_failed'
                }
            )
            # Return empty stats on error
            return TradeStats(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0,
                total_pnl_percent=0,
                avg_hold_time_minutes=0,
                total_fees_sol=0,
            )


# Global instances
mongo_manager = MongoManager()
trade_repository = TradeRepository(mongo_manager)


def get_mongo_manager() -> MongoManager:
    """Get MongoDB manager instance."""
    return mongo_manager


def get_trade_repository() -> TradeRepository:
    """Get trade repository instance."""
    return trade_repository


async def init_database() -> None:
    """Initialize database connection."""
    mongo_manager.connect()


async def close_database() -> None:
    """Close database connection."""
    mongo_manager.close()