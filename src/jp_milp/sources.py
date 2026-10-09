"""Read-only selected Kyushu raw-field extraction with explicit raw units.

These readers do not invent Qref, product shares, payment recognition or menus.
"""
import csv
import hashlib
import io
from pathlib import Path
from datetime import datetime, timedelta
import zipfile
from .config import JST, require


def provenance(path):
    p=Path(path)
    return dict(path=str(p.resolve()), sha256=hashlib.sha256(p.read_bytes()).hexdigest(), information='ex_post')


def key(day, slot):
    return (datetime.strptime(day, '%Y%m%d').replace(tzinfo=JST)+timedelta(minutes=30*(int(slot)-1))).isoformat()


def nullable(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def kyushu_lfc(path):
    result=[]
    with Path(path).open(encoding='cp932', newline='') as stream:
        for row in csv.reader(stream):
            if len(row) >= 19 and row[0].isdigit() and len(row[0]) == 8:
                result.append(dict(start=key(row[0], row[1]), frequency_mean_hz=nullable(row[4]),
                                   frequency_upper_hz=nullable(row[5]), frequency_lower_hz=nullable(row[6]),
                                   lfc_mean_mw=nullable(row[16]), lfc_upper_mw=nullable(row[17]), lfc_lower_mw=nullable(row[18])))
    require(len({r['start'] for r in result}) == len(result), 'Duplicate LFC key')
    return dict(rows=result, source=provenance(path), status='STATISTICS_ONLY_NOT_MODEL_INPUT')


def kyushu_edc_related(path, member):
    result=[]
    with zipfile.ZipFile(path) as archive:
        with io.TextIOWrapper(archive.open(member), encoding='cp932') as stream:
            for row in csv.reader(stream):
                if len(row) >= 11 and row[0].isdigit() and len(row[0]) == 8:
                    result.append(dict(start=key(row[0], row[1]), own_mo_kwh=nullable(row[7]),
                                       exchange_kwh=nullable(row[8]), forecast_other_kwh=nullable(row[10])))
    require(len({r['start'] for r in result}) == len(result), 'Duplicate EDC-related key')
    return dict(rows=result, source=dict(provenance(path), member=member), status='NOT_PURE_EDC_OR_T1')


def kyushu_ics(path):
    result=[]
    with Path(path).open(encoding='cp932', newline='') as stream:
        for row in csv.reader(stream):
            if len(row) >= 58 and row[0] == 'D':
                result.append(dict(start=key(row[1], row[2]), imbalance_kwh=nullable(row[21]),
                                   surplus_status_raw=row[39], partition_raw=row[57]))
    require(len({r['start'] for r in result}) == len(result), 'Duplicate ICS key')
    return dict(rows=result, source=provenance(path), status='CONDITIONING_ONLY_NO_ACTIVATION_CHANNEL')
