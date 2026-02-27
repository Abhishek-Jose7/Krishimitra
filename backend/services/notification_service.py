"""
Notification Service — Price Alert Management

Manages farmer price alerts: create, check thresholds against
current prices, trigger notifications, track read status.
"""

import datetime
from database.db import db
from database.models import PriceAlert, Farmer
from services.mandi_service import MandiService


class NotificationService:

    @staticmethod
    def create_price_alert(farmer_id, crop, mandi, target_price, direction='above'):
        """
        Creates a new price alert for a farmer.
        direction: 'above' (notify when price goes above target)
                   'below' (notify when price drops below target)
        """
        alert = PriceAlert(
            farmer_id=farmer_id,
            crop=crop,
            mandi=mandi,
            target_price=target_price,
            direction=direction,
            is_active=True,
            is_read=False,
        )
        db.session.add(alert)
        db.session.commit()
        return alert.to_dict()

    @staticmethod
    def check_and_trigger_alerts():
        """
        Called by scheduler. Checks all active alerts against current prices.
        Triggers alerts that match conditions.
        Returns count of newly triggered alerts.
        """
        active_alerts = PriceAlert.query.filter_by(is_active=True).all()
        triggered_count = 0

        # Cache prices to avoid redundant lookups
        price_cache = {}

        for alert in active_alerts:
            cache_key = f"{alert.crop}_{alert.mandi}"
            if cache_key not in price_cache:
                # Get current price from mandi service
                prices = MandiService.get_nearby_prices(alert.crop)
                mandi_price = next(
                    (p['today_price'] for p in prices if p['mandi'] == alert.mandi),
                    None
                )
                price_cache[cache_key] = mandi_price

            current_price = price_cache.get(cache_key)
            if current_price is None:
                continue

            should_trigger = False
            if alert.direction == 'above' and current_price >= alert.target_price:
                should_trigger = True
            elif alert.direction == 'below' and current_price <= alert.target_price:
                should_trigger = True

            if should_trigger:
                alert.is_active = False
                alert.triggered_at = datetime.datetime.utcnow()
                triggered_count += 1

                # Log notification (placeholder for SMS/push)
                _send_notification(
                    alert.farmer_id,
                    f"🔔 Price Alert: {alert.crop} at {alert.mandi} is now ₹{current_price:.0f}/Q "
                    f"({'above' if alert.direction == 'above' else 'below'} your target of ₹{alert.target_price:.0f})"
                )

        db.session.commit()
        return triggered_count

    @staticmethod
    def get_farmer_alerts(farmer_id, include_inactive=False):
        """Returns all alerts for a farmer."""
        query = PriceAlert.query.filter_by(farmer_id=farmer_id)
        if not include_inactive:
            query = query.filter(
                (PriceAlert.is_active == True) | (PriceAlert.triggered_at.isnot(None))
            )
        alerts = query.order_by(PriceAlert.created_at.desc()).all()
        return [a.to_dict() for a in alerts]

    @staticmethod
    def get_triggered_unread(farmer_id):
        """Returns triggered but unread alerts."""
        alerts = (
            PriceAlert.query
            .filter_by(farmer_id=farmer_id, is_read=False)
            .filter(PriceAlert.triggered_at.isnot(None))
            .all()
        )
        return [a.to_dict() for a in alerts]

    @staticmethod
    def mark_alert_read(alert_id):
        """Mark an alert as read."""
        alert = PriceAlert.query.get(alert_id)
        if alert:
            alert.is_read = True
            db.session.commit()
            return alert.to_dict()
        return None

    @staticmethod
    def deactivate_alert(alert_id):
        """Cancel an active alert."""
        alert = PriceAlert.query.get(alert_id)
        if alert:
            alert.is_active = False
            db.session.commit()
            return alert.to_dict()
        return None


def _send_notification(farmer_id, message):
    """
    Placeholder for actual notification delivery.
    In production, this would:
    1. Send SMS via Twilio/MSG91
    2. Send push notification via FCM
    3. Store in notification inbox
    For now, just logs it.
    """
    import logging
    logger = logging.getLogger('notifications')
    logger.info(f"NOTIFICATION [farmer={farmer_id}]: {message}")
