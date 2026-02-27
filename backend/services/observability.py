"""
Observability — Structured Logging, API Metrics, Error Tracking

Provides production-grade observability:
- JSON-formatted structured logs
- Per-endpoint request/latency metrics
- Error tracking with context
"""

import time
import logging
import json
import traceback
from functools import wraps
from flask import request, g, jsonify


class JsonFormatter(logging.Formatter):
    """Structured JSON log formatter."""

    def format(self, record):
        log_data = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        if hasattr(record, 'extra_data'):
            log_data.update(record.extra_data)
        if record.exc_info and record.exc_info[0]:
            log_data['exception'] = traceback.format_exception(*record.exc_info)
        return json.dumps(log_data)


class ApiMetrics:
    """In-memory API metrics collector."""

    def __init__(self):
        self.request_count = {}    # endpoint -> count
        self.error_count = {}      # endpoint -> count
        self.latency_sum = {}      # endpoint -> total ms
        self.latency_max = {}      # endpoint -> max ms

    def record_request(self, endpoint, latency_ms, is_error=False):
        self.request_count[endpoint] = self.request_count.get(endpoint, 0) + 1
        self.latency_sum[endpoint] = self.latency_sum.get(endpoint, 0) + latency_ms
        self.latency_max[endpoint] = max(self.latency_max.get(endpoint, 0), latency_ms)
        if is_error:
            self.error_count[endpoint] = self.error_count.get(endpoint, 0) + 1

    def get_summary(self):
        summary = {}
        for endpoint in self.request_count:
            count = self.request_count[endpoint]
            summary[endpoint] = {
                'requests': count,
                'errors': self.error_count.get(endpoint, 0),
                'avg_latency_ms': round(self.latency_sum.get(endpoint, 0) / count, 2) if count > 0 else 0,
                'max_latency_ms': round(self.latency_max.get(endpoint, 0), 2),
                'error_rate_pct': round(self.error_count.get(endpoint, 0) / count * 100, 1) if count > 0 else 0,
            }
        return summary

    def get_totals(self):
        total_requests = sum(self.request_count.values())
        total_errors = sum(self.error_count.values())
        return {
            'total_requests': total_requests,
            'total_errors': total_errors,
            'error_rate_pct': round(total_errors / total_requests * 100, 1) if total_requests > 0 else 0,
        }


# Global metrics instance
metrics = ApiMetrics()


def setup_observability(app):
    """
    Configures structured logging and request tracking for a Flask app.
    Call this in create_app().
    """
    # Set up structured JSON logging
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    app.logger.handlers = [handler]
    app.logger.setLevel(logging.INFO)

    # Also set up the root logger for services
    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(logging.INFO)

    # Request timing middleware
    @app.before_request
    def before_request():
        g.start_time = time.time()

    @app.after_request
    def after_request(response):
        latency_ms = (time.time() - g.get('start_time', time.time())) * 1000
        endpoint = request.endpoint or request.path
        is_error = response.status_code >= 400

        metrics.record_request(endpoint, latency_ms, is_error)

        # Log every request
        app.logger.info(
            f"{request.method} {request.path} -> {response.status_code} ({latency_ms:.0f}ms)",
            extra={'extra_data': {
                'type': 'request',
                'method': request.method,
                'path': request.path,
                'status': response.status_code,
                'latency_ms': round(latency_ms, 2),
                'ip': request.remote_addr,
            }}
        )
        return response

    # Global error handler
    @app.errorhandler(Exception)
    def handle_exception(e):
        app.logger.error(
            f"Unhandled exception: {str(e)}",
            exc_info=True,
            extra={'extra_data': {
                'type': 'error',
                'error_class': e.__class__.__name__,
                'path': request.path,
                'method': request.method,
            }}
        )
        return jsonify({'error': 'Internal server error', 'message': str(e)}), 500

    # Metrics endpoint
    @app.route('/metrics')
    def metrics_endpoint():
        return jsonify({
            'totals': metrics.get_totals(),
            'per_endpoint': metrics.get_summary(),
        })

    return app
