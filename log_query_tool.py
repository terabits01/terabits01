#!/usr/bin/env python3
"""Query large log files with boolean expressions and export matches to CSV."""

from __future__ import annotations

import argparse
import csv
import ipaddress
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

TOKEN_PATTERN = re.compile(r"\s*(\(|\)|AND\b|OR\b|NOT\b|\"[^\"]*\"|'[^']*'|[^\s()]+)", re.IGNORECASE)
IP_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


@dataclass
class Node:
    kind: str
    value: str | None = None
    left: "Node | None" = None
    right: "Node | None" = None


class QueryParser:
    def __init__(self, query: str):
        self.tokens = self._tokenize(query)
        self.pos = 0

    @staticmethod
    def _tokenize(query: str) -> List[str]:
        tokens = TOKEN_PATTERN.findall(query)
        if not tokens:
            raise ValueError("Query is empty")
        cleaned: List[str] = []
        for token in tokens:
            token = token.strip()
            if not token:
                continue
            if token[0] in {'"', "'"} and token[-1] == token[0]:
                token = token[1:-1]
            cleaned.append(token)
        return cleaned

    def _peek(self) -> str | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _consume(self) -> str:
        token = self._peek()
        if token is None:
            raise ValueError("Unexpected end of query")
        self.pos += 1
        return token

    def parse(self) -> Node:
        node = self._parse_or()
        if self._peek() is not None:
            raise ValueError(f"Unexpected token: {self._peek()}")
        return node

    def _parse_or(self) -> Node:
        node = self._parse_and()
        while (token := self._peek()) and token.upper() == "OR":
            self._consume()
            node = Node("OR", left=node, right=self._parse_and())
        return node

    def _parse_and(self) -> Node:
        node = self._parse_not()
        while (token := self._peek()) and token.upper() == "AND":
            self._consume()
            node = Node("AND", left=node, right=self._parse_not())
        return node

    def _parse_not(self) -> Node:
        token = self._peek()
        if token and token.upper() == "NOT":
            self._consume()
            return Node("NOT", left=self._parse_not())
        return self._parse_primary()

    def _parse_primary(self) -> Node:
        token = self._consume()
        if token == "(":
            node = self._parse_or()
            if self._consume() != ")":
                raise ValueError("Missing closing parenthesis")
            return node
        if token == ")":
            raise ValueError("Unexpected closing parenthesis")
        return Node("TERM", value=token)


def evaluate(node: Node, line: str) -> bool:
    kind = node.kind
    if kind == "TERM":
        assert node.value is not None
        return node.value.lower() in line.lower()
    if kind == "AND":
        return evaluate(node.left, line) and evaluate(node.right, line)
    if kind == "OR":
        return evaluate(node.left, line) or evaluate(node.right, line)
    if kind == "NOT":
        return not evaluate(node.left, line)
    raise ValueError(f"Unknown node kind: {kind}")


def extract_ips(line: str) -> str:
    ips: list[str] = []
    for match in IP_PATTERN.findall(line):
        try:
            ipaddress.ip_address(match)
            ips.append(match)
        except ValueError:
            continue
    return ",".join(dict.fromkeys(ips))


def query_logs(paths: Sequence[Path], query_ast: Node) -> Iterable[dict[str, str]]:
    for path in paths:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line_number, raw in enumerate(handle, start=1):
                line = raw.rstrip("\n")
                if evaluate(query_ast, line):
                    yield {
                        "source_file": str(path),
                        "line_number": str(line_number),
                        "matched_line": line,
                        "extracted_ips": extract_ips(line),
                    }


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query large log files and export matches to CSV.")
    parser.add_argument("query", help="Search query using AND/OR/NOT and parentheses")
    parser.add_argument("inputs", nargs="+", help="Input log files")
    parser.add_argument("-o", "--output", default="results.csv", help="Output CSV file path")
    return parser.parse_args(argv)


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    files = [Path(p) for p in args.inputs]
    missing = [str(p) for p in files if not p.exists()]
    if missing:
        print(f"Missing files: {', '.join(missing)}", file=sys.stderr)
        return 2

    try:
        query_ast = QueryParser(args.query).parse()
    except ValueError as exc:
        print(f"Invalid query: {exc}", file=sys.stderr)
        return 2

    with Path(args.output).open("w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=["source_file", "line_number", "matched_line", "extracted_ips"])
        writer.writeheader()
        for row in query_logs(files, query_ast):
            writer.writerow(row)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
