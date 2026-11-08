import pytest
from novamercado.core import sanitize, catalogs

def base():
    return {'tienda_id':5,'fecha':'2026-03-01','familias':[{'familia_id':'abarrotes','en_promocion':0}]}

def test_valid_request_with_missing_families():
    p,q=sanitize(base());assert len(p['familias'])==12;assert q['estado']=='advertencia'

def test_repair_store_date_family():
    p=base();p['tienda_id']='T05';p['fecha']='01/03/2026';p['familias'][0]['familia_id']='ABARROTES '
    out,q=sanitize(p);assert out['tienda_id']==5;assert out['fecha']=='2026-03-01';assert q['estado']=='advertencia'

def test_conflicting_duplicate_rejected():
    p=base();p['familias'].append({'familia_id':'abarrotes','en_promocion':3})
    with pytest.raises(ValueError):sanitize(p)

def test_negative_promotions_rejected():
    p=base();p['familias'][0]['en_promocion']=-1
    with pytest.raises(ValueError):sanitize(p)

def test_observation_negative_warning():
    p={'tienda_id':1,'fecha':'2026-03-01','ventas':[{'familia_id':'abarrotes','ventas':-4}]}
    _,q=sanitize(p,'observaciones');assert q['estado']=='advertencia'

def test_unknown_family_rejected():
    p=base();p['familias'][0]['familia_id']='unknown'
    with pytest.raises(ValueError):sanitize(p)
