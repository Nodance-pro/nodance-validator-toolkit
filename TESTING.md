Testing and Validation

Nodance Validator Toolkit v0.1.0

Test environment

* Date: November 26, 2026
* OS: Ubuntu 22.04.5 LTS
* Python: 3.10.12
* Architecture: Linux virtual machine
* CPU: 4 logical CPUs
* RAM: 7.64 GiB

Automated CI testing

Python version	Result
Python 3.8	PASS
Python 3.10	PASS
Python 3.12	PASS

Manual infrastructure testing

Test	Result
Basic CLI execution	PASS
CPU inventory	PASS
Memory inventory	PASS
Disk space inspection	PASS
NTP synchronization check	PASS
JSON output	PASS
Configurable warning thresholds	PASS
Warning exit code (1)	PASS
Active systemd service check	Operator confirmed
Nonexistent systemd service handling	Operator confirmed
Invalid filesystem path handling	Operator confirmed

Security and operational scope

* Local infrastructure diagnostics
* Read-only system checks
* No root privileges required
* No external Python dependencies
* No network requests or telemetry during diagnostics

Current limitations

Testing was performed on a Linux virtual machine, not a production validator.

Blockchain-specific health checks, backup readiness validation, emergency notifications and automated failover are not implemented in v0.1.0.

Next development milestone

v0.2.0 — Backup Readiness Checker.

The next milestone will focus on comparing primary and backup infrastructure reports without sharing SSH credentials or private validator keys.
