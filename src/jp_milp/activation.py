"""External statistical preprocessing; never infer reference capacity from a bid."""
from math import inf
import numpy as np
from scipy.special import ndtr, ndtri
from .config import require, number


def phi(x):
    return float(np.exp(-.5*x*x) / np.sqrt(2*np.pi))


def positive_normal(mean, sigma):
    """H(m,s) = E[max(N(m,s²),0)], including the deterministic limit."""
    number(mean, 'mean'); require(number(sigma, 'sigma') >= 0, 'Negative sigma')
    return max(mean, 0.) if sigma == 0 else sigma*phi(mean/sigma)+mean*float(ndtr(mean/sigma))


def normal_bins(mean, sigma, count, boundaries=()):
    require(isinstance(count, int) and count >= 2, 'At least two requested bins')
    require(number(sigma, 'sigma') >= 0, 'Negative sigma'); number(mean, 'mean')
    if sigma == 0:
        return [(1., mean, mean, mean)]
    cuts = sorted(set([-inf, inf, *boundaries,
                       *(mean + sigma*ndtri(i/count) for i in range(1, count))]))
    bins = []
    for lo, hi in zip(cuts, cuts[1:]):
        a, b = (lo-mean)/sigma, (hi-mean)/sigma
        # Survival-function difference avoids cancellation in the right tail.
        w = float(ndtr(-a)-ndtr(-b) if a >= 0 else ndtr(b)-ndtr(a))
        if w <= 0:
            continue
        conditional = mean + sigma*(phi(a)-phi(b))/w
        bins.append((w, conditional, lo, hi))
    require(abs(sum(v[0] for v in bins)-1) < 1e-12, 'Probability mass lost')
    return bins


def fcr_states(mean, sigma, deadband_up, deadband_down, span_up, span_down,
               h_up, h_down, count=11):
    """Split at all response kinks; conditional response means preserve alpha."""
    require(min(number(deadband_up, 'deadband up'), number(deadband_down, 'deadband down')) >= 0,
            'Negative deadband')
    require(min(number(span_up, 'span up'), number(span_down, 'span down')) > 0, 'Positive spans required')
    require(min(number(h_up, 'h up'), number(h_down, 'h down')) >= 0, 'Negative direction map')
    cuts = [-deadband_up-span_up, -deadband_up, 0, deadband_down, deadband_down+span_down]
    rows = []
    for w, x, lo, hi in normal_bins(mean, sigma, count, cuts):
        up = min(1., max(0., (-x-deadband_up)/span_up))
        down = min(1., max(0., (x-deadband_down)/span_down))
        rows.append(dict(weight=w, f=h_up*up-h_down*down, s=0., t=0.,
                         gamma_up=up, gamma_down=down))
    return rows


def lfc_normal_states(mean_mw, sigma_mw, rho_up, rho_down, reference_up_mw,
                      reference_down_mw, h_up, h_down, count=11):
    require(min(number(reference_up_mw, 'up reference'), number(reference_down_mw, 'down reference')) > 0,
            'Same-pool directional reference capacities required')
    require(all(0 <= number(x, 'pool share') <= 1 for x in (rho_up, rho_down)), 'Invalid pool share')
    require(min(number(h_up, 'h up'), number(h_down, 'h down')) >= 0, 'Negative mapping')
    return [(w, max(x, 0)*rho_up*h_up/reference_up_mw - max(-x, 0)*rho_down*h_down/reference_down_mw)
            for w, x, _, _ in normal_bins(mean_mw, sigma_mw, count, [0.])]


def joint_weights(left, right, coupling):
    require(coupling in ('independent', 'same', 'opposite'), 'Unknown coupling')
    for marginal in (left, right):
        require(all(number(w, 'weight') > 0 and np.isfinite(x) for w, x in marginal)
                and abs(sum(w for w, _ in marginal)-1) < 1e-9, 'Invalid marginal')
    if coupling == 'independent':
        return [(w*v, x, z) for w, x in left for v, z in right]
    l = sorted(left, key=lambda a: a[1])
    r = sorted(right, key=lambda a: a[1], reverse=coupling == 'opposite')
    out = []; a = b = 0.; i = j = 0
    while i < len(l) and j < len(r):
        end_a, end_b = a+l[i][0], b+r[j][0]
        w = min(end_a, end_b)-max(a, b)
        if w > 1e-14:
            out.append((w, l[i][1], r[j][1]))
        if end_a <= end_b + 1e-14:
            a = end_a; i += 1
        if end_b <= end_a + 1e-14:
            b = end_b; j += 1
    return out


def composite_states(lfc, edc_center, deviations, theta, coupling='independent'):
    require(0 <= number(theta, 'theta') <= 1, 'Invalid mean sensitivity')
    number(edc_center, 'EDC center')
    require(abs(sum(w*x for w, x in deviations)) < 1e-9, 'EDC deviation must have zero mean')
    mean = sum(w*x for w, x in lfc)
    return [dict(weight=w, f=0., s=x-mean+theta*mean, t=edc_center+z)
            for w, x, z in joint_weights(lfc, deviations, coupling)]


def edc_product_energy(channels, shares):
    """§13.6 gross proxy. Channels: {name: (net_MWh, hidden_counterflow_MWh)}.

    Shares include ALL modelled regional products, including non-bid products.
    Caller must supply a non-overlapping channel mapping and its evidence.
    """
    result = {p: [0., 0.] for p in shares}
    for name, (net, hidden) in channels.items():
        number(net, name); require(number(hidden, 'counterflow') >= 0, 'Negative counterflow')
        for direction in range(2):
            weights = [number(v[name][direction], 'allocation') for v in shares.values()]
            require(min(weights, default=0) >= 0 and sum(weights) <= 1+1e-12, 'Overallocated EDC channel')
            gross = max(net if direction == 0 else -net, 0) + hidden
            for product, values in shares.items():
                result[product][direction] += values[name][direction]*gross
    return result
