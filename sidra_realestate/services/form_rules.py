# Copyright (c) 2026, Mohamoud Abdullahi Sheikh
"""Field rules (`depends_on`, `read_only_depends_on`, `mandatory_depends_on`) without running code.

Desk evaluates these rules as JavaScript in the browser; Frappe has no server-side evaluator.
The Berjaya forms need the same rules on the server (to refuse a write to a field that is
read-only by rule) and in the browser (to show and hide fields as the user types). So each rule
is parsed once, here, into a small tree that both sides evaluate the same way. Nothing is ever
executed: an expression outside the grammar below is "not understood" (`parse` returns None)
and the caller decides the safe reading (shown, read-only, or not required, as appropriate).

Grammar, which covers every rule in this app (see `test_form_rules.py`):
	rule    := "eval:" expr | fieldname
	expr    := and ("||" and)*
	and     := unary ("&&" unary)*
	unary   := "!" unary | "(" expr ")" | compare
	compare := value [("==" | "!=" | "===" | "!==") value]
	value   := "doc." name | string | number | true | false | null
	value   := "in_list(" list "," value ")" | list ".includes(" value ")"

Tree nodes (JSON): {"or": [..]}, {"and": [..]}, {"not": x}, {"eq": [a, b]}, {"ne": [a, b]},
{"in": [[values], x]}, {"field": name}, {"lit": value}.
"""

import re

_TOKEN = re.compile(
	r"""\s*(?:
		(?P<str>'(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*")
		|(?P<num>-?\d+(?:\.\d+)?)
		|(?P<op>===|!==|==|!=|&&|\|\||!|\(|\)|\[|\]|,|\.)
		|(?P<name>[A-Za-z_][A-Za-z0-9_]*)
	)""",
	re.VERBOSE,
)
_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class _Unknown(Exception):
	pass


def parse(rule: str | None):
	"""The rule as a tree, or None when there is no rule or it is not understood."""
	if not rule or not isinstance(rule, str):
		return None
	text = rule.strip()
	if not text.startswith("eval:"):
		return {"field": text} if _NAME.match(text) else None
	try:
		tokens = _tokens(text[len("eval:") :])
		parser = _Parser(tokens)
		tree = parser.expr()
		if parser.position != len(tokens):
			raise _Unknown
		return tree
	except _Unknown:
		return None


def _tokens(text):
	tokens, position = [], 0
	while position < len(text):
		if text[position:].strip() == "":
			break
		match = _TOKEN.match(text, position)
		if not match or match.end() == position:
			raise _Unknown
		position = match.end()
		kind = match.lastgroup
		value = match.group(kind)
		if kind == "str":
			value = value[1:-1].replace("\\'", "'").replace('\\"', '"')
		tokens.append((kind, value))
	return tokens


class _Parser:
	def __init__(self, tokens):
		self.tokens = tokens
		self.position = 0

	def peek(self, offset=0):
		index = self.position + offset
		return self.tokens[index] if index < len(self.tokens) else (None, None)

	def take(self, kind=None, value=None):
		token = self.peek()
		if token[0] is None or (kind and token[0] != kind) or (value is not None and token[1] != value):
			raise _Unknown
		self.position += 1
		return token

	def accept(self, value):
		if self.peek() == ("op", value):
			self.position += 1
			return True
		return False

	def expr(self):
		parts = [self.conjunction()]
		while self.accept("||"):
			parts.append(self.conjunction())
		return parts[0] if len(parts) == 1 else {"or": parts}

	def conjunction(self):
		parts = [self.unary()]
		while self.accept("&&"):
			parts.append(self.unary())
		return parts[0] if len(parts) == 1 else {"and": parts}

	def unary(self):
		if self.accept("!"):
			return {"not": self.unary()}
		if self.accept("("):
			inner = self.expr()
			self.take("op", ")")
			return inner
		left = self.value()
		for operator, node in (("===", "eq"), ("==", "eq"), ("!==", "ne"), ("!=", "ne")):
			if self.accept(operator):
				return {node: [left, self.value()]}
		return left

	def value(self):
		kind, value = self.peek()
		if kind == "str":
			self.position += 1
			return {"lit": value}
		if kind == "num":
			self.position += 1
			return {"lit": float(value) if "." in value else int(value)}
		if kind == "op" and value == "[":
			items = self.literal_list()
			self.take("op", ".")
			self.take("name", "includes")
			self.take("op", "(")
			subject = self.value()
			self.take("op", ")")
			return {"in": [items, subject]}
		if kind == "name":
			self.position += 1
			if value in ("true", "false", "null"):
				return {"lit": {"true": True, "false": False, "null": None}[value]}
			if value == "doc":
				self.take("op", ".")
				return {"field": self.take("name")[1]}
			if value == "in_list":
				self.take("op", "(")
				items = self.literal_list()
				self.take("op", ",")
				subject = self.value()
				self.take("op", ")")
				return {"in": [items, subject]}
		raise _Unknown

	def literal_list(self):
		self.take("op", "[")
		items = []
		while not self.accept("]"):
			kind, value = self.take()
			if kind == "str":
				items.append(value)
			elif kind == "num":
				items.append(float(value) if "." in value else int(value))
			else:
				raise _Unknown
			if not self.accept(","):
				self.take("op", "]")
				break
		return items


# ---------------------------------------------------------------------- evaluation
def evaluate(tree, values) -> bool:
	"""JavaScript truthiness of the rule for `values` (a dict or a Document)."""
	return _truthy(_value(tree, values))


def _get(values, field):
	if hasattr(values, "get"):
		return values.get(field)
	return getattr(values, field, None)


def _value(node, values):
	if "lit" in node:
		return node["lit"]
	if "field" in node:
		return _get(values, node["field"])
	if "not" in node:
		return not evaluate(node["not"], values)
	if "and" in node:
		return all(evaluate(part, values) for part in node["and"])
	if "or" in node:
		return any(evaluate(part, values) for part in node["or"])
	if "eq" in node:
		return _same(*(_value(side, values) for side in node["eq"]))
	if "ne" in node:
		return not _same(*(_value(side, values) for side in node["ne"]))
	if "in" in node:
		items, subject = node["in"]
		return any(_same(item, _value(subject, values)) for item in items)
	raise ValueError(f"unknown rule node {node}")


def _plain(value):
	if value is None:
		return ""
	if isinstance(value, bool):
		return "1" if value else "0"
	if isinstance(value, float) and value.is_integer():
		value = int(value)
	return str(value)


def _same(left, right):
	"""Loose equality as the rules use it: values are compared as text, a blank as ''."""
	return _plain(left) == _plain(right)


def _truthy(value):
	if value is None or value is False:
		return False
	if isinstance(value, int | float):
		return value != 0
	if isinstance(value, str):
		return value != ""
	if isinstance(value, list | tuple | dict):
		return True
	return bool(value)
