from typing import Dict, Any, Tuple, List

# Adapter to call mlapp.predictor with app-level feature dicts
from mlapp.predictor import predict_one, predict_batch

APP_TO_KOI = {
    'orbital_period': 'koi_period',
    'transit_duration': 'koi_duration',
    'transit_depth': 'koi_depth',
    'stellar_effective_temperature': 'koi_steff',
    'planetary_radius': 'koi_prad',
    'stellar_radius': 'koi_srad',
    'equilibrium_temperature': 'koi_teq',
    'impact_parameter': 'koi_impact',
}


def predict_with_kepler_model(features: Dict[str, Any]) -> Tuple[str, float, Dict[str, float]]:
    # Map app fields to koi_* expected by the model
    payload: Dict[str, Any] = {}
    for app_key, koi_key in APP_TO_KOI.items():
        if app_key in features:
            payload[koi_key] = features[app_key]

    result = predict_one(payload)

    # Binary model: probability = P(planet), label in {0,1}
    p_planet = float(result.get('probability', 0.0))
    y_hat = int(result.get('label', 0))
    label = 'CONFIRMED' if y_hat == 1 else 'FALSE_POSITIVE'

    details = {
        'probability_confirmed': p_planet,
        'probability_candidate': 0.0,
        'probability_false_positive': 1.0 - p_planet,
    }
    return label, (p_planet if y_hat == 1 else 1.0 - p_planet), details


def batch_probability_from_candidates(candidates) -> List[Dict[str, Any]]:
    """Compute probability for a queryset of ExoplanetCandidate using koi_* from additional_data.

    Returns list of dicts with meta and probability, sorted ascending by probability.
    """
    records: List[Dict[str, Any]] = []
    metas: List[Dict[str, Any]] = []
    for c in candidates:
        ad = c.additional_data or {}
        payload: Dict[str, Any] = {}
        # Prefer values from additional_data if present
        for app_key, koi_key in APP_TO_KOI.items():
            if koi_key in ad:
                payload[koi_key] = ad[koi_key]
        # Fallback to model fields when missing in additional_data
        if 'koi_period' not in payload and getattr(c, 'orbital_period', None) is not None:
            payload['koi_period'] = c.orbital_period
        if 'koi_duration' not in payload and getattr(c, 'transit_duration', None) is not None:
            payload['koi_duration'] = c.transit_duration
        if 'koi_depth' not in payload and getattr(c, 'transit_depth', None) is not None:
            payload['koi_depth'] = c.transit_depth
        if 'koi_steff' not in payload and getattr(c, 'stellar_effective_temperature', None) is not None:
            payload['koi_steff'] = c.stellar_effective_temperature
        if 'koi_prad' not in payload and getattr(c, 'planetary_radius', None) is not None:
            payload['koi_prad'] = c.planetary_radius
        if 'koi_srad' not in payload and getattr(c, 'stellar_radius', None) is not None:
            payload['koi_srad'] = c.stellar_radius
        if 'koi_teq' not in payload and getattr(c, 'equilibrium_temperature', None) is not None:
            payload['koi_teq'] = c.equilibrium_temperature
        if 'koi_impact' not in payload and getattr(c, 'impact_parameter', None) is not None:
            payload['koi_impact'] = c.impact_parameter
        # minimal required keys
        if not payload:
            continue
        records.append(payload)
        metas.append({
            'candidate_id': c.id,
            'object_id': ad.get('object_id'),
            'kepoi_name': ad.get('kepoi_name'),
            'kepler_name': ad.get('kepler_name'),
            'kepid': ad.get('kepid'),
            'koi_disposition': ad.get('koi_disposition'),
            'koi_period': ad.get('koi_period'),
            'koi_duration': ad.get('koi_duration'),
            'koi_depth': ad.get('koi_depth'),
            'koi_model_snr': ad.get('koi_model_snr'),
            'duty_cycle': ad.get('duty_cycle'),
            'koi_prad': ad.get('koi_prad'),
        })

    if not records:
        return []

    df = predict_batch(records)
    out: List[Dict[str, Any]] = []
    for i in range(len(df)):
        item = metas[i].copy()
        p_planet = float(df.iloc[i].get('probability', 0.0))
        y_hat = int(df.iloc[i].get('label', 0))
        label = 'CONFIRMED' if y_hat == 1 else 'FALSE_POSITIVE'

        item['probability_confirmed'] = p_planet
        item['probability_candidate'] = 0.0
        item['probability_false_positive'] = 1.0 - p_planet
        item['label'] = label
        item['probability'] = p_planet if y_hat == 1 else (1.0 - p_planet)
        out.append(item)

    out.sort(key=lambda x: x['probability'])
    return out