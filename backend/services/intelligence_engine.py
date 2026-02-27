"""
Intelligence Engine — Region + Crop Type Awareness

Every farmer sees a DIFFERENT dashboard priority based on:
  1. Region (state) → what matters most locally
  2. Crop type → perishable vs grain → different advice cycles

This is the "brain" that decides WHAT to show, HOW prominently,
and HOW OFTEN to sync.
"""

import datetime
import random


class IntelligenceEngine:
    # ═══════════════════════════════════════
    # REGION PROFILES
    # ═══════════════════════════════════════
    REGION_PROFILES = {
        'Kerala': {
            'focus': 'weather_heavy',
            'label': 'Weather Intelligence',
            'description': 'Kerala receives 3000mm+ annual rainfall. Weather drives everything.',
            'primary_cards': ['weather_extended', 'rainfall_alert', 'flood_risk'],
            'secondary_cards': ['price_insight', 'sell_hold'],
            'weather_weight': 0.9,   # How important weather is (0-1)
            'market_weight': 0.4,
            'msp_weight': 0.3,
            'sync_interval_hours': 3,  # Sync weather every 3 hours
            'alerts': {
                'rainfall_threshold_mm': 60,
                'flood_risk_districts': ['Wayanad', 'Idukki', 'Ernakulam', 'Kottayam', 'Alappuzha'],
                'monsoon_months': [6, 7, 8, 9, 10],
            },
            'seasonal_advice': {
                'pre_monsoon': 'Secure storage. Harvest any standing crop immediately.',
                'monsoon': 'Monitor water levels daily. Avoid transport during heavy rain.',
                'post_monsoon': 'Check crop for moisture damage before selling.',
            },
        },
        'Karnataka': {
            'focus': 'volatility_mandi',
            'label': 'Market Volatility Watch',
            'description': 'Karnataka has high price swings + multiple competing mandis.',
            'primary_cards': ['volatility_alert', 'mandi_compare', 'price_trend'],
            'secondary_cards': ['weather', 'sell_hold'],
            'weather_weight': 0.4,
            'market_weight': 0.9,
            'msp_weight': 0.5,
            'sync_interval_hours': 6,
            'alerts': {
                'volatility_threshold': 0.15,
                'key_mandis': ['Hubli', 'Davangere', 'Mysuru', 'Belgaum', 'Shimoga', 'Bengaluru'],
            },
            'mandi_compare_config': {
                'show_top_n': 5,
                'include_transport_cost': True,
                'highlight_best_effective_price': True,
            },
        },
        'Tamil Nadu': {
            'focus': 'msp_govt',
            'label': 'MSP & Government Focus',
            'description': 'TN has strong procurement + UZHAVAR mandis. MSP matters most.',
            'primary_cards': ['msp_comparison', 'govt_procurement', 'sell_hold'],
            'secondary_cards': ['weather', 'mandi_compare'],
            'weather_weight': 0.4,
            'market_weight': 0.6,
            'msp_weight': 0.9,
            'sync_interval_hours': 12,
            'alerts': {
                'msp_floor_warning': True,
                'procurement_districts': ['Thanjavur', 'Tiruvarur', 'Nagapattinam', 'Cuddalore'],
            },
            'govt_schemes': {
                'uzhavar_sandhai': {
                    'label': 'Uzhavar Sandhai (Farmer Market)',
                    'benefit': 'Direct sale to consumers at higher price',
                    'eligibility': 'All registered farmers',
                },
                'free_insurance': {
                    'label': 'TN Crop Insurance',
                    'benefit': 'Free premium crop insurance for small farmers',
                    'eligibility': 'Land < 5 hectares',
                },
            },
        },
        'Maharashtra': {
            'focus': 'market_intelligence',
            'label': 'Market Intelligence',
            'description': 'MH is India\'s market hub. Onion/Soybean price swings = big money.',
            'primary_cards': ['price_insight', 'sell_hold', 'mandi_compare', 'volatility_alert'],
            'secondary_cards': ['weather', 'msp_comparison'],
            'weather_weight': 0.5,
            'market_weight': 0.95,
            'msp_weight': 0.6,
            'sync_interval_hours': 4,
            'alerts': {
                'price_spike_threshold': 10,  # % change in a day
                'key_mandis': ['Pune', 'Nashik', 'Nagpur', 'Aurangabad', 'Solapur'],
                'track_onion_separately': True,
            },
            'market_intel_config': {
                'show_weekly_trend': True,
                'show_arrivals_volume': True,
                'inter_mandi_arbitrage': True,
            },
        },
    }

    # Default fallback for unlisted states
    DEFAULT_REGION = {
        'focus': 'balanced',
        'label': 'Smart Dashboard',
        'description': 'Balanced view of weather, prices, and advice.',
        'primary_cards': ['weather', 'price_insight', 'sell_hold'],
        'secondary_cards': ['mandi_compare', 'msp_comparison'],
        'weather_weight': 0.5,
        'market_weight': 0.5,
        'msp_weight': 0.5,
        'sync_interval_hours': 8,
    }

    # ═══════════════════════════════════════
    # CROP TYPE PROFILES
    # ═══════════════════════════════════════
    CROP_PROFILES = {
        # ── PERISHABLE CROPS ──
        'Onion': {
            'type': 'perishable',
            'shelf_life_days': 14,
            'forecast_horizon': 'short',  # 7-14 day forecast
            'sync_interval_hours': 4,     # Sync every 4 hours
            'volatility_sensitive': True,
            'storage_critical': True,
            'msp_relevant': False,        # No MSP for onions
            'advice_style': 'urgent',
            'alerts': {
                'price_drop_threshold': 5,   # Alert if > 5% drop in a day
                'glut_warning': True,
                'cold_storage_advice': True,
            },
            'dashboard_cards': ['volatility_alert', 'daily_price', 'storage_countdown', 'sell_window'],
        },
        'Sugarcane': {
            'type': 'perishable',
            'shelf_life_days': 3,
            'forecast_horizon': 'short',
            'sync_interval_hours': 6,
            'volatility_sensitive': False,
            'storage_critical': False,
            'msp_relevant': True,         # FRP (Fair & Remunerative Price)
            'advice_style': 'urgent',
            'alerts': {
                'frp_tracking': True,
                'mill_payment_status': True,
            },
            'dashboard_cards': ['frp_status', 'mill_availability', 'transport_timing'],
        },
        'Cotton': {
            'type': 'semi_perishable',
            'shelf_life_days': 180,
            'forecast_horizon': 'long',
            'sync_interval_hours': 12,
            'volatility_sensitive': True,
            'storage_critical': False,
            'msp_relevant': True,
            'advice_style': 'strategic',
            'alerts': {
                'international_price_impact': True,
                'quality_grading_advice': True,
            },
            'dashboard_cards': ['msp_comparison', 'quality_premium', 'long_term_trend'],
        },
        'Groundnut': {
            'type': 'semi_perishable',
            'shelf_life_days': 60,
            'forecast_horizon': 'medium',
            'sync_interval_hours': 8,
            'volatility_sensitive': True,
            'storage_critical': True,
            'msp_relevant': True,
            'advice_style': 'balanced',
            'alerts': {
                'moisture_warning': True,
                'oil_content_price_impact': True,
            },
            'dashboard_cards': ['price_trend', 'storage_advice', 'msp_comparison'],
        },

        # ── GRAIN CROPS ──
        'Rice': {
            'type': 'grain',
            'shelf_life_days': 365,
            'forecast_horizon': 'long',   # 30-90 day forecast
            'sync_interval_hours': 12,    # Sync every 12 hours
            'volatility_sensitive': False,
            'storage_critical': True,
            'msp_relevant': True,
            'advice_style': 'patient',
            'alerts': {
                'msp_procurement_open': True,
                'storage_moisture_check': True,
            },
            'dashboard_cards': ['msp_comparison', 'long_term_trend', 'storage_optimization', 'sell_hold'],
        },
        'Wheat': {
            'type': 'grain',
            'shelf_life_days': 365,
            'forecast_horizon': 'long',
            'sync_interval_hours': 12,
            'volatility_sensitive': False,
            'storage_critical': True,
            'msp_relevant': True,
            'advice_style': 'patient',
            'alerts': {
                'msp_procurement_open': True,
                'storage_pest_warning': True,
            },
            'dashboard_cards': ['msp_comparison', 'long_term_trend', 'storage_optimization', 'sell_hold'],
        },
        'Maize': {
            'type': 'grain',
            'shelf_life_days': 180,
            'forecast_horizon': 'medium',
            'sync_interval_hours': 8,
            'volatility_sensitive': True,
            'storage_critical': True,
            'msp_relevant': True,
            'advice_style': 'balanced',
            'alerts': {
                'ethanol_demand_impact': True,
                'fungal_storage_warning': True,
            },
            'dashboard_cards': ['price_trend', 'msp_comparison', 'storage_advice', 'sell_hold'],
        },
        'Soybean': {
            'type': 'grain',
            'shelf_life_days': 120,
            'forecast_horizon': 'medium',
            'sync_interval_hours': 8,
            'volatility_sensitive': True,
            'storage_critical': True,
            'msp_relevant': True,
            'advice_style': 'balanced',
            'alerts': {
                'oil_price_correlation': True,
                'international_market_impact': True,
            },
            'dashboard_cards': ['price_trend', 'msp_comparison', 'volatility_watch', 'sell_hold'],
        },
    }

    DEFAULT_CROP = {
        'type': 'grain',
        'shelf_life_days': 90,
        'forecast_horizon': 'medium',
        'sync_interval_hours': 8,
        'volatility_sensitive': False,
        'storage_critical': False,
        'msp_relevant': True,
        'advice_style': 'balanced',
        'dashboard_cards': ['price_insight', 'sell_hold', 'msp_comparison'],
    }

    # ═══════════════════════════════════════
    # MSP DATA (2024-25 Kharif + Rabi)
    # ═══════════════════════════════════════
    MSP_DATA = {
        'Rice': {'msp': 2300, 'bonus_states': {'Tamil Nadu': 200, 'Telangana': 500}},
        'Wheat': {'msp': 2275, 'bonus_states': {'Madhya Pradesh': 200, 'Punjab': 100}},
        'Maize': {'msp': 2090, 'bonus_states': {}},
        'Soybean': {'msp': 4892, 'bonus_states': {'Madhya Pradesh': 200}},
        'Cotton': {'msp': 7121, 'bonus_states': {'Gujarat': 200}},
        'Sugarcane': {'msp': 340, 'bonus_states': {'Uttar Pradesh': 35, 'Maharashtra': 15}},
        'Groundnut': {'msp': 6783, 'bonus_states': {}},
        'Onion': {'msp': 0, 'bonus_states': {}},  # No MSP for onions
    }

    # ═══════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════
    @staticmethod
    def get_intelligence(state, crop, district=None, land_size=2.0, storage_available=False):
        """
        Returns a complete intelligence package for a farmer.
        This is what the dashboard endpoint calls.
        """
        region_profile = IntelligenceEngine.REGION_PROFILES.get(state, IntelligenceEngine.DEFAULT_REGION)
        crop_profile = IntelligenceEngine.CROP_PROFILES.get(crop, IntelligenceEngine.DEFAULT_CROP)

        # Merge region + crop to determine card ordering & weights
        card_priority = IntelligenceEngine._merge_card_priority(region_profile, crop_profile)

        # Generate region-specific alerts
        region_alerts = IntelligenceEngine._generate_region_alerts(state, region_profile, district)

        # Generate crop-specific alerts
        crop_alerts = IntelligenceEngine._generate_crop_alerts(crop, crop_profile, storage_available)

        # MSP context
        msp_context = IntelligenceEngine._get_msp_context(crop, state)

        # Sync recommendation
        sync_hours = min(
            region_profile.get('sync_interval_hours', 8),
            crop_profile.get('sync_interval_hours', 8),
        )

        return {
            # ── Strategy ──
            'region_focus': region_profile.get('focus', 'balanced'),
            'region_label': region_profile.get('label', 'Smart Dashboard'),
            'crop_type': crop_profile.get('type', 'grain'),
            'advice_style': crop_profile.get('advice_style', 'balanced'),
            'forecast_horizon': crop_profile.get('forecast_horizon', 'medium'),

            # ── Card ordering ──
            'card_priority': card_priority,

            # ── Weights (for scoring) ──
            'weights': {
                'weather': region_profile.get('weather_weight', 0.5),
                'market': region_profile.get('market_weight', 0.5),
                'msp': region_profile.get('msp_weight', 0.5),
            },

            # ── Alerts ──
            'region_alerts': region_alerts,
            'crop_alerts': crop_alerts,

            # ── MSP ──
            'msp': msp_context,

            # ── Sync ──
            'sync_interval_hours': sync_hours,
            'volatility_sensitive': crop_profile.get('volatility_sensitive', False),

            # ── Storage ──
            'shelf_life_days': crop_profile.get('shelf_life_days', 90),
            'storage_critical': crop_profile.get('storage_critical', False),

            # ── Government schemes (region-specific) ──
            'govt_schemes': region_profile.get('govt_schemes', {}),
        }

    # ═══════════════════════════════════════
    # PRIVATE: Merge card priority
    # ═══════════════════════════════════════
    @staticmethod
    def _merge_card_priority(region, crop):
        """
        Merges region primary_cards + crop dashboard_cards into a single
        priority-ordered list (no duplicates).
        """
        region_primary = region.get('primary_cards', [])
        region_secondary = region.get('secondary_cards', [])
        crop_cards = crop.get('dashboard_cards', [])

        # Start with region primary, then interleave crop-specific
        merged = []
        seen = set()

        for card in region_primary:
            if card not in seen:
                merged.append(card)
                seen.add(card)

        for card in crop_cards:
            if card not in seen:
                merged.append(card)
                seen.add(card)

        for card in region_secondary:
            if card not in seen:
                merged.append(card)
                seen.add(card)

        return merged

    # ═══════════════════════════════════════
    # PRIVATE: Region-specific alerts
    # ═══════════════════════════════════════
    @staticmethod
    def _generate_region_alerts(state, profile, district):
        alerts = []
        now = datetime.datetime.now()
        month = now.month

        if state == 'Kerala':
            alert_config = profile.get('alerts', {})
            monsoon_months = alert_config.get('monsoon_months', [])
            flood_districts = alert_config.get('flood_risk_districts', [])

            if month in monsoon_months:
                alerts.append({
                    'type': 'weather_warning',
                    'severity': 'high',
                    'icon': '🌧️',
                    'title': 'Monsoon Active',
                    'message': 'Heavy rainfall expected. Secure stored crop and avoid transport.',
                    'action': 'Check weather forecast before any market trip.',
                })

                if district and district in flood_districts:
                    alerts.append({
                        'type': 'flood_risk',
                        'severity': 'critical',
                        'icon': '🌊',
                        'title': f'Flood Risk — {district}',
                        'message': f'{district} is in a flood-prone zone. Take precautions.',
                        'action': 'Move stored grain to higher ground. Contact local authorities.',
                    })

            # Seasonal advice
            seasonal = profile.get('seasonal_advice', {})
            if month in [4, 5]:
                alerts.append({
                    'type': 'seasonal',
                    'severity': 'info',
                    'icon': '📋',
                    'title': 'Pre-Monsoon Advisory',
                    'message': seasonal.get('pre_monsoon', ''),
                })

        elif state == 'Karnataka':
            alerts.append({
                'type': 'volatility_watch',
                'severity': 'medium',
                'icon': '📊',
                'title': 'Price Volatility Active',
                'message': 'Karnataka mandis show high price variation. Compare before selling.',
                'action': 'Check at least 3 mandis before finalizing sale.',
            })

        elif state == 'Tamil Nadu':
            alerts.append({
                'type': 'msp_info',
                'severity': 'info',
                'icon': '🏛️',
                'title': 'Government Procurement Active',
                'message': 'Check if your district has active procurement centers.',
                'action': 'Visit nearest Uzhavar Sandhai for direct consumer sale.',
            })

        elif state == 'Maharashtra':
            alerts.append({
                'type': 'market_intel',
                'severity': 'medium',
                'icon': '📈',
                'title': 'Market Intelligence Update',
                'message': 'High arrival volumes in nearby mandis. Monitor prices closely.',
                'action': 'Compare prices across Pune, Nashik, and Nagpur mandis.',
            })

        return alerts

    # ═══════════════════════════════════════
    # PRIVATE: Crop-specific alerts
    # ═══════════════════════════════════════
    @staticmethod
    def _generate_crop_alerts(crop, profile, storage_available):
        alerts = []
        crop_type = profile.get('type', 'grain')
        shelf_life = profile.get('shelf_life_days', 90)

        if crop_type == 'perishable':
            alerts.append({
                'type': 'perishable_warning',
                'severity': 'high',
                'icon': '⏰',
                'title': f'{crop} — Sell within {shelf_life} days',
                'message': f'{crop} is perishable. Quality drops rapidly after harvest.',
                'action': f'Plan sale within {shelf_life} days of harvest.',
            })

            if profile.get('volatility_sensitive'):
                alerts.append({
                    'type': 'volatility_alert',
                    'severity': 'high',
                    'icon': '📉',
                    'title': 'Daily Price Check Required',
                    'message': f'{crop} prices can swing 5-15% in a single day.',
                    'action': 'Check prices daily. Set a target price and sell when reached.',
                })

        elif crop_type == 'grain':
            if storage_available:
                alerts.append({
                    'type': 'storage_optimization',
                    'severity': 'info',
                    'icon': '🏪',
                    'title': 'Storage Advantage',
                    'message': f'You can store {crop} for up to {shelf_life} days. Wait for MSP procurement or price peak.',
                    'action': 'Monitor moisture levels weekly. Check for pests monthly.',
                })
            else:
                alerts.append({
                    'type': 'no_storage_warning',
                    'severity': 'medium',
                    'icon': '⚠️',
                    'title': 'No Storage Available',
                    'message': f'Without storage, sell {crop} within 2 weeks of harvest.',
                    'action': 'Consider renting warehouse space or selling at MSP procurement center.',
                })

            if profile.get('msp_relevant') and profile.get('alerts', {}).get('msp_procurement_open'):
                alerts.append({
                    'type': 'msp_procurement',
                    'severity': 'info',
                    'icon': '🏛️',
                    'title': 'MSP Procurement Window',
                    'message': f'Check if government procurement for {crop} is open in your district.',
                    'action': 'Register at nearest procurement center. Carry land documents.',
                })

        return alerts

    # ═══════════════════════════════════════
    # PRIVATE: MSP Context
    # ═══════════════════════════════════════
    @staticmethod
    def _get_msp_context(crop, state):
        msp_entry = IntelligenceEngine.MSP_DATA.get(crop, {'msp': 0, 'bonus_states': {}})
        base_msp = msp_entry['msp']
        state_bonus = msp_entry['bonus_states'].get(state, 0)
        effective_msp = base_msp + state_bonus

        return {
            'base_msp': base_msp,
            'state_bonus': state_bonus,
            'effective_msp': effective_msp,
            'has_msp': base_msp > 0,
            'crop': crop,
        }
