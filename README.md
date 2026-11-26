# Nodance Validator Toolkit

Open-source, local-first infrastructure diagnostics for blockchain validator operators.

## v0.1.0 — Linux infrastructure checker

This initial release inventories logical CPUs and memory, checks free space on a selected filesystem, queries system time synchronization and optionally inspects one systemd unit. It runs on Linux with Python 3.8+ and requires no third-party Python packages or root access. Some systemd queries may be unavailable depending on the host.

```sh
python3 nodance_check.py
python3 nodance_check.py --chain solana --role backup --disk-path / --json
python3 nodance_check.py --chain monad --role primary
```

`--chain` and `--role` are labels only. Blockchain-specific checks, comparison of primary/backup hosts, and emergency notifications are not implemented yet. This release does not certify readiness or authorize failover.

### Configurable checks

Use `--disk-path` to select the actual ledger/state filesystem. The default warning threshold is 15% free space (a configurable heuristic, not a blockchain requirement). Use `--min-cpu`, `--min-ram-gib`, `--min-disk-gib`, and `--min-disk-percent` to specify your own thresholds. CPU and RAM are informational unless minimum values are provided. Use `--service UNIT` to check your actual systemd unit. An active unit is not proof of consensus participation.

### Output and exit codes

`--json` emits a structured local report. Statuses: PASS, INFO, SKIP, WARN, UNKNOWN. Overall NO_WARNINGS means no warning or unknown among executed checks, not a healthy validator certification. WARN takes precedence over INCOMPLETE; inspect individual results.

- 0: no warnings or unknown results
- 1: at least one warning
- 2: incomplete check or invalid CLI usage

### Security and privacy

Read-only checks. No outbound requests, telemetry, remote login, credential collection, key file access, automatic remediation or failover. No hostname, service name, or selected filesystem path is printed. Reports still reveal operational metadata; review before sharing. No secrets should be included in issue reports. This tool has not undergone an independent security audit.

### Roadmap

- Solana and Monad chain-specific adapters, validated against upstream documentation and actual nodes.
- Explicit primary/backup comparison, stale-data handling and hard readiness gates.
- Independent heartbeat observer and opt-in emergency notification channels.
- Documented incident response and integration tests on real validator infrastructure.

### Development

```sh
python3 -m unittest discover -s tests -v
```

Feedback from validator operators is welcome. Please report your Linux distribution, tool version, expected behavior and sanitized output. Do not submit passwords, private keys or sensitive node configuration.

License: MIT (see LICENSE).
