"""Reviewed nominal capacity clocks and due/frozen horizon closure."""
from datetime import timedelta
from .config import timestamp, require

HISTORICAL='HISTORICAL_JP_2026'
CLOSURE='DUE_AND_FROZEN_CLOSURE'

def capacity_clock(first):
    day=timestamp(first).replace(hour=0,minute=0,second=0)
    # E38 primary Articles 27-32 (2025-04-01), E34 (2026-03-14),
    # E35/E02: extends the same reviewed regimes through the September tail.
    require('2025-12-01' <= first[:10] < '2026-09-02','Historical clock scope is Dec 2025-Sep 1 2026')
    if first[:10] < '2026-03-14':
        saturday=day-timedelta(days=(day.weekday()-5)%7)
        gate=(saturday-timedelta(days=4)).replace(hour=14)
        return gate,gate.replace(hour=15),6
    gate=(day-timedelta(days=1)).replace(hour=14)
    return gate,gate.replace(hour=15),1

def planning_end(data,now,execute_end,frozen):
    """At least two days; all due-today and frozen future deliveries + tails.

    Also close over native contracts intersecting the expanded interval. New
    future-gate orders are provisional and are not prematurely frozen.
    """
    end=execute_end+timedelta(days=1)
    if data.get('planning_horizon_policy','TWO_DAYS')!='DUE_AND_FROZEN_CLOSURE':return end
    specs=[(o,list(o['weights']),0.) for o in data['spot_orders']]
    for b in data['capacity_blocks']:
        tail=max(sum(s['hours'] for s in path['segments']) for path in b['services'])
        specs.append((b,b['intervals'],max(0.,tail-.5)))
    for spec,keys,tail in specs:
        last=max(timestamp(t) for t in keys)+timedelta(minutes=30)
        if last<=now:continue
        if spec['id'] in frozen or now<=timestamp(spec['gate'])<execute_end:
            end=max(end,last+timedelta(hours=tail))
    # Round up to midnight to avoid splitting regular 3h native blocks.
    def midnight_ceiling(t):
        floor=t.replace(hour=0,minute=0,second=0,microsecond=0)
        return floor if floor==t else floor+timedelta(days=1)
    end=midnight_ceiling(end)
    while True:
        extended=end
        for _,keys,_ in specs:
            first=min(timestamp(t) for t in keys);last=max(timestamp(t) for t in keys)+timedelta(minutes=30)
            if first<end and last>now:extended=max(extended,last)
        extended=midnight_ceiling(extended)
        if extended==end:break
        end=extended
    available=timestamp(data['intervals'][-1]['start'])+timedelta(minutes=30)
    require(end<=available,'Due/frozen obligations exceed supplied observation coverage; cannot drop or clip commitments')
    return end
