from __future__ import annotations
"""Alpha Expression Parser - 因子表达式解析器.

解析 WorldQuant Alpha 表达式，验证语法并转换为可执行函数。
"""


from typing import Any


class AlphaToken:
    """Alpha 表达式 Token."""

    def __init__(
        self,
        token_type: str,
        value: str,
        start: int = 0,
        end: int = 0,
    ) -> None:
        self.token_type = token_type
        self.value = value
        self.start = start
        self.end = end


class AlphaLexer:
    """词法分析器."""

    KEYWORDS = {
        "rank": "OP_RANK",
        "delay": "OP_DELAY",
        "delta": "OP_DELTA",
        "ts_sum": "OP_TS_SUM",
        "ts_mean": "OP_TS_MEAN",
        "ts_stddev": "OP_TS_STDDEV",
        "ts_max": "OP_TS_MAX",
        "ts_min": "OP_TS_MIN",
        "ts_argmax": "OP_TS_ARGMAX",
        "ts_argmin": "OP_TS_ARGMIN",
        "ts_correlation": "OP_TS_CORRELATION",
        "ts_covariance": "OP_TS_COVARIANCE",
        "ts_skewness": "OP_TS_SKEWNESS",
        "ts_zscore": "OP_TS_ZSCORE",
        "ts_decay_linear": "OP_TS_DECAY_LINEAR",
        "ts_decay_exponential": "OP_TS_DECAY_EXPONENTIAL",
        "signed_power": "OP_SIGNED_POWER",
        "signed_log": "OP_SIGNED_LOG",
        "log": "OP_LOG",
        "abs": "OP_ABS",
        "sqrt": "OP_SQRT",
        "sign": "OP_SIGN",
        "returns_0_1": "VAR_RETURNS",
        "close_0": "VAR_CLOSE",
        "volume_0": "VAR_VOLUME",
        "open_0": "VAR_OPEN",
        "high_0": "VAR_HIGH",
        "low_0": "VAR_LOW",
    }

    OPERATORS = {"+", "-", "*", "/", "(", ")", ",", "^"}

    def tokenize(self, expr: str) -> list[AlphaToken]:
        """将表达式转换为 Token 列表."""
        tokens = []
        pos = 0
        expr = expr.strip()

        while pos < len(expr):
            if expr[pos].isspace():
                pos += 1
                continue

            if expr[pos] in self.OPERATORS:
                tokens.append(AlphaToken("OP", expr[pos], pos, pos + 1))
                pos += 1
                continue

            if expr[pos].isalpha() or expr[pos] == "_":
                start = pos
                while pos < len(expr) and (expr[pos].isalnum() or expr[pos] == "_"):
                    pos += 1

                value = expr[start:pos]
                token_type = self.KEYWORDS.get(value, "IDENTIFIER")
                tokens.append(AlphaToken(token_type, value, start, pos))
                continue

            if expr[pos].isdigit():
                start = pos
                while pos < len(expr) and (expr[pos].isdigit() or expr[pos] == "."):
                    pos += 1
                tokens.append(AlphaToken("NUMBER", expr[start:pos], start, pos))
                continue

            pos += 1

        return tokens


