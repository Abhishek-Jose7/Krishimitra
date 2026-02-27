"""
Background Scheduler — Periodic Jobs

Runs background tasks inside the Flask process using APScheduler:
- Weather sync (every 6 hours)
- Price recording (daily)
- Price alert checking (hourly)
- Data cleanup (weekly)
"""

import logging
import datetime
import random
from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger('scheduler')

# The scheduler instance
scheduler = BackgroundScheduler()

# Flask app reference (set during init)
_flask_app = None


def init_scheduler(app):
    """
    Initialize and start the background scheduler.
    Must be called after app creation.
    """
    global _flask_app
    _flask_app = app

    # Job 1: Sync weather for all active districts (every 6 hours)
    scheduler.add_job(
        func=sync_weather_all_districts,
        trigger='interval',
        hours=6,
        id='weather_sync',
        name='Weather Sync',
        replace_existing=True,
    )

    # Job 2: Record daily prices for all mandis (daily at 6 PM)
    scheduler.add_job(
        func=sync_prices_all_mandis,
        trigger='cron',
        hour=18,
        id='price_sync',
        name='Price Sync',
        replace_existing=True,
    )

    # Job 3: Check price alerts (every hour)
    scheduler.add_job(
        func=check_price_alerts,
        trigger='interval',
        hours=1,
        id='alert_check',
        name='Price Alert Check',
        replace_existing=True,
    )

    # Job 4: Cleanup old data (weekly on Sunday at 3 AM)
    scheduler.add_job(
        func=cleanup_old_data,
        trigger='cron',
        day_of_week='sun',
        hour=3,
        id='data_cleanup',
        name='Data Cleanup',
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Background scheduler started with 4 jobs")


def shutdown_scheduler():
    """Gracefully shut down the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down")


def sync_weather_all_districts():
    """Fetch and store weather for all districts with active farmers."""
    if not _flask_app:
        return

    with _flask_app.app_context():
        try:
            from database.db import db
            from database.models import Farmer, WeatherHistory
            from services.weather_service import WeatherService

            # Get unique districts
            districts = db.session.query(Farmer.district).distinct().all()
            districts = [d[0] for d in districts if d[0]]

            if not districts:
                districts = ['Pune', 'Nashik', 'Nagpur']  # defaults

            count = 0
            for district in districts:
                try:
                    weather = WeatherService.get_weather(district)
                    if weather:
                        record = WeatherHistory(
                            district=district,
                            temperature=weather.get('temperature'),
                            humidity=weather.get('humidity'),
                            rainfall=weather.get('rainfall', 0),
                            condition=weather.get('condition'),
                        )
                        db.session.add(record)
                        count += 1
                except Exception as e:
                    logger.error(f"Weather sync failed for {district}: {e}")

            db.session.commit()
            logger.info(f"Weather sync complete: {count} districts updated")
        except Exception as e:
            logger.error(f"Weather sync job failed: {e}")


def sync_prices_all_mandis():
    """Record current prices for all crop/mandi combinations."""
    if not _flask_app:
        return

    with _flask_app.app_context():
        try:
            from database.db import db
            from database.models import PriceHistory
            from services.mandi_service import MandiService

            crops = ['Rice', 'Wheat', 'Maize', 'Soybean', 'Cotton', 'Onion']
            today = datetime.date.today()
            count = 0

            for crop in crops:
                prices = MandiService.get_nearby_prices(crop)
                for mandi_data in prices:
                    # Check if already recorded today
                    existing = PriceHistory.query.filter_by(
                        crop=crop, mandi=mandi_data['mandi'], date=today
                    ).first()

                    if not existing:
                        record = PriceHistory(
                            crop=crop,
                            mandi=mandi_data['mandi'],
                            district=mandi_data.get('district'),
                            price=mandi_data['today_price'],
                            date=today,
                            source='simulated',
                        )
                        db.session.add(record)
                        count += 1

            db.session.commit()
            logger.info(f"Price sync complete: {count} records added")
        except Exception as e:
            logger.error(f"Price sync job failed: {e}")


def check_price_alerts():
    """Check all active price alerts against current prices."""
    if not _flask_app:
        return

    with _flask_app.app_context():
        try:
            from services.notification_service import NotificationService
            triggered = NotificationService.check_and_trigger_alerts()
            if triggered > 0:
                logger.info(f"Price alerts: {triggered} alerts triggered")
        except Exception as e:
            logger.error(f"Alert check job failed: {e}")


def cleanup_old_data():
    """Delete records older than 365 days to keep DB size manageable."""
    if not _flask_app:
        return

    with _flask_app.app_context():
        try:
            from database.db import db
            from database.models import PriceHistory, WeatherHistory

            cutoff_date = datetime.date.today() - datetime.timedelta(days=365)
            cutoff_dt = datetime.datetime.combine(cutoff_date, datetime.time.min)

            price_deleted = PriceHistory.query.filter(PriceHistory.date < cutoff_date).delete()
            weather_deleted = WeatherHistory.query.filter(WeatherHistory.recorded_at < cutoff_dt).delete()

            db.session.commit()
            logger.info(f"Cleanup: deleted {price_deleted} price records, {weather_deleted} weather records")
        except Exception as e:
            logger.error(f"Cleanup job failed: {e}")


def get_scheduler_status():
    """Returns status of all scheduled jobs."""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            'id': job.id,
            'name': job.name,
            'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
            'trigger': str(job.trigger),
        })
    return {
        'running': scheduler.running,
        'jobs': jobs,
    }
