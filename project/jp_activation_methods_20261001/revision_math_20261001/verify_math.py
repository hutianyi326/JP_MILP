"""Independent numerical examples for the V2 research specification; no model edits."""
from pathlib import Path
import csv
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone

import numpy as np
from scipy.optimize import linprog
from scipy.special import betainc

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REPORT = HERE.parent / '日本EPRX激活推算方法研究.md'
results = []


def check(name, passed, **details):
    results.append(dict(test=name, passed=bool(passed), **details))
    if not passed:
        raise AssertionError(name)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


# Full observed key inventory, not inferred from row count alone.
fit_path = ROOT / 'countries/JP/research/analysis/rrfit_forecast_usage_30min_JST_expost.csv'
by_area = {}
with fit_path.open(encoding='utf-8-sig', newline='') as f:
    for row in csv.DictReader(f):
        ts = datetime.fromisoformat(row['timestamp_JST'])
        if ts.tzinfo is not None:
            ts = ts.astimezone(timezone(timedelta(hours=9))).replace(tzinfo=None)
        by_area.setdefault(row['area'], []).append(ts)
areas = {'北海道', '東北', '東京', '中部', '北陸', '関西', '中国', '四国', '九州'}
check('FIT exact nine-area set', set(by_area) == areas, areas=sorted(by_area))
expected = [datetime(2025, 1, 1) + timedelta(minutes=30*i) for i in range(29184)]
check('FIT exact JST endpoints, uniqueness and continuity',
      all(sorted(rows) == expected for rows in by_area.values()),
      start=str(expected[0]), last_interval_start=str(expected[-1]),
      end_exclusive='2026-09-01 00:00:00', intervals_per_area=len(expected))

# Rounded mixture masses must sum to one, including the two endpoint bins.
ys = np.arange(101) / 100
lo, hi = np.maximum(0, ys-.005), np.minimum(1, ys+.005)
mass = .55*(betainc(2.3, 3.1, hi)-betainc(2.3, 3.1, lo))
mass[0] += .25
mass[-1] += .20
check('P3 rounded mixture probability', np.all(mass >= 0) and abs(mass.sum()-1) < 1e-12,
      sum_probability=float(mass.sum()))

# OU exact transition preserves stationary variance analytically.
kappa, sigma, delta = 3.0, .08, 1/3600
phi = np.exp(-kappa*delta)
innov_var = sigma**2/(2*kappa)*(1-phi**2)
stationary_var = sigma**2/(2*kappa)
check('F2 OU stationary moment identity',
      abs(phi**2*stationary_var+innov_var-stationary_var) < 1e-14,
      delta_hours=delta, stationary_variance=stationary_var)

# Saturated droop and ramp stay inside the prescribed signed interval.
freq = np.array([-.1, -.02, 0, .02, .1])
target = np.minimum(1, 20*np.maximum(-freq-.01, 0))-np.minimum(1, 20*np.maximum(freq-.01, 0))
response, prev = [], 0.
for value in target:
    prev += np.clip(value-prev, -.25, .25)
    response.append(prev)
check('F4 F6 droop direction and normalized ramp',
      target[0] > 0 and target[-1] < 0 and np.all(np.abs(response) <= 1)
      and np.max(np.abs(np.diff([0]+response))) <= .25+1e-12)

counts = np.array([[390,106,7],[108,788,3],[5,5,6]], dtype=float)
prob = (counts+1)/(counts+1).sum(axis=1, keepdims=True)
check('K1 smoothed transition row sums', np.allclose(prob.sum(axis=1), 1),
      alpha=1, row_sums=prob.sum(axis=1).tolist())

# Partial-identification bound checked against an independent two-variable LP.
partial = []
for qp, qm, dur, net in [(1,1,.5,.1), (2,.7,.5,-.15), (.4,1.6,.5,.1)]:
    bound = (dur-max(net,0)/qp-max(-net,0)/qm)/(1/qp+1/qm)
    opt = linprog([-1,-1], A_ub=[[1/qp,1/qm]], b_ub=[dur],
                  A_eq=[[1,-1]], b_eq=[net], bounds=(0,None), method='highs')
    check('J5 gross-energy bound '+str((qp,qm,net)), opt.success and
          abs(opt.x[0]+opt.x[1]-(abs(net)+2*bound)) < 1e-9,
          Kmax=float(bound), U=float(opt.x[0]), D=float(opt.x[1]))
    partial.append(bound)

