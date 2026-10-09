"""Runtime configuration and common validation (JP formulation §§2, 9, 14.7)."""
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math

JST = timezone(timedelta(hours=9))
DT = .5
TOL = 1e-6
SCENARIOS = ('LV_FCR', 'HV_SPOT_FCR', 'HV_SPOT_S1_T1')


class InputError(ValueError):
    """Missing, incompatible or unsupported input; never an economic zero."""


def require(ok, message):
    if not ok:
        raise InputError(message)


def number(value, label):
    require(isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value), f'{label}: finite numeric input required')
    return float(value)


def timestamp(value):
    t = datetime.fromisoformat(value)
    require(t.tzinfo is not None, 'Timezone required')
    t = t.astimezone(JST)
    require(t.minute in (0, 30) and t.second == 0 and t.microsecond == 0,
            'JST half-hour boundary required')
    return t


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False, separators=(',', ':')).encode()).hexdigest()


@dataclass(frozen=True)
class Asset:
    version: str
    charge_mw: float
    discharge_mw: float
    nominal_mwh: float
    minimum_mwh: float
    maximum_mwh: float
    initial_mwh: float
    target_mwh: float
    eta_charge: float
    eta_discharge: float
    auxiliary_ac_mw: float
    auxiliary_dc_mw: float
    import_mw: float
    export_mw: float
    service_scale: float
    service_offset_mw: float
    poi_scale: float
    poi_offset_mw: float
    port_domain_min_mw: float
    port_domain_max_mw: float

    def validate(self):
        require(bool(self.version), 'asset version required')
        for k, v in asdict(self).items():
            if k != 'version':
                number(v, 'asset.' + k)
        require(min(self.charge_mw, self.discharge_mw, self.nominal_mwh,
                    self.service_scale, self.poi_scale) > 0, 'Positive equipment limits required')
        require(0 <= self.minimum_mwh < self.maximum_mwh <= self.nominal_mwh,
                'Invalid usable SOC range')
        require(all(self.minimum_mwh <= x <= self.maximum_mwh
                    for x in (self.initial_mwh, self.target_mwh)), 'Initial/target SOC outside limits')
        require(0 < self.eta_charge <= 1 and 0 < self.eta_discharge <= 1, 'Invalid efficiencies')
        require(min(self.auxiliary_ac_mw, self.auxiliary_dc_mw, self.import_mw, self.export_mw) >= 0,
                'Negative auxiliary/POI limits')
        require(self.port_domain_min_mw < self.port_domain_max_mw, 'Invalid affine port domain')

    @property
    def usable_mwh(self):
        return self.maximum_mwh - self.minimum_mwh

    @property
    def net_bounds(self):
        return (max(-self.charge_mw - self.auxiliary_ac_mw,
                    (-self.import_mw - self.poi_offset_mw) / self.poi_scale,
                    self.port_domain_min_mw),
                min(self.discharge_mw - self.auxiliary_ac_mw,
                    (self.export_mw - self.poi_offset_mw) / self.poi_scale,
                    self.port_domain_max_mw))


@dataclass(frozen=True)
class Solver:
    time_limit_seconds: float = 60
    mip_rel_gap: float = 1e-4
    presolve: bool = True
    backend: str = 'scipy'

    def validate(self):
        require(number(self.time_limit_seconds, 'time limit') > 0, 'Positive time limit required')
        require(0 <= number(self.mip_rel_gap, 'gap') < 1, 'Invalid gap')
        require(self.backend in ('scipy','highspy','scip'),'Unknown solver backend')
