# Log Query Tool

A command-line tool for searching very large log files with boolean query operators (`AND`, `OR`, `NOT`) and exporting matching rows to CSV.

## Features

- Streams log files line-by-line (memory efficient for large files)
- Query syntax with parentheses and boolean operators
- Case-insensitive matching
- Extracts valid IPv4 addresses from each matching log line
- Outputs results to a CSV file for further analysis

## Requirements

- Python 3.9+

## Usage

```bash
python3 log_query_tool.py "192.168.1.10 AND (failed OR denied)" network.log firewall.log -o results.csv
```

### Arguments

- `query`: boolean query expression
- `inputs`: one or more input log files
- `-o, --output`: output CSV path (default: `results.csv`)

## Query Syntax

### Supported operators

- `AND`: both terms must be present
- `OR`: either term may be present
- `NOT`: excludes matches
- `(` `)`: explicit grouping

### Precedence

1. `NOT`
2. `AND`
3. `OR`

### Examples

- Find IP and error:
  - `"10.10.10.5 AND error"`
- Find either timeout or reset, but not health checks:
  - `"(timeout OR reset) AND NOT healthcheck"`
- Phrase search with spaces:
  - `"\"connection refused\" AND 172.16.1.4"`

## CSV Output Columns

- `source_file`: log file path
- `line_number`: line number in source file
- `matched_line`: raw matched log line
- `extracted_ips`: comma-separated valid IPv4 addresses found in line

## Publish to GitHub

```bash
git init
# if not already initialized

git add .
git commit -m "Add boolean log query tool with CSV export"
git branch -M main
git remote add origin <your-github-repo-url>
git push -u origin main
```

If this repository already has a remote, replace `<your-github-repo-url>` with your target URL and push.
