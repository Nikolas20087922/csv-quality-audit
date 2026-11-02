"""Validate a CSV against a JSON contract. Uses only the Python standard library."""
import argparse
import csv
import json
import math
from datetime import date
from pathlib import Path


def validate_schema(schema):
    columns = schema.get('columns')
    if not isinstance(columns, dict) or not columns:
        raise ValueError('Schema needs a non-empty columns object')
    for name, rule in columns.items():
        if not isinstance(rule, dict) or rule.get('type', 'string') not in {'string', 'integer', 'number', 'date'}:
            raise ValueError(f'Invalid rule for {name}')
        if 'min' in rule and 'max' in rule and rule['min'] > rule['max']:
            raise ValueError(f'min exceeds max for {name}')
        if ('min' in rule or 'max' in rule) and rule.get('type') not in {'integer', 'number'}:
            raise ValueError(f'Bounds require a numeric type for {name}')
    return columns


def convert(value, kind):
    if kind == 'integer':
        return int(value)
    if kind == 'number':
        result = float(value)
        if not math.isfinite(result):
            raise ValueError('Non-finite number')
        return result
    if kind == 'date':
        return date.fromisoformat(value)
    return value


def audit(path, schema):
    """Return deterministic diagnostics; line numbers are CSV record start lines."""
    columns = validate_schema(schema)
    issues, seen = [], {name: set() for name, rule in columns.items() if rule.get('unique')}

    def issue(line, column, code, message):
        issues.append(dict(line=line, column=column, code=code, message=message))

    with Path(path).open(encoding='utf-8-sig', newline='') as source:
        reader = csv.reader(source, strict=True)
        headers = next(reader, None)
        if not headers:
            raise ValueError('CSV is empty or has no header')
        if len(headers) != len(set(headers)) or any(not h.strip() for h in headers):
            raise ValueError('CSV headers must be non-empty and unique')
        missing = [name for name in columns if name not in headers]
        for name in missing:
            issue(1, name, 'missing_column', 'Column required by schema is absent')
        count = 0
        previous_line = reader.line_num
        for record in reader:
            line = previous_line + 1
            previous_line = reader.line_num
            count += 1
            if len(record) != len(headers):
                issue(line, '', 'row_width', f'Expected {len(headers)} cells, received {len(record)}')
                continue
            row = dict(zip(headers, record))
            for name, rule in columns.items():
                if name in missing:
                    continue
                value = row[name].strip()
                if not value:
                    if rule.get('required'):
                        issue(line, name, 'missing_value', 'Required value is empty')
                    continue
                try:
                    parsed = convert(value, rule.get('type', 'string'))
                except (ValueError, OverflowError):
                    issue(line, name, 'invalid_type', f"Expected {rule.get('type', 'string')}")
                    continue
                if 'enum' in rule and value not in rule['enum']:
                    issue(line, name, 'invalid_choice', 'Value is not an allowed choice')
                if 'min' in rule and parsed < rule['min']:
                    issue(line, name, 'below_min', 'Value is below minimum')
                if 'max' in rule and parsed > rule['max']:
                    issue(line, name, 'above_max', 'Value is above maximum')
                if name in seen:
                    if parsed in seen[name]:
                        issue(line, name, 'duplicate', 'Value must be unique')
                    seen[name].add(parsed)
    return dict(rows=count, valid=not issues, issue_count=len(issues), issues=issues)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv_file', type=Path)
    parser.add_argument('--schema', type=Path, required=True)
    parser.add_argument('--output', type=Path, help='Write JSON report to this file')
    args = parser.parse_args(argv)
    try:
        result = audit(args.csv_file, json.loads(args.schema.read_text(encoding='utf-8')))
        rendered = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
        if args.output:
            args.output.write_text(rendered, encoding='utf-8')
        else:
            print(rendered, end='')
        return 0 if result['valid'] else 1
    except (OSError, ValueError, TypeError, csv.Error) as exc:
        parser.exit(2, f'error: {exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
