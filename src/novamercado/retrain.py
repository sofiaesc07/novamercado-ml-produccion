"""Reentrenamiento con evaluación prospectiva independiente de MLflow."""
import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sqlalchemy import text

from novamercado.core import DATA, business_cost, catalogs, features
from novamercado.database import engine
from novamercado.registry import NAME, champion, client, download, publish
from novamercado.training import train

MIN_EVALUATION_DAYS = 7
MIN_EVALUATION_ROWS = 50


def _independent_observations(cat):
    """Use only observations after the original historical dataset ends."""
    raw = pd.read_csv(DATA / 'historico_ventas.csv', usecols=['fecha'])
    last_historical_day = pd.to_datetime(raw['fecha']).max()
    observations = Path(os.getenv('OBSERVATIONS_CSV', '/app/model_store/observaciones.csv'))
    if not observations.exists():
        return pd.DataFrame(), last_historical_day
    df = pd.read_csv(observations)
    if df.empty:
        return df, last_historical_day
    df['fecha'] = pd.to_datetime(df['fecha'])
    df = df[df['fecha'] > last_historical_day].copy()
    df = df.drop_duplicates(['fecha', 'tienda_id', 'familia_id'], keep='last')
    return df, last_historical_day


def _score(model_bundle, frame, cat, fixed_factors):
    """Compare model predictions using the SAME frozen ordering policy."""
    estimate = np.maximum(model_bundle['model'].predict(features(frame, cat)), 0)
    suggested = np.ceil([
        value * fixed_factors[str(family)]
        for value, family in zip(estimate, frame['familia_id'])
    ])
    return business_cost(frame['ventas'], suggested, frame['familia_id'], cat)


def _compare(incumbent, candidate):
    """Require enough post-history outcomes and exclude them from ML training."""
    cat = catalogs()
    frame, historical_end = _independent_observations(cat)
    distinct_days = frame['fecha'].nunique() if not frame.empty else 0
    if len(frame) < MIN_EVALUATION_ROWS or distinct_days < MIN_EVALUATION_DAYS:
        return False, 0.0, (
            f'Sin muestra prospectiva suficiente: {len(frame)} filas, '
            f'{distinct_days} dias despues de {historical_end.date()}. '
            f'Se requieren {MIN_EVALUATION_ROWS} filas y {MIN_EVALUATION_DAYS} dias.'
        )
    # Important: the current training routine uses recent observations for its
    # factor calibration. Freeze both policies at incumbent factors here to
    # prevent candidate policy tuning from giving an unfair advantage.
    factors = {str(k): float(v) for k, v in incumbent['factors'].items()}
    families = {str(v) for v in frame['familia_id'].unique()}
    if not families.issubset(factors):
        return False, 0.0, 'Faltan factores vigentes para algunas familias.'
    # The candidate's current train() uses a temporal cutoff that could put
    # prospectively observed dates into its training split in later retrains.
    # Do not promote unless the candidate's training cutoff precedes all
    # prospective observations; metrics include the actual cutoff.
    candidate_cutoff = pd.Timestamp(candidate['metrics']['validacion_desde'])
    if not bool((frame['fecha'] >= candidate_cutoff).all()):
        return False, 0.0, 'La muestra de evaluacion se solapa con el entrenamiento candidato.'
    incumbent_cost = _score(incumbent, frame, cat, factors)
    candidate_cost = _score(candidate, frame, cat, factors)
    improvement = (incumbent_cost - candidate_cost) / max(incumbent_cost, 1e-9)
    return True, improvement, (
        f'Comparacion en {len(frame)} ventas y {distinct_days} dias posteriores '
        f'al historico, politica de inventario fija: costo champion={incumbent_cost:.4f}, '
        f'costo candidato={candidate_cost:.4f}, mejora={improvement:.2%}.'
    )


def execute(runid):
    with engine.begin() as conn:
        rows = conn.execute(text(
            'SELECT fecha,tienda_id,familia_id,ventas FROM observaciones'
        )).mappings().all()
    if rows:
        observations = pd.DataFrame(rows)
        # No promotion flag is stored in observations; retain this limitation.
        observations['en_promocion'] = 0
        target = Path(os.getenv('OBSERVATIONS_CSV', '/app/model_store/observaciones.csv'))
        target.parent.mkdir(parents=True, exist_ok=True)
        observations.to_csv(target, index=False)
    try:
        active = champion()
        incumbent = joblib.load(download(active.version))
        artifact, metrics = train()
        candidate = joblib.load(artifact)
        comparable, improvement, detail = _compare(incumbent, candidate)
        # The evaluation uses frozen incumbent ordering factors for both
        # models. Publish the same factors, so evaluated and deployed
        # candidate behavior cannot diverge.
        candidate['factors'] = incumbent['factors']
        joblib.dump(candidate, artifact)
        new_version = publish(artifact, metrics)
        promoted = bool(comparable and improvement >= 0.02)
        version = str(active.version)
        if promoted:
            registry = client()
            registry.set_registered_model_alias(NAME, 'anterior', active.version)
            registry.set_registered_model_alias(NAME, 'champion', new_version)
            download(new_version)
            version = str(new_version)
        reason = detail + ' Umbral de promocion: 2%.'
        with engine.begin() as conn:
            conn.execute(text(
                'UPDATE entrenamientos SET estado=:s, promovido=:p, '
                'version=:v, motivo=:m WHERE id=:id'
            ), {'s': 'exitoso', 'p': promoted, 'v': version,
                'm': reason[:500], 'id': runid})
    except Exception as exc:
        with engine.begin() as conn:
            conn.execute(text(
                'UPDATE entrenamientos SET estado=:s,promovido=:p,'
                'version=:v,motivo=:m WHERE id=:id'
            ), {'s': 'fallido', 'p': False, 'v': None,
                'm': str(exc)[:500], 'id': runid})
        raise
