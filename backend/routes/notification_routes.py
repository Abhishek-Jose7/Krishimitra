"""
Notification Routes — Price Alert API endpoints

POST /notifications/alert          — Create new price alert
GET  /notifications/alerts/<id>    — Get farmer's alerts
POST /notifications/alerts/<id>/read — Mark alert as read
DELETE /notifications/alerts/<id>  — Deactivate an alert
"""

from flask import Blueprint, request, jsonify
from services.notification_service import NotificationService

notification_bp = Blueprint('notification', __name__, url_prefix='/notifications')


@notification_bp.route('/alert', methods=['POST'])
def create_alert():
    data = request.json
    farmer_id = data.get('farmer_id')
    crop = data.get('crop')
    mandi = data.get('mandi')
    target_price = data.get('target_price')
    direction = data.get('direction', 'above')

    if not all([farmer_id, crop, mandi, target_price]):
        return jsonify({'error': 'farmer_id, crop, mandi, and target_price are required'}), 400

    try:
        target_price = float(target_price)
    except (ValueError, TypeError):
        return jsonify({'error': 'target_price must be a number'}), 400

    alert = NotificationService.create_price_alert(
        farmer_id=farmer_id,
        crop=crop,
        mandi=mandi,
        target_price=target_price,
        direction=direction,
    )
    return jsonify({'alert': alert, 'message': f'Price alert created. You will be notified when {crop} goes {direction} ₹{target_price}'}), 201


@notification_bp.route('/alerts/<int:farmer_id>', methods=['GET'])
def get_alerts(farmer_id):
    include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
    alerts = NotificationService.get_farmer_alerts(farmer_id, include_inactive)
    unread = NotificationService.get_triggered_unread(farmer_id)
    return jsonify({
        'alerts': alerts,
        'unread_count': len(unread),
        'unread': unread,
    })


@notification_bp.route('/alerts/<int:alert_id>/read', methods=['POST'])
def mark_read(alert_id):
    result = NotificationService.mark_alert_read(alert_id)
    if result:
        return jsonify({'alert': result})
    return jsonify({'error': 'Alert not found'}), 404


@notification_bp.route('/alerts/<int:alert_id>', methods=['DELETE'])
def deactivate_alert(alert_id):
    result = NotificationService.deactivate_alert(alert_id)
    if result:
        return jsonify({'alert': result, 'message': 'Alert deactivated'})
    return jsonify({'error': 'Alert not found'}), 404
