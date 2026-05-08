from datetime import datetime, timedelta
from sqlalchemy import func

from database import get_db_session
from models import Deal, PostLog, Commission
from logging import logger

def get_daily_stats(date: datetime.date | None = None) -> dict:
    """Returns daily statistics for scraped deals, posted deals, and errors."""
    if date is None:
        date = datetime.utcnow().date()

    start_of_day = datetime.combine(date, datetime.min.time())
    end_of_day = datetime.combine(date, datetime.max.time())

    with get_db_session() as session:
        deals_scraped = session.query(Deal).filter(Deal.posted_at >= start_of_day, Deal.posted_at <= end_of_day).count()
        deals_posted_telegram = session.query(PostLog).filter(
            PostLog.timestamp >= start_of_day,
            PostLog.timestamp <= end_of_day,
            PostLog.channel == 'telegram',
            PostLog.status == 'success'
        ).distinct(PostLog.deal_id).count()
        deals_posted_whatsapp = session.query(PostLog).filter(
            PostLog.timestamp >= start_of_day,
            PostLog.timestamp <= end_of_day,
            PostLog.channel == 'whatsapp',
            PostLog.status == 'success'
        ).distinct(PostLog.deal_id).count()

        errors = session.query(PostLog).filter(
            PostLog.timestamp >= start_of_day,
            PostLog.timestamp <= end_of_day,
            PostLog.status == 'error'
        ).all()
        error_details = [{"deal_id": e.deal_id, "channel": e.channel, "message": e.error_message} for e in errors]

        # Categories distribution
        category_counts = session.query(Deal.category, func.count(Deal.id)).filter(
            Deal.posted_at >= start_of_day, Deal.posted_at <= end_of_day
        ).group_by(Deal.category).all()
        categories = {cat: count for cat, count in category_counts}

    stats = {
        "date": date.isoformat(),
        "deals_scraped": deals_scraped,
        "deals_posted_telegram": deals_posted_telegram,
        "deals_posted_whatsapp": deals_posted_whatsapp,
        "channels": {"telegram": deals_posted_telegram, "whatsapp": deals_posted_whatsapp},
        "categories": categories,
        "errors": error_details
    }
    logger.debug(f"Daily stats for {date}: {stats}")
    return stats

def get_revenue_stats() -> dict:
    """Returns total revenue statistics (today, this week, this month, total)."""
    now = datetime.utcnow()
    today_start = datetime.combine(now.date(), datetime.min.time())
    this_week_start = now - timedelta(days=now.weekday()) # Monday as start of week
    this_month_start = datetime(now.year, now.month, 1)

    with get_db_session() as session:
        today_revenue = session.query(func.sum(Commission.amount)).filter(Commission.date_tracked >= today_start).scalar() or 0.0
        this_week_revenue = session.query(func.sum(Commission.amount)).filter(Commission.date_tracked >= this_week_start).scalar() or 0.0
        this_month_revenue = session.query(func.sum(Commission.amount)).filter(Commission.date_tracked >= this_month_start).scalar() or 0.0
        total_revenue = session.query(func.sum(Commission.amount)).scalar() or 0.0

    stats = {
        "today": round(today_revenue, 2),
        "this_week": round(this_week_revenue, 2),
        "this_month": round(this_month_revenue, 2),
        "total": round(total_revenue, 2)
    }
    logger.debug(f"Revenue stats: {stats}")
    return stats

def print_dashboard():
    """Prints formatted dashboard statistics to the terminal."""
    today = datetime.utcnow().date()
    daily_stats = get_daily_stats(today)
    revenue_stats = get_revenue_stats()

    print("\n--- Clube USA Dashboard ---")
    print(f"Data: {daily_stats['date']}")
    print("-" * 30)

    print("\n[ Estatísticas Diárias ]")
    print(f"  Deals Raspados: {daily_stats['deals_scraped']}")
    print(f"  Deals Postados (Telegram): {daily_stats['deals_posted_telegram']}")
    print(f"  Deals Postados (WhatsApp): {daily_stats['deals_posted_whatsapp']}")
    print("  Categorias:")
    for category, count in daily_stats['categories'].items():
        print(f"    - {category}: {count}")
    print(f"  Erros de Postagem: {len(daily_stats['errors'])}")
    for error in daily_stats['errors']:
        print(f"    - [Deal {error['deal_id']} / {error['channel']}]: {error['message']}")

    print("\n[ Estatísticas de Receita ]")
    print(f"  Hoje: R${revenue_stats['today']:.2f}")
    print(f"  Esta Semana: R${revenue_stats['this_week']:.2f}")
    print(f"  Este Mês: R${revenue_stats['this_month']:.2f}")
    print(f"  Total: R${revenue_stats['total']:.2f}")
    print("-" * 30)
    print("Dashboard atualizado.")

if __name__ == '__main__':
    # This block is for direct execution to see the dashboard
    from database import init_db
    init_db() # Ensure DB is ready
    print_dashboard()