"""Evaluate a restricted SQL boolean / numeric dialect against a CSV DataFrame."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Optional, Union

import pandas as pd

# Common spreadsheet versions of values stored as numbers in SQL.
TRUE_VALUES = {"1", "y", "yes", "true", "t"}
FALSE_VALUES = {"0", "n", "no", "false", "f"}
MALE_VALUES = {"1", "m", "male"}
FEMALE_VALUES = {"2", "f", "female"}

KEYWORDS = {
    "AND",
    "OR",
    "NOT",
    "BETWEEN",
    "IN",
    "IS",
    "NULL",
    "TRUE",
    "FALSE",
}

TOKEN_RE = re.compile(
    r"""
    (?P<STRING>'(?:[^']*)')
    |(?P<NUM>\d+(?:\.\d+)?)
    |(?P<OP><>|!=|<=|>=|=|<|>)
    |(?P<LPAREN>\()
    |(?P<RPAREN>\))
    |(?P<COMMA>,)
    |(?P<IDENT>[A-Za-z_][A-Za-z0-9_]*)
    |(?P<WS>\s+)
    """,
    re.VERBOSE,
)


# Small record types used to turn a SQL filter into manageable parts.
@dataclass
class Token:
    kind: str
    value: str


def tokenize(expr: str) -> list[Token]:
    # Breaks a supported SQL filter into words, values and operators.
    tokens: list[Token] = []
    pos = 0
    text = expr.strip()
    while pos < len(text):
        m = TOKEN_RE.match(text, pos)
        if not m:
            raise ValueError(f"Unexpected token at {pos}: {text[pos:pos + 20]!r}")
        kind = m.lastgroup or ""
        raw = m.group()
        pos = m.end()
        if kind == "WS":
            continue
        if kind == "IDENT" and raw.upper() in KEYWORDS:
            tokens.append(Token(raw.upper(), raw.upper()))
        elif kind == "STRING":
            tokens.append(Token("STRING", raw[1:-1]))
        else:
            tokens.append(Token(kind, raw))
    return tokens


@dataclass
class Literal:
    value: Any


@dataclass
class Column:
    name: str


@dataclass
class BinOp:
    op: str
    left: Any
    right: Any


@dataclass
class Between:
    col: Any
    low: Any
    high: Any


@dataclass
class InList:
    col: Any
    values: list[Any]


@dataclass
class IsNull:
    col: Any
    negated: bool


@dataclass
class NotOp:
    inner: Any


@dataclass
class BoolConst:
    value: bool


Node = Union[Literal, Column, BinOp, Between, InList, IsNull, NotOp, BoolConst]


class Parser:
    # Rebuilds those parts in the same AND, OR and comparison order as the SQL.
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.i = 0

    def peek(self) -> Optional[Token]:
        return self.tokens[self.i] if self.i < len(self.tokens) else None

    def accept(self, *kinds: str) -> Optional[Token]:
        tok = self.peek()
        if tok and tok.kind in kinds:
            self.i += 1
            return tok
        return None

    def expect(self, *kinds: str) -> Token:
        tok = self.accept(*kinds)
        if not tok:
            got = self.peek()
            raise ValueError(f"Expected {kinds}, got {got}")
        return tok

    def parse(self) -> Node:
        if not self.tokens:
            return BoolConst(True)
        node = self.parse_or()
        if self.peek() is not None:
            raise ValueError(f"Trailing token: {self.peek()}")
        return node

    def parse_or(self) -> Node:
        node = self.parse_and()
        while self.accept("OR"):
            node = BinOp("OR", node, self.parse_and())
        return node

    def parse_and(self) -> Node:
        node = self.parse_not()
        while True:
            tok = self.peek()
            if tok and tok.kind == "AND":
                # BETWEEN uses AND as a delimiter, handled inside comparison
                self.i += 1
                node = BinOp("AND", node, self.parse_not())
            else:
                break
        return node

    def parse_not(self) -> Node:
        if self.accept("NOT"):
            return NotOp(self.parse_not())
        return self.parse_primary()

    def parse_primary(self) -> Node:
        if self.accept("LPAREN"):
            node = self.parse_or()
            self.expect("RPAREN")
            return node
        if self.accept("TRUE"):
            return BoolConst(True)
        if self.accept("FALSE"):
            return BoolConst(False)
        return self.parse_comparison()

    def parse_value(self) -> Node:
        if self.accept("LPAREN"):
            node = self.parse_or()
            self.expect("RPAREN")
            return node
        tok = self.accept("IDENT", "NUM", "STRING", "TRUE", "FALSE", "NULL")
        if not tok:
            raise ValueError(f"Expected value, got {self.peek()}")
        if tok.kind == "IDENT":
            return Column(tok.value)
        if tok.kind == "NUM":
            return Literal(float(tok.value) if "." in tok.value else int(tok.value))
        if tok.kind == "STRING":
            return Literal(tok.value)
        if tok.kind == "TRUE":
            return BoolConst(True)
        if tok.kind == "FALSE":
            return BoolConst(False)
        return Literal(None)

    def parse_comparison(self) -> Node:
        left = self.parse_value()
        tok = self.peek()
        if tok and tok.kind == "BETWEEN":
            self.i += 1
            low = self.parse_value()
            self.expect("AND")
            high = self.parse_value()
            return Between(left, low, high)
        if tok and tok.kind == "IN":
            self.i += 1
            self.expect("LPAREN")
            values = [self.parse_value()]
            while self.accept("COMMA"):
                values.append(self.parse_value())
            self.expect("RPAREN")
            return InList(left, values)
        if tok and tok.kind == "IS":
            self.i += 1
            negated = bool(self.accept("NOT"))
            self.expect("NULL")
            return IsNull(left, negated)
        if tok and tok.kind == "OP":
            op = tok.value
            self.i += 1
            right = self.parse_value()
            return BinOp(op, left, right)
        # Bare column treated as truthy
        return left


def parse_expression(expr: str) -> Node:
    # Converts one SQL filter into the internal form evaluated against the CSV.
    text = (expr or "").strip()
    if not text or text.upper() == "TRUE":
        return BoolConst(True)
    return Parser(tokenize(text)).parse()


def _is_blank(series: pd.Series) -> pd.Series:
    if series.dtype == object or str(series.dtype) == "string":
        stripped = series.astype(str).str.strip()
        return series.isna() | stripped.isin(("", "nan", "None", "NaT"))
    return series.isna()


def _as_string(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip()


def _as_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def infer_equivalents(series: pd.Series, literal: Any) -> set[str]:
    """Links SQL codes such as 1/2 or 1/0 to CSV labels such as Male/Female or Y/N."""
    accepted = {str(literal).strip()}
    try:
        if float(literal) == int(float(literal)):
            accepted.add(str(int(float(literal))))
    except (TypeError, ValueError):
        pass

    sample = {
        v.lower()
        for v in _as_string(series.dropna().astype(str)).unique()
        if v and v.lower() not in {"nan", "none"}
    }
    looks_gender = bool(sample & {"male", "female", "m", "f"}) or sample <= (
        MALE_VALUES | FEMALE_VALUES | {""}
    )
    looks_flag = bool(sample & {"y", "n", "yes", "no"}) or sample <= (
        TRUE_VALUES | FALSE_VALUES | {""}
    )

    key = str(literal).strip().lower()
    if looks_gender:
        if key in MALE_VALUES:
            accepted |= {"1", "m", "male", "Male", "M"}
        elif key in FEMALE_VALUES:
            accepted |= {"2", "f", "female", "Female", "F"}
    if looks_flag:
        if key in TRUE_VALUES:
            accepted |= {"1", "Y", "y", "Yes", "yes", "TRUE", "true", "T", "t"}
        elif key in FALSE_VALUES:
            accepted |= {"0", "N", "n", "No", "no", "FALSE", "false", "F", "f"}
    return {a.lower() for a in accepted}


def _literal_value(node: Node) -> Any:
    if isinstance(node, Literal):
        return node.value
    if isinstance(node, BoolConst):
        return node.value
    raise ValueError(f"Expected literal, got {type(node).__name__}")


def _column_name(node: Node) -> str:
    if isinstance(node, Column):
        return node.name
    raise ValueError(f"Expected column, got {type(node).__name__}")


class ExpressionEngine:
    # Applies supported SQL comparisons to every row in the uploaded CSV.
    def __init__(
        self,
        df: pd.DataFrame,
        resolve_column: Callable[[str], str],
        extra_value_maps: Optional[dict[str, dict[str, list[str]]]] = None,
    ):
        self.df = df
        self.resolve_column = resolve_column
        self.extra_value_maps = extra_value_maps or {}

    def series_for(self, sql_name: str) -> tuple[str, pd.Series]:
        csv_name = self.resolve_column(sql_name)
        if csv_name not in self.df.columns:
            raise KeyError(f"CSV column not found for {sql_name} → {csv_name}")
        return csv_name, self.df[csv_name]

    def eval_bool(self, expr: str) -> pd.Series:
        # Returns one True/False result per source row for count calculations.
        node = parse_expression(expr)
        result = self._eval(node)
        if isinstance(result, pd.Series):
            if result.dtype == bool or str(result.dtype) == "boolean":
                return result.fillna(False).astype(bool)
            numeric = _as_numeric(result)
            if numeric.notna().any():
                return (numeric.fillna(0) != 0)
            text = _as_string(result).str.lower()
            return text.isin(TRUE_VALUES | MALE_VALUES | {"male"})
        return pd.Series([bool(result)] * len(self.df), index=self.df.index)

    def eval_numeric(self, expr: str) -> pd.Series:
        # Returns source values for genuine numeric sum calculations.
        node = parse_expression(expr)
        result = self._eval(node)
        if isinstance(result, pd.Series):
            return _as_numeric(result)
        return pd.Series([result] * len(self.df), index=self.df.index)

    def referenced_sql_columns(self, expr: str) -> list[str]:
        # Lists the SQL fields that must be found through the mapping workbook.
        tokens = tokenize(expr) if expr.strip() and expr.strip().upper() != "TRUE" else []
        names = []
        for tok in tokens:
            if tok.kind == "IDENT":
                names.append(tok.value)
        return names

    def _eval(self, node: Node) -> Any:
        # Evaluates each part of the filter and combines the row results.
        if isinstance(node, BoolConst):
            return pd.Series([node.value] * len(self.df), index=self.df.index)
        if isinstance(node, Literal):
            return node.value
        if isinstance(node, Column):
            _, series = self.series_for(node.name)
            return series
        if isinstance(node, NotOp):
            inner = self._eval(node.inner)
            if isinstance(inner, pd.Series):
                if inner.dtype == bool:
                    return ~inner.fillna(False)
                return _as_numeric(inner).fillna(0) == 0
            return not inner
        if isinstance(node, IsNull):
            _, series = self.series_for(_column_name(node.col))
            blank = _is_blank(series)
            return ~blank if node.negated else blank
        if isinstance(node, Between):
            _, series = self.series_for(_column_name(node.col))
            low = _literal_value(node.low)
            high = _literal_value(node.high)
            num = _as_numeric(series)
            return num.ge(float(low)) & num.le(float(high))
        if isinstance(node, InList):
            _, series = self.series_for(_column_name(node.col))
            mask = pd.Series(False, index=self.df.index)
            for item in node.values:
                mask = mask | self._equals(series, _column_name(node.col), _literal_value(item))
            return mask
        if isinstance(node, BinOp):
            if node.op == "AND":
                return self._eval(node.left) & self._eval(node.right)
            if node.op == "OR":
                return self._eval(node.left) | self._eval(node.right)
            left = self._eval(node.left)
            right = self._eval(node.right)
            if node.op in {"=", "=="}:
                if isinstance(node.left, Column):
                    return self._equals(left, node.left.name, right)
                return left == right
            if node.op in {"!=", "<>"}:
                if isinstance(node.left, Column):
                    return ~self._equals(left, node.left.name, right)
                return left != right
            lnum = _as_numeric(left) if isinstance(left, pd.Series) else left
            rnum = float(right) if not isinstance(right, pd.Series) else _as_numeric(right)
            if node.op == ">":
                return lnum > rnum
            if node.op == "<":
                return lnum < rnum
            if node.op == ">=":
                return lnum >= rnum
            if node.op == "<=":
                return lnum <= rnum
        raise ValueError(f"Cannot evaluate {node}")

    def _equals(self, series: pd.Series, sql_name: str, literal: Any) -> pd.Series:
        # Compares equivalent text and numeric forms without changing source data.
        if literal is None:
            return _is_blank(series)
        extra = self.extra_value_maps.get(sql_name, {})
        mapped = extra.get(str(literal)) or extra.get(literal)
        accepted = {str(literal).strip().lower()}
        if mapped:
            accepted |= {str(v).strip().lower() for v in mapped}
        accepted |= infer_equivalents(series, literal)
        text = _as_string(series).str.lower()
        mask = text.isin(accepted)
        try:
            num_lit = float(literal)
            mask = mask | (_as_numeric(series) == num_lit)
        except (TypeError, ValueError):
            pass
        return mask.fillna(False)