class AlphaParser:
    """语法分析器."""

    def __init__(self) -> None:
        self._lexer = AlphaLexer()
        self._tokens: list[AlphaToken] = []
        self._pos = 0

    def parse(self, expr: str) -> dict[str, Any]:
        """解析表达式，返回 AST."""
        self._tokens = self._lexer.tokenize(expr)
        self._pos = 0

        if not self._tokens:
            return {"error": "Empty expression"}

        try:
            ast = self._parse_expression()
            return {
                "type": "Program",
                "body": ast,
                "tokens": len(self._tokens),
            }
        except Exception as e:
            return {"error": str(e)}

    def _parse_expression(self) -> dict[str, Any]:
        """解析表达式节点."""
        return self._parse_additive()

    def _parse_additive(self) -> dict[str, Any]:
        """解析加减运算."""
        left = self._parse_multiplicative()

        while self._peek():
            op = self._peek().value
            if op in ("+", "-"):
                self._advance()
                right = self._parse_multiplicative()
                left = {
                    "type": "BinaryExpression",
                    "operator": op,
                    "left": left,
                    "right": right,
                }
            else:
                break

        return left

    def _parse_multiplicative(self) -> dict[str, Any]:
        """解析乘除运算."""
        left = self._parse_unary()

        while self._peek():
            op = self._peek().value
            if op in ("*", "/", "^"):
                self._advance()
                right = self._parse_unary()
                left = {
                    "type": "BinaryExpression",
                    "operator": op,
                    "left": left,
                    "right": right,
                }
            else:
                break

        return left

    def _parse_unary(self) -> dict[str, Any]:
        """解析一元运算."""
        if self._peek() and self._peek().value == "-":
            self._advance()
            operand = self._parse_unary()
            return {"type": "UnaryExpression", "operator": "-", "argument": operand}

        return self._parse_primary()

    def _parse_primary(self) -> dict[str, Any]:
        """解析基本单元."""
        token = self._peek()

        if not token:
            return {"type": "Empty"}

        if token.token_type.startswith("OP_"):
            return self._parse_call()

        if token.token_type == "IDENTIFIER":
            self._advance()
            return {"type": "Identifier", "name": token.value}

        if token.token_type == "NUMBER":
            self._advance()
            return {"type": "Literal", "value": float(token.value)}

        if token.value == "(":
            self._advance()
            expr = self._parse_expression()
            if self._peek() and self._peek().value == ")":
                self._advance()
            return expr

        self._advance()
        return {"type": "Unknown", "value": token.value}

    def _parse_call(self) -> dict[str, Any]:
        """解析函数调用."""
        token = self._peek()

        if not token or not token.token_type.startswith("OP_"):
            return self._parse_primary()

        self._advance()
        name = token.value

        if self._peek() and self._peek().value == "(":
            self._advance()
            args = []

            if self._peek() and self._peek().value != ")":
                args.append(self._parse_expression())

                while self._peek() and self._peek().value == ",":
                    self._advance()
                    args.append(self._parse_expression())

            if self._peek() and self._peek().value == ")":
                self._advance()

            return {"type": "CallExpression", "name": name, "arguments": args}

        return {"type": "Identifier", "name": name}

    def _peek(self) -> AlphaToken | None:
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        return None

    def _advance(self) -> AlphaToken | None:
        if self._pos < len(self._tokens):
            token = self._tokens[self._pos]
            self._pos += 1
            return token
        return None


class AlphaValidator:
    """表达式验证器."""

    def __init__(self) -> None:
        self._parser = AlphaParser()
        self._known_operators = set(AlphaLexer.KEYWORDS.keys())

    def validate(self, expr: str) -> dict[str, Any]:
        """验证表达式语法和语义."""
        result = self._parser.parse(expr)

        if "error" in result:
            return result

        errors = []
        warnings = []

        tokens = self._parser._tokens
        token_values = [t.value for t in tokens]

        for token in tokens:
            if token.token_type == "IDENTIFIER" and token.value not in self._known_operators:
                warnings.append(f"Unknown identifier: {token.value}")

        if not token_values:
            errors.append("Empty expression")

        paren_balance = token_values.count("(") - token_values.count(")")
        if paren_balance != 0:
            errors.append(f"Unbalanced parentheses: {paren_balance:+d}")

        comma_count = token_values.count(",")
        if comma_count > 10:
            warnings.append(f"High argument count ({comma_count}), consider simplifying")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "complexity": self._calculate_complexity(tokens),
            "ast": result,
        }

    def _calculate_complexity(self, tokens: list[AlphaToken]) -> int:
        """计算表达式复杂度."""
        score = 0
        for t in tokens:
            if t.token_type.startswith("OP_"):
                score += 2
            elif t.token_type == "NUMBER":
                score += 1

        return score


_alpha_parser = AlphaParser()
_alpha_validator = AlphaValidator()


def parse_alpha_expression(expr: str) -> dict[str, Any]:
    """解析 Alpha 表达式."""
    return _alpha_parser.parse(expr)


def validate_alpha_expression(expr: str) -> dict[str, Any]:
    """验证 Alpha 表达式."""
    return _alpha_validator.validate(expr)


def format_validation_error(errors: list[str]) -> str:
    """格式化验证错误."""
    if not errors:
        return "✓ 表达式验证通过"

    lines = ["✕ 表达式验证失败"]
    for e in errors:
        lines.append(f"  - {e}")

    return "\n".join(lines)
