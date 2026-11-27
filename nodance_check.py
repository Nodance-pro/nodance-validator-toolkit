
#!/usr/bin/env python3
"""Read-only Linux infrastructure checks. No network requests or telemetry."""
import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone

VERSION = '0.2.0-dev'
SCHEMA_VERSION = 2
GIB = 1024 ** 3


def result(name, status, detail, metrics=None, thresholds=None):
    return {
        'check': name,
        'status': status,
        'detail': detail,
        'metrics': metrics if metrics is not None else {},
        'thresholds': thresholds if thresholds is not None else {}
    }


def threshold(name, value, minimum, unit):
    if minimum is None:
        return result(name, 'INFO', '{} {}'.format(value, unit))
    return result(name, 'PASS' if value >= minimum else 'WARN',
                  '{} {}; configured minimum {} {}'.format(
                      value, unit, minimum, unit))


def command(args):
    try:
        p = subprocess.run(
            args, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True, timeout=5, check=False)
        return p.returncode, p.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return None, ''


def cpu_check(minimum):
    count = os.cpu_count()
    limits = {'min_logical_cpus': minimum}

    if count is None:
        return result(
            'cpu', 'UNKNOWN',
            'Logical CPU count unavailable',
            {'logical_cpus': None}, limits)

    r = threshold('cpu', count, minimum, 'logical CPUs')
    r['metrics'] = {'logical_cpus': count}
    r['thresholds'] = limits
    return r


def memory_check(minimum):
    limits = {'min_total_gib': minimum}

    try:
        with open('/proc/meminfo', encoding='ascii') as f:
            values = {
                line.split(':')[0]: int(line.split()[1])
                for line in f
                if line.startswith(('MemTotal:', 'MemAvailable:'))
            }

        total = values['MemTotal'] / 1048576
        available = values['MemAvailable'] / 1048576

        r = threshold('memory', round(total, 2), minimum, 'GiB total')

        if minimum is not None:
            r['status'] = 'PASS' if total >= minimum else 'WARN'

        r['detail'] += '; {:.2f} GiB currently available'.format(
            available)

        r['metrics'] = {
            'total_gib': total,
            'available_gib': available
        }
        r['thresholds'] = limits
        return r

    except (OSError, KeyError, ValueError, IndexError):
        return result(
            'memory', 'UNKNOWN',
            'Memory statistics unavailable',
            {'total_gib': None, 'available_gib': None},
            limits)


def disk_check(path, minimum, warn_pct):
    limits = {
        'min_free_gib': minimum,
        'min_free_percent': warn_pct
    }

    try:
        d = shutil.disk_usage(path)

        if d.total <= 0:
            raise ValueError('zero disk size')

        pct = 100 * d.free / d.total
        free = d.free / GIB

        status = 'WARN' if (
            pct < warn_pct or
            (minimum is not None and free < minimum)
        ) else 'PASS'

        detail = (
            '{:.2f} GiB free ({:.1f}%); '
            'configured minimum {:.1f}%{}'
        ).format(
            free, pct, warn_pct,
            '' if minimum is None
            else ' and {} GiB'.format(minimum))

        return result(
            'disk', status, detail,
            {
                'total_gib': d.total / GIB,
                'free_gib': free,
                'free_percent': pct
            },
            limits)

    except (OSError, ValueError):
        return result(
            'disk', 'UNKNOWN',
            'Cannot inspect selected filesystem',
            {
                'total_gib': None,
                'free_gib': None,
                'free_percent': None
            },
            limits)


def time_check():
    rc, out = command([
        'timedatectl', 'show',
        '--property=NTPSynchronized', '--value'
    ])

    if rc != 0 or out not in ('yes', 'no'):
        return result(
            'time_sync', 'UNKNOWN',
            'NTP synchronization status unavailable',
            {'ntp_synchronized': None})

    return result(
        'time_sync',
        'PASS' if out == 'yes' else 'WARN',
        'System reports NTP synchronized: ' + out,
        {'ntp_synchronized': out == 'yes'})


