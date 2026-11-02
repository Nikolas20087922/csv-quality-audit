# CSV Quality Audit

A small Python CLI that checks CSV data before it enters a reporting pipeline.
It reports missing values, invalid numbers/dates, duplicates, broken row widths,
and values outside a JSON contract. No third-party packages are needed.

## Try it

Requires Python 3.10 or newer. Run from the repository directory:

```sh
python3 audit.py examples/orders.csv --schema examples/schema.json
python3 audit.py examples/broken.csv --schema examples/schema.json --output report.json
python3 -m unittest discover -s tests -v
```

The clean example returns exit code `0`. The broken example returns `1` and a
JSON report with **six issues** across three records. Input/configuration errors
return `2`. These codes allow the tool to be used as a CI data quality gate.

## Contract

```json
{"columns":{"id":{"type":"integer","required":true,"unique":true},"amount":{"type":"number","min":0},"date":{"type":"date"}}}
```

Supported types: `string` (default), `integer`, finite `number`, and ISO `date`.
Rules: `required`, `unique`, numeric `min`/`max`, and `enum` (raw trimmed strings).
All columns named by the contract must exist. Extra columns are allowed.
Whitespace is stripped for validation; empty optional values are skipped.
Numeric uniqueness is checked after conversion, so `01` and `1` are duplicates.
Dates use Python's `date.fromisoformat`. Input is UTF-8, with optional BOM.

Each issue includes a record's starting physical line number, column, code and
message. Quoted multiline CSV records are supported. Input files are never changed.

## Design and limits

The reader processes rows sequentially. Memory grows with the number of issues
and unique values; this is intended for small/medium datasets, not a distributed
data platform. The JSON contract is a deliberately small custom format, not
JSON Schema. There is no automatic repair, database connection, or type inference.

Tests cover CLI exit codes, BOM, multiline rows, schema/header errors, missing
columns, invalid dates, non-finite numbers and normalized duplicates.

## Learning notes

Portfolio learning project created for Nikolas Lutsenko with AI assistance.
It is not commercial work. Useful topics to explain or extend: CSV parsing,
data contracts, numeric normalization, error reporting, memory usage and tests.
Possible next step: cap report sizes and add streaming JSONL diagnostics.
