JSON Report Schema

Schema version 2

Introduced in Nodance Validator Toolkit v0.2.0-dev.

Schema version 2 extends the original infrastructure report with structured metrics and configurable thresholds for machine-readable infrastructure comparison.

Report fields

Field	Type	Description
version	string	Toolkit version
schema_version	integer	Report schema version
timestamp_utc	string	UTC report generation timestamp
chain_label	string	generic, solana or monad
role	string	primary, backup or standalone
scope	string	Diagnostic scope
status	string	Overall report status
checks	array	Infrastructure check results

Check structure

Each check contains:

* check: Check identifier.
* status: Individual check status.
* detail: Human-readable description.
* metrics: Structured measurements.
* thresholds: Configured requirements.

Supported metrics

CPU

* logical_cpus

Memory

* total_gib
* available_gib

Disk

* total_gib
* free_gib
* free_percent

Time synchronization

* ntp_synchronized

Systemd service

* configured
* load_state
* active_state

Unavailable measurements are represented by null.

Configurable thresholds

* min_logical_cpus
* min_total_gib
* min_free_gib
* min_free_percent

A null threshold indicates that no minimum has been configured.

Check statuses

* INFO: Informational measurement.
* PASS: Configured check passed.
* WARN: A requirement was not satisfied.
* UNKNOWN: Check could not be completed.
* SKIP: Optional check was not configured.

Overall status and exit codes

Status	Exit code
NO_WARNINGS	0
WARN	1
INCOMPLETE	2

WARN takes precedence over UNKNOWN when determining the overall report status.

Compatibility

Existing report fields are retained from v0.1.0.

Consumers should inspect schema_version before processing structured metrics. Reports from v0.1.0 do not contain a schema_version field.

Validation

Development validation performed on November 27, 2026.

* GitHub Actions: three successful Python matrix jobs.
* Python versions: 3.8, 3.10 and 3.12.
* Manual environment: Ubuntu 22.04.5 LTS.
* Structured metrics verified.
* Configurable thresholds verified.
* Expected warning status verified.

Privacy and limitations

Reports do not include private keys, SSH credentials, hostnames, configured filesystem paths or systemd unit names.

Infrastructure reports may still contain operational information and should be shared carefully.

Chain labels do not indicate blockchain-specific validation.

This schema does not certify validator readiness or safe failover.

Next milestone

Implement an offline primary and backup infrastructure report comparison tool.
