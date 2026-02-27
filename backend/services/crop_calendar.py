"""
Crop Calendar — Season-Aware Recommendation Adjustment

Tracks sowing, growing, harvest, and post-harvest phases for major crops
across Indian states. Adjusts recommendations based on where the farmer
is in the crop cycle.
"""

import datetime


class CropCalendar:

    # Crop calendar data: per crop per region group
    # months are 1-indexed (Jan=1, Dec=12)
    CALENDAR = {
        'Rice': {
            'kharif': {  # Most of India
                'sowing': [6, 7],          # Jun-Jul
                'growing': [7, 8, 9],      # Jul-Sep
                'harvest': [10, 11],       # Oct-Nov
                'post_harvest': [12, 1, 2], # Dec-Feb
                'peak_arrival': [11, 12],  # Nov-Dec
                'states': ['Maharashtra', 'Karnataka', 'Tamil Nadu', 'Andhra Pradesh',
                           'Telangana', 'West Bengal', 'Odisha', 'Bihar', 'UP'],
            },
            'rabi': {  # Some southern states grow rabi rice
                'sowing': [11, 12],
                'growing': [1, 2, 3],
                'harvest': [3, 4],
                'post_harvest': [4, 5, 6],
                'peak_arrival': [4, 5],
                'states': ['Tamil Nadu', 'Kerala', 'Andhra Pradesh'],
            },
        },
        'Wheat': {
            'rabi': {
                'sowing': [10, 11],
                'growing': [12, 1, 2],
                'harvest': [3, 4],
                'post_harvest': [4, 5, 6],
                'peak_arrival': [4, 5],
                'states': ['Punjab', 'Haryana', 'UP', 'Madhya Pradesh',
                           'Rajasthan', 'Maharashtra', 'Gujarat', 'Bihar'],
            },
        },
        'Maize': {
            'kharif': {
                'sowing': [6, 7],
                'growing': [7, 8, 9],
                'harvest': [9, 10],
                'post_harvest': [10, 11, 12],
                'peak_arrival': [10, 11],
                'states': ['Karnataka', 'Rajasthan', 'Madhya Pradesh', 'Bihar',
                           'UP', 'Maharashtra', 'Andhra Pradesh'],
            },
            'rabi': {
                'sowing': [10, 11],
                'growing': [12, 1, 2],
                'harvest': [2, 3],
                'post_harvest': [3, 4, 5],
                'peak_arrival': [3, 4],
                'states': ['Bihar', 'Andhra Pradesh', 'Karnataka'],
            },
        },
        'Soybean': {
            'kharif': {
                'sowing': [6, 7],
                'growing': [7, 8, 9],
                'harvest': [10, 11],
                'post_harvest': [11, 12, 1],
                'peak_arrival': [11, 12],
                'states': ['Madhya Pradesh', 'Maharashtra', 'Rajasthan', 'Karnataka'],
            },
        },
        'Cotton': {
            'kharif': {
                'sowing': [5, 6],
                'growing': [7, 8, 9, 10],
                'harvest': [10, 11, 12],
                'post_harvest': [1, 2, 3],
                'peak_arrival': [11, 12, 1],
                'states': ['Gujarat', 'Maharashtra', 'Telangana', 'Andhra Pradesh',
                           'Rajasthan', 'Madhya Pradesh', 'Haryana', 'Punjab'],
            },
        },
        'Onion': {
            'kharif': {
                'sowing': [6, 7],
                'growing': [8, 9],
                'harvest': [10, 11],
                'post_harvest': [11, 12],
                'peak_arrival': [11, 12],
                'states': ['Maharashtra', 'Karnataka', 'Madhya Pradesh'],
            },
            'rabi': {
                'sowing': [11, 12],
                'growing': [1, 2],
                'harvest': [3, 4, 5],
                'post_harvest': [5, 6],
                'peak_arrival': [4, 5],
                'states': ['Maharashtra', 'Karnataka', 'Gujarat', 'Rajasthan'],
            },
        },
        'Sugarcane': {
            'annual': {
                'sowing': [1, 2, 10],  # planted Jan-Feb or Oct
                'growing': [3, 4, 5, 6, 7, 8, 9, 10, 11],  # 10-12 month crop
                'harvest': [11, 12, 1, 2, 3, 4],  # crushing season
                'post_harvest': [5, 6],
                'peak_arrival': [12, 1, 2, 3],
                'states': ['UP', 'Maharashtra', 'Karnataka', 'Tamil Nadu', 'Gujarat'],
            },
        },
        'Groundnut': {
            'kharif': {
                'sowing': [6, 7],
                'growing': [7, 8, 9],
                'harvest': [10, 11],
                'post_harvest': [11, 12, 1],
                'peak_arrival': [11, 12],
                'states': ['Gujarat', 'Rajasthan', 'Andhra Pradesh', 'Tamil Nadu',
                           'Karnataka', 'Maharashtra'],
            },
        },
    }

    # Season-specific advice templates
    PHASE_ADVICE = {
        'pre_sowing': {
            'message': 'Seeds and inputs demand rising. Good time to sell stored crop from last season.',
            'market_impact': 'Prices for stored crops tend to be higher as supply reduces.',
            'priority': 'sell_stored',
        },
        'sowing': {
            'message': 'Farmers are sowing. Market supply reducing. Prices may start rising.',
            'market_impact': 'Decreasing market arrivals typically support price recovery.',
            'priority': 'monitor',
        },
        'growing': {
            'message': 'Crop is growing. Market prices depend on weather and existing stocks.',
            'market_impact': 'Weather events during this phase heavily impact future supply.',
            'priority': 'weather_watch',
        },
        'harvest': {
            'message': 'Harvest season. Many farmers selling simultaneously. Prices often dip.',
            'market_impact': 'Peak market arrivals. If you have storage, consider holding.',
            'priority': 'storage_decision',
        },
        'post_harvest': {
            'message': 'Peak arrivals tapering off. Prices typically stabilize and may start rising.',
            'market_impact': 'Supply reduces as stored quantities deplete. Patient sellers benefit.',
            'priority': 'price_recovery',
        },
    }

    @classmethod
    def get_current_phase(cls, crop, state, month=None):
        """
        Determines what farming phase the crop is in for the given state.
        Returns: { phase, season_type, advice, days_to_next_phase }
        """
        if month is None:
            month = datetime.date.today().month

        crop_data = cls.CALENDAR.get(crop, {})
        if not crop_data:
            return {
                'phase': 'unknown',
                'season_type': 'unknown',
                'advice': cls.PHASE_ADVICE.get('growing', {}),
                'days_to_next_phase': None,
                'crop_supported': False,
            }

        # Find the matching season for this state
        matched_season = None
        matched_data = None
        for season_type, data in crop_data.items():
            if state in data.get('states', []):
                matched_season = season_type
                matched_data = data
                break

        # Fallback to first available season
        if not matched_data:
            matched_season = list(crop_data.keys())[0]
            matched_data = crop_data[matched_season]

        # Determine current phase
        current_phase = 'pre_sowing'  # default
        for phase in ['sowing', 'growing', 'harvest', 'post_harvest']:
            if month in matched_data.get(phase, []):
                current_phase = phase
                break

        # If not in any defined phase, it's pre-sowing
        all_active_months = set()
        for phase in ['sowing', 'growing', 'harvest', 'post_harvest']:
            all_active_months.update(matched_data.get(phase, []))
        if month not in all_active_months:
            current_phase = 'pre_sowing'

        # Calculate days to next phase
        phase_order = ['sowing', 'growing', 'harvest', 'post_harvest', 'pre_sowing']
        current_idx = phase_order.index(current_phase) if current_phase in phase_order else 0
        next_phase = phase_order[(current_idx + 1) % len(phase_order)]

        next_months = matched_data.get(next_phase, [])
        if not next_months and next_phase == 'pre_sowing':
            # Pre-sowing is the gap; next phase wraps to sowing
            next_months = matched_data.get('sowing', [])

        days_to_next = None
        if next_months:
            today = datetime.date.today()
            for nm in sorted(next_months):
                target_month = nm
                target_year = today.year if target_month >= today.month else today.year + 1
                target_date = datetime.date(target_year, target_month, 1)
                diff = (target_date - today).days
                if diff > 0:
                    days_to_next = diff
                    break

        is_peak_arrival = month in matched_data.get('peak_arrival', [])

        return {
            'phase': current_phase,
            'season_type': matched_season,
            'advice': cls.PHASE_ADVICE.get(current_phase, {}),
            'days_to_next_phase': days_to_next,
            'next_phase': next_phase,
            'is_peak_arrival_period': is_peak_arrival,
            'crop_supported': True,
        }

    @classmethod
    def adjust_recommendation(cls, recommendation, crop, state):
        """
        Modifies a recommendation dict based on current crop phase.
        Adds season_context with phase-aware adjustments.
        """
        phase_info = cls.get_current_phase(crop, state)
        phase = phase_info['phase']
        advice = phase_info.get('advice', {})

        season_context = {
            'current_phase': phase,
            'season_type': phase_info.get('season_type'),
            'phase_message': advice.get('message', ''),
            'market_impact': advice.get('market_impact', ''),
            'days_to_next_phase': phase_info.get('days_to_next_phase'),
            'next_phase': phase_info.get('next_phase'),
            'is_peak_arrival': phase_info.get('is_peak_arrival_period', False),
        }

        # Adjust recommendation based on phase
        if phase == 'harvest' and recommendation.get('recommendation') == 'HOLD':
            season_context['phase_adjustment'] = (
                'REINFORCED: Holding during harvest season is wise — '
                'prices typically recover 10-20% once peak arrivals end.'
            )
        elif phase == 'harvest' and recommendation.get('recommendation') == 'SELL NOW':
            season_context['phase_adjustment'] = (
                'CAUTION: Selling during peak harvest means competing with high supply. '
                'Consider holding 2-4 weeks if storage allows.'
            )
        elif phase == 'post_harvest':
            season_context['phase_adjustment'] = (
                'Arrivals reducing. Prices should stabilize or rise. '
                'Good time to sell stored crop.'
            )
        elif phase == 'pre_sowing':
            season_context['phase_adjustment'] = (
                'Next season preparations starting. Sell stored crop now '
                'to fund input purchases.'
            )
        else:
            season_context['phase_adjustment'] = advice.get('message', '')

        recommendation['season_context'] = season_context
        return recommendation
