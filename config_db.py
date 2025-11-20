import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncEngine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Float, JSON, DateTime, ForeignKey, select, update
from config import DATABASE_URL, MAX_TASK_ATTEMPTS

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("DatabaseCore")

class Base(DeclarativeBase):
    pass

class ScrapeTask(Base):
    """Table for queuing URLs to be processed."""
    __tablename__ = 'scrape_tasks'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String, unique=True, index=True)
    status: Mapped[str] = mapped_column(String, default='pending')
    priority: Mapped[int] = mapped_column(default=1)
    attempts: Mapped[int] = mapped_column(default=0)
    last_error: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

class ScrapeResult(Base):
    """Table for storing final results."""
    __tablename__ = 'scrape_results'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey('scrape_tasks.id'))
    title: Mapped[str] = mapped_column(String)
    price: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String)
    confidence_score: Mapped[float] = mapped_column(Float)
    meta_data: Mapped[Dict[str, Any]] = mapped_column(JSON) 
    extracted_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

class DatabaseCore:
    def __init__(self, db_url: str = DATABASE_URL):
        self.engine: AsyncEngine = create_async_engine(db_url, echo=False)
        self.async_session_maker = async_sessionmaker(self.engine, expire_on_commit=False)

    async def init_models(self) -> None:
        """Initialize database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def dispose(self) -> None:
        """Dispose of the connection pool."""
        await self.engine.dispose()

    async def add_task(self, url: str, priority: int = 1) -> bool:
        """Add a new task to the queue."""
        async with self.async_session_maker() as session:
            try:
                stmt = select(ScrapeTask).where(ScrapeTask.url == url)
                existing = await session.execute(stmt)
                if existing.scalar():
                    return False
                
                task = ScrapeTask(url=url, priority=priority)
                session.add(task)
                await session.commit()
                return True
            except Exception as e:
                logger.error(f"Error adding task: {e}")
                return False

    async def get_pending_task(self) -> Optional[ScrapeTask]:
        """Get the next pending task and mark it as processing."""
        async with self.async_session_maker() as session:
            async with session.begin():
                stmt = select(ScrapeTask).where(
                    ScrapeTask.status.in_(['pending', 'failed']),
                    ScrapeTask.attempts < MAX_TASK_ATTEMPTS
                ).order_by(ScrapeTask.priority.desc()).limit(1).with_for_update()
                
                result = await session.execute(stmt)
                task = result.scalar()
                
                if task:
                    task.status = 'processing'
                    task.attempts += 1
                    await session.commit()
                    return task
                return None

    async def save_success(self, task_id: int, data: Dict[str, Any]) -> None:
        """Save the successful result of a scrape task."""
        async with self.async_session_maker() as session:
            async with session.begin():
                result = ScrapeResult(
                    task_id=task_id,
                    title=data['title'],
                    price=data['price'],
                    currency=data['currency'],
                    confidence_score=data['score'],
                    meta_data=data['meta']
                )
                session.add(result)
                
                stmt = update(ScrapeTask).where(ScrapeTask.id == task_id).values(status='done')
                await session.execute(stmt)
                await session.commit()

    async def log_failure(self, task_id: int, error_msg: str) -> None:
        """Log a failure for a task."""
        async with self.async_session_maker() as session:
            async with session.begin():
                stmt = update(ScrapeTask).where(ScrapeTask.id == task_id).values(
                    status='failed', 
                    last_error=str(error_msg)[:500]
                )
                await session.execute(stmt)
                await session.commit()
