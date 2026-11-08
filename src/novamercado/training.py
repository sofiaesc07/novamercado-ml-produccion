import os
import json
import hashlib
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from novamercado.core import DATA, catalogs, features, business_cost

MODEL_DIR=Path(os.getenv('MODEL_DIR','/app/model_store'))

def train():
    cat=catalogs();df=pd.read_csv(DATA/'historico_ventas.csv');df['fecha']=pd.to_datetime(df.fecha)
    extra=Path(os.getenv('OBSERVATIONS_CSV','/app/model_store/observaciones.csv'))
    if extra.exists():
        obs=pd.read_csv(extra);obs['fecha']=pd.to_datetime(obs.fecha)
        df=pd.concat([df,obs],ignore_index=True).drop_duplicates(['fecha','tienda_id','familia_id'],keep='last')
    df=df.sort_values('fecha');dates=sorted(df.fecha.unique())
    if len(dates)<60:raise RuntimeError('histórico insuficiente')
    cutoff=dates[-min(45,max(14,len(dates)//5))]
    train_df=df[df.fecha<cutoff];valid=df[df.fecha>=cutoff]
    xtrain=features(train_df,cat);xval=features(valid,cat)
    ytrain=train_df.ventas.to_numpy();yval=valid.ventas.to_numpy()
    # Baseline: historical median by store and family.
    med=train_df.groupby(['tienda_id','familia_id']).ventas.median()
    baseline=np.array([med.get((r.tienda_id,r.familia_id),float(np.median(ytrain))) for r in valid.itertuples()])
    model=HistGradientBoostingRegressor(max_iter=130,max_leaf_nodes=31,learning_rate=.09,l2_regularization=5,random_state=42)
    model.fit(xtrain,ytrain)
    prediction=np.maximum(model.predict(xval),0)
    costs=cat['costos'].set_index('familia_id')
    factors={};suggestions=[]
    for family in cat['familias'].familia_id:
        mask=valid.familia_id.to_numpy()==family
        if not mask.any():continue
        candidates=np.arange(.7,1.81,.05)
        losses=[business_cost(yval[mask],np.ceil(prediction[mask]*factor),valid.familia_id.to_numpy()[mask],cat) for factor in candidates]
        factors[family]=float(candidates[int(np.argmin(losses))])
    suggestions=np.array([np.ceil(p*factors[f]) for p,f in zip(prediction,valid.familia_id)])
    base_suggest=np.array([np.ceil(p*factors[f]) for p,f in zip(baseline,valid.familia_id)])
    metrics={'mae_ml':float(mean_absolute_error(yval,prediction)),'rmse_ml':float(np.sqrt(mean_squared_error(yval,prediction))), 'mae_baseline':float(mean_absolute_error(yval,baseline)), 'costo_ml':business_cost(yval,suggestions,valid.familia_id,cat),'costo_baseline':business_cost(yval,base_suggest,valid.familia_id,cat),'validacion_desde':str(pd.Timestamp(cutoff).date()),'n_entrenamiento':len(train_df)}
    MODEL_DIR.mkdir(parents=True,exist_ok=True)
    artifact=MODEL_DIR/'candidate.joblib';joblib.dump({'model':model,'factors':factors,'metrics':metrics},artifact)
    return artifact,metrics

if __name__=='__main__':
    artifact,metrics=train();print(json.dumps(metrics,indent=2))
