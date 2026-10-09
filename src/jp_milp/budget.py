"""Explicit generation of §9.1 common-coverage budgets, not per-strategy samples."""
from calendar import isleap
from collections import Counter
from .config import timestamp, require, number


def common_coverage_budget(formal_intervals, observation_intervals, annual_efc=600.):
    require(number(annual_efc, 'annual engineering EFC rate') >= 0, 'Negative annual EFC')
    require(len(set(formal_intervals)) == len(formal_intervals), 'Duplicate formal budget coverage')
    require(len(set(observation_intervals)) == len(observation_intervals), 'Duplicate observation budget coverage')
    require(not set(formal_intervals).intersection(observation_intervals), 'Observation overlaps formal coverage')
    formal=Counter(timestamp(t).year for t in formal_intervals)
    observation=Counter(timestamp(t).year for t in observation_intervals)
    counts=dict(formal)
    for year, count in observation.items():
        if year not in counts:
            counts[year]=count
    budgets={str(y): annual_efc*n/(48*(366 if isleap(y) else 365)) for y, n in counts.items()}
    return dict(annual_budgets_efc=budgets, basis='USER_ENGINEERING_COMMON_COVERAGE',
                lookahead_only_years=[str(y) for y in counts if y not in formal],
                common_interval_counts={str(y): n for y, n in counts.items()}, annual_rate=annual_efc)