# Gaussian posterior checked using the equivalent covariance update identity.
H = np.array([[1.,2.],[2.,-1.]])
V0 = np.array([[2.,.3],[.3,1.]])
Se = np.diag([.2,.4])
posterior = np.linalg.inv(np.linalg.inv(V0)+H.T@np.linalg.solve(Se,H))
alternative = V0-V0@H.T@np.linalg.solve(H@V0@H.T+Se,H@V0)
check('J2 posterior covariance identity', np.allclose(posterior,alternative)
      and np.min(np.linalg.eigvalsh(posterior)) > 0)

# Finite-support transport primal vs the stated dual, including zero radius.
weights = np.array([.4,.6])
profits = np.array([3.,7.,-2.])
dist = np.array([[0.,1.,2.],[1.,0.,1.]])
row_eq = np.zeros((2,6))
row_eq[0,:3], row_eq[1,3:] = 1,1
for eps in [0., .3, 1.5]:
    primal = linprog(np.tile(profits,2), A_ub=dist.reshape(1,-1), b_ub=[eps],
                     A_eq=row_eq, b_eq=weights, bounds=(0,None), method='highs')
    dual_A, dual_b = [], []
    for i in range(2):
        for j in range(3):
            row = [0.,0.,-dist[i,j]]
            row[i] = 1
            dual_A.append(row)
            dual_b.append(profits[j])
    dual = linprog([-.4,-.6,eps], A_ub=dual_A, b_ub=dual_b,
                   bounds=[(None,None),(None,None),(0,None)], method='highs')
    check('W2 W3 primal-dual '+str(eps), primal.success and dual.success and
          abs(primal.fun+dual.fun) < 1e-9, epsilon=eps, worst_profit=float(primal.fun),
          dual_profit=float(-dual.fun))

base, activation, eta, dur = -.8,.5,.92,.5
net_power = base+activation
charge, discharge = max(-net_power,0), max(net_power,0)
soc_change = (eta*charge-discharge/eta)*dur
check('M5 M6 upward response can remain charging', abs(soc_change-.138) < 1e-12,
      charge_mw=charge, SOC_change_MWh=soc_change)
usable, nominal = .8,1.
efc = (eta*charge+discharge/eta)*dur/(2*usable)
check('M4 EFC uses usable energy', abs(efc-.08625) < 1e-12,
      usable_MWh=usable, nominal_MWh=nominal, EFC=efc)

# Structural checks do not replace independent mathematical review.
doc = REPORT.read_text(encoding='utf-8')
tags = re.findall(r'\\tag\{([^}]+)\}', doc)
check('Unique equation tags', len(tags) == len(set(tags)), equation_count=len(tags))
check('Display-math delimiter pairs', len(re.findall(r'^\$\$$', doc, re.M)) % 2 == 0)
check('Complete numbered sections', all(re.search(r'^## '+str(i)+r' ', doc, re.M)
                                         for i in range(1,23)))
broken = []
for link in re.findall(r'\]\(([^)]+)\)', doc):
    if re.match(r'[a-zA-Z]+:',link) or link.startswith('#'):
        continue
    target = link.split('#')[0]
    if target and not (REPORT.parent/target).exists():
        broken.append(target)
check('Local document links', not broken, broken_links=broken)
check('Old snapshot unchanged', sha(HERE/'before_report.md') ==
      '99fd957dffec6c7edc04a5a74004507b90a789a9461af15447d0d96ac4d89c89')
payload = dict(scope='Research equations, examples, document structure and FIT key coverage; not a MILP benchmark or activation calibration',
               generated_at=datetime.now(timezone.utc).isoformat(),
               report_sha256=sha(REPORT), script_sha256=sha(Path(__file__)),
               input_sha256={str(fit_path.relative_to(ROOT)):sha(fit_path)},
               tests=results, passed=sum(r['passed'] for r in results), failed=0)
(HERE/'math_checks.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(passed=payload['passed'],failed=0,equation_count=len(tags),
                     report_sha256=payload['report_sha256']),ensure_ascii=False))