def service_check(service):
    metrics = {
        'configured': service is not None,
        'load_state': None,
        'active_state': None
    }

    if service is None:
        return result(
            'service', 'SKIP',
            'No systemd unit configured', metrics)

    rc, out = command([
        'systemctl', 'show',
        '--property=LoadState,ActiveState',
        '--', service
    ])

    if rc != 0:
        return result(
            'service', 'UNKNOWN',
            'Cannot inspect configured systemd unit', metrics)

    states = dict(
        line.split('=', 1)
        for line in out.splitlines()
        if '=' in line
    )

    metrics['load_state'] = states.get('LoadState')
    metrics['active_state'] = states.get('ActiveState')

    if states.get('LoadState') != 'loaded':
        return result(
            'service', 'UNKNOWN',
            'Configured unit is not loaded', metrics)

    state = states.get('ActiveState')

    if state == 'active':
        return result(
            'service', 'PASS',
            'Configured unit is active (not a consensus check)',
            metrics)

    if state in (
        'inactive', 'failed', 'activating',
        'deactivating', 'reloading', 'maintenance'
    ):
        return result(
            'service', 'WARN',
            'Configured unit state: ' + state, metrics)

    return result(
        'service', 'UNKNOWN',
        'Unit state unavailable', metrics)


def overall(checks):
    statuses = {c['status'] for c in checks}

    if 'WARN' in statuses:
        return 'WARN'

    if 'UNKNOWN' in statuses:
        return 'INCOMPLETE'

    return 'NO_WARNINGS'


def nonnegative(value):
    import math
    n = float(value)

    if not math.isfinite(n) or n < 0:
        raise argparse.ArgumentTypeError(
            'expected a finite nonnegative number')

    return n


def percent(value):
    n = nonnegative(value)

    if n > 100:
        raise argparse.ArgumentTypeError('expected 0–100')

    return n


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)

    p.add_argument('--version', action='version', version=VERSION)

    p.add_argument(
        '--chain',
        choices=['generic', 'solana', 'monad'],
        default='generic',
        help='Report label only; no chain-specific checks')

    p.add_argument(
        '--role',
        choices=['primary', 'backup', 'standalone'],
        default='standalone')

    p.add_argument(
        '--disk-path', default='/',
        help='Filesystem to inspect; path is not included in report')

    p.add_argument('--min-cpu', type=nonnegative)
    p.add_argument('--min-ram-gib', type=nonnegative)
    p.add_argument('--min-disk-gib', type=nonnegative)
    p.add_argument('--min-disk-percent', type=percent, default=15)

    p.add_argument(
        '--service',
        help='Optional systemd unit name; omitted from report')

    p.add_argument('--json', action='store_true')

    a = p.parse_args(argv)

    if platform.system() != 'Linux':
        p.error('Linux only')

    checks = [
        cpu_check(a.min_cpu),
        memory_check(a.min_ram_gib),
        disk_check(
            a.disk_path,
            a.min_disk_gib,
            a.min_disk_percent),
        time_check(),
        service_check(a.service)
    ]

    report = {
        'version': VERSION,
        'schema_version': SCHEMA_VERSION,
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'chain_label': a.chain,
        'role': a.role,
        'scope': 'local Linux checks only',
        'status': overall(checks),
        'checks': checks
    }

    if a.json:
        print(json.dumps(report, indent=2))
    else:
        print('Nodance Infrastructure Checker v' + VERSION)

        print('Chain label: {} | Role: {}'.format(
            a.chain, a.role))

        for c in checks:
            print('{:8} {:12} {}'.format(
                c['status'], c['check'], c['detail']))

        print('Result: ' + report['status'])
        print('Not a validator readiness or failover certification.')

    return (
        1 if report['status'] == 'WARN'
        else 2 if report['status'] == 'INCOMPLETE'
        else 0
    )


if __name__ == '__main__':
    sys.exit(main())
