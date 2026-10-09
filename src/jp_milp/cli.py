"""Command-line entry point; no default station, prices or regional allocations."""
import argparse
import json
from pathlib import Path
from .inputs import load, validate
from .rolling import run
from .sensitivity import suite


def main():
    parser=argparse.ArgumentParser(description='Japan conditional MILP; JPY, JST, 30 minutes')
    parser.add_argument('--input', required=True, help='Validated normalized JSON bundle')
    parser.add_argument('--end', help='Exclusive formal end, JST-aware midnight')
    parser.add_argument('--output')
    parser.add_argument('--preflight-only', action='store_true')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--edc-sensitivity', help='JSON mapping interval -> positive weight / zero-mean deviation pairs')
    args=parser.parse_args()
    try:
        data=load(args.input)
        if args.preflight_only:
            print(json.dumps(validate(data), ensure_ascii=False, indent=2)); return 0
        if not args.output or not args.end:
            parser.error('--end and --output are required for a solve')
        if args.edc_sensitivity:
            if args.resume:
                parser.error('Resume individual sensitivity runs, not a whole suite')
            deviations=json.loads(Path(args.edc_sensitivity).read_text(encoding='utf-8-sig'))
            result=suite(data, args.end, deviations, args.output)
        else:
            result=run(data, args.end, args.output, resume=args.resume)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2 if result.get('status') == 'BLOCKED' else 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps(dict(status='NOT_READY_OR_FAILED', reason=str(exc)), ensure_ascii=False)); return 2


if __name__ == '__main__':
    raise SystemExit(main())
