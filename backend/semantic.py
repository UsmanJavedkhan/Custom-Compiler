"""
SMILE Semantic Analysis -- Syntax-Directed Translation (SDT).

This is the semantic phase of the SMILE compiler. It follows the classic
Dragon-book recipe (Ch. 5, Syntax-Directed Definitions):

    1.  RULES & REGULATIONS OF THE GRAMMAR
        The student attaches a *semantic rule* to every production of the
        grammar -- a Syntax-Directed Definition (SDD).  We support
        **synthesized attributes only** (an S-attributed definition): every
        attribute of a head is computed from the attributes of its children.

            PRODUCTION            SEMANTIC RULE
            E -> E joro T          { E.val = E1.val + T.val }
            E -> T                 { E.val = T.val }
            T -> num               { T.val = num.val }

        In a rule the *head* is written bare (E), and a child that shares the
        head's symbol is subscripted (E1, E2, ...).  Terminals expose a
        built-in `.val` / `.lexeme` (e.g. `num.val` is the number 14).

    2.  ANNOTATED PARSE TREE
        We parse the input with the SLR(1) driver to obtain the parse tree,
        then walk it bottom-up (post-order) and evaluate each production's
        rule, decorating every node with its attribute values.  The result is
        the *annotated parse tree*.

Reuses the syntax-phase machinery (parse_grammar / build_slr / token mapping)
so the grammar lives in exactly one place.
"""

import ast
from typing import Dict, List, Optional, Tuple

from parsers import (
    DEFAULT_GRAMMAR_TEXT,
    END,
    EPS,
    EPSILON_TOKENS,
    Grammar,
    build_slr,
    grammar_listing,
    parse_grammar,
    production_str,
    tokens_to_terminals,
)


# A default SDD that matches DEFAULT_GRAMMAR_TEXT -- the classic expression
# evaluator.  `id.val` falls back to the identifier name (string) since the
# value of a variable is unknown without a symbol table; numeric programs never
# fire that production.
DEFAULT_SEMANTIC_TEXT = (
    "E -> E joro T      { E.val = E1.val + T.val }\n"
    "E -> E ghata T     { E.val = E1.val - T.val }\n"
    "E -> T             { E.val = T.val }\n"
    "T -> T guna F      { T.val = T1.val * F.val }\n"
    "T -> T taqseem F   { T.val = T1.val / F.val }\n"
    "T -> F             { T.val = F.val }\n"
    "F -> id            { F.val = id.val }\n"
    "F -> num           { F.val = num.val }"
)


class SemanticError(Exception):
    """Raised while evaluating a semantic rule (faaaah: ... message)."""


# ───────────────────────── Safe rule evaluator ─────────────────────────
# Semantic-rule expressions are evaluated over a tiny, whitelisted subset of
# Python via the `ast` module -- never raw eval(). Only arithmetic, comparison,
# boolean ops, literals, name/attribute lookups and a few safe builtins.

_SAFE_FUNCS = {
    "int": int, "float": float, "str": str, "bool": bool,
    "abs": abs, "round": round, "len": len, "min": min, "max": max,
}

_BINOPS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.FloorDiv: lambda a, b: a // b,
    ast.Mod: lambda a, b: a % b,
    ast.Pow: lambda a, b: a ** b,
}

_CMPOPS = {
    ast.Eq: lambda a, b: a == b,
    ast.NotEq: lambda a, b: a != b,
    ast.Lt: lambda a, b: a < b,
    ast.LtE: lambda a, b: a <= b,
    ast.Gt: lambda a, b: a > b,
    ast.GtE: lambda a, b: a >= b,
}


class _AttrRef:
    """A symbol occurrence in a rule (e.g. `E1`, `T`, `num`); `.attr` reads an
    attribute, raising a SemanticError if it was never set."""

    def __init__(self, name: str, attrs: Dict[str, object]):
        object.__setattr__(self, "_name", name)
        object.__setattr__(self, "_attrs", attrs)

    def __getattr__(self, item: str):
        attrs = object.__getattribute__(self, "_attrs")
        if item in attrs:
            return attrs[item]
        name = object.__getattribute__(self, "_name")
        raise SemanticError(
            f"faaaah: '{name}.{item}' ki koi value nahi -- ye attribute kahin set nahi hua"
        )


def _eval_node(node: ast.AST, env: Dict[str, _AttrRef]):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, env)
    if isinstance(node, ast.Constant):          # numbers / strings / True / False
        return node.value
    if isinstance(node, ast.Name):
        if node.id not in env:
            raise SemanticError(
                f"faaaah: '{node.id}' is production mein koi symbol nahi -- "
                f"valid: {', '.join(sorted(env)) or '(koi nahi)'}"
            )
        return env[node.id]
    if isinstance(node, ast.Attribute):
        obj = _eval_node(node.value, env)
        return getattr(obj, node.attr)
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        left, right = _eval_node(node.left, env), _eval_node(node.right, env)
        try:
            return _BINOPS[type(node.op)](left, right)
        except ZeroDivisionError:
            raise SemanticError("faaaah: zero se taqseem? ye nahi ho sakta bhai")
        except TypeError:
            raise SemanticError(
                f"faaaah: type mismatch -> '{_fmt(left)}' aur '{_fmt(right)}' par "
                f"ye operation nahi ho sakta (shayad id ki value number nahi hai?)"
            )
    if isinstance(node, ast.UnaryOp):
        val = _eval_node(node.operand, env)
        if isinstance(node.op, ast.USub):
            return -val
        if isinstance(node.op, ast.UAdd):
            return +val
        if isinstance(node.op, ast.Not):
            return not val
    if isinstance(node, ast.BoolOp):
        vals = [_eval_node(v, env) for v in node.values]
        if isinstance(node.op, ast.And):
            return all(vals)
        return any(vals)
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in _CMPOPS:
        return _CMPOPS[type(node.ops[0])](
            _eval_node(node.left, env), _eval_node(node.comparators[0], env)
        )
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _SAFE_FUNCS:
        args = [_eval_node(a, env) for a in node.args]
        return _SAFE_FUNCS[node.func.id](*args)
    raise SemanticError(
        "faaaah: rule mein aisa expression nahi chalta -- sirf +-*/%, comparison, "
        "aur attribute (jaise E1.val) use karo"
    )


def _safe_eval(expr: str, env: Dict[str, _AttrRef]):
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        raise SemanticError(f"faaaah: rule ka expression galat hai -> '{expr}'")
    return _eval_node(tree, env)


# ─────────────────────── Semantic-rule parsing ─────────────────────────

# One target assignment, e.g. "E.val = E1.val + T.val".  The `=` must not be a
# comparison (==, <=, >=, !=).
import re as _re
_ASSIGN_RE = _re.compile(r"^\s*(\w+)\s*\.\s*(\w+)\s*=(?!=)\s*(.+)$", _re.DOTALL)


def _norm_symbols(part: str) -> Tuple[str, List[str]]:
    """Parse the production side of a rule line ('E -> E joro T') into (lhs, rhs)."""
    if "->" not in part:
        raise SemanticError(f"faaaah: rule line mein '->' nahi mila -> '{part.strip()}'")
    lhs, rhs_text = part.split("->", 1)
    lhs = lhs.strip()
    rhs = rhs_text.split()
    if any(s in EPSILON_TOKENS for s in rhs):
        rhs = []
    return lhs, rhs


def parse_semantic_rules(text: str, g: Grammar):
    """
    Parse the SDD text and attach a list of (target_attr, expr) assignments to
    each production index.

    Returns (rules_by_prod, errors)
      rules_by_prod : {prod_index: {"line": str, "assigns": [(attr, expr), ...]}}
    """
    # Index productions by (lhs, tuple(rhs)) so a rule line can find its prod.
    by_key: Dict[Tuple[str, Tuple[str, ...]], int] = {}
    for i, (lhs, rhs) in enumerate(g.productions):
        by_key[(lhs, tuple(rhs))] = i

    rules_by_prod: Dict[int, dict] = {}
    errors: List[str] = []

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("~"):
            continue
        if "{" not in line or "}" not in line:
            errors.append(
                f"faaaah: rule '{line}' mein semantic action {{...}} nahi mila"
            )
            continue

        prod_part, rest = line.split("{", 1)
        action_part = rest.rsplit("}", 1)[0]

        try:
            lhs, rhs = _norm_symbols(prod_part)
        except SemanticError as e:
            errors.append(str(e))
            continue

        key = (lhs, tuple(rhs))
        if key not in by_key:
            errors.append(
                f"faaaah: '{lhs} -> {' '.join(rhs) or EPS}' tumhari grammar mein "
                f"koi production nahi -- pehle grammar se match karo"
            )
            continue
        prod = by_key[key]

        assigns: List[Tuple[str, str]] = []
        for stmt in _split_statements(action_part):
            stmt = stmt.strip()
            if not stmt:
                continue
            m = _ASSIGN_RE.match(stmt)
            if not m:
                errors.append(
                    f"faaaah: rule '{stmt}' samajh nahi aaya -- "
                    f"format: HEAD.attr = expression"
                )
                continue
            target_sym, attr, expr = m.group(1), m.group(2), m.group(3).strip()
            if target_sym != lhs:
                errors.append(
                    f"faaaah: '{lhs} -> {' '.join(rhs) or EPS}' mein sirf head "
                    f"'{lhs}' ko value do (synthesized) -- '{target_sym}' ko nahi"
                )
                continue
            assigns.append((attr, expr))

        rules_by_prod[prod] = {"line": line, "assigns": assigns}

    return rules_by_prod, errors


def _split_statements(action: str) -> List[str]:
    """Split a semantic action into statements on ';' or newlines."""
    parts: List[str] = []
    for chunk in action.split("\n"):
        parts.extend(chunk.split(";"))
    return parts


# ───────────────────── Parse tree (SLR driver) ─────────────────────────
# A dedicated driver that records, at every internal node, which production was
# used to reduce it -- so we can later look up that production's semantic rule.

def build_annotated_tree(g, action, goto, terminals, display):
    """Run an SLR parse; return (tree, trace, accepted, error).

    Each node: {symbol, lexeme, terminal, prod, children}.
      * terminal leaf : symbol = grammar terminal (num/id/joro/...), lexeme = text
      * internal node : symbol = nonterminal, prod = production index used
    """
    state_stack = [0]
    node_stack: List[dict] = []
    pointer = 0
    trace: List[dict] = []
    guard = 0

    toks = list(terminals) + [END]
    disp = list(display) + [END]

    while True:
        guard += 1
        if guard > 10000:
            return None, trace, False, "faaaah: parser loop mein phans gaya"
        state = state_stack[-1]
        lookahead = toks[pointer]
        act = action.get(state, {}).get(lookahead)
        input_repr = " ".join(disp[pointer:])

        if act is None:
            trace.append({"action": f"error: unexpected '{disp[pointer]}'", "input": input_repr})
            return None, trace, False, (
                f"faaaah: syntax error -> '{disp[pointer]}' yahan nahi aana chahiye tha "
                f"(semantic analysis se pehle syntax theek karo)"
            )

        if act == "acc":
            trace.append({"action": "accept", "input": input_repr})
            return (node_stack[-1] if node_stack else None), trace, True, None

        if act.startswith("s"):
            nxt = int(act[1:])
            trace.append({"action": f"shift '{disp[pointer]}'", "input": input_repr})
            node_stack.append({
                "symbol": lookahead, "lexeme": disp[pointer],
                "terminal": True, "prod": None, "children": [],
            })
            state_stack.append(nxt)
            pointer += 1

        elif act.startswith("r"):
            prod = int(act[1:])
            lhs, rhs = g.productions[prod]
            trace.append({"action": f"reduce {prod}: {production_str(g, prod)}",
                          "input": input_repr})
            if rhs:
                children = node_stack[len(node_stack) - len(rhs):]
                del node_stack[len(node_stack) - len(rhs):]
                for _ in rhs:
                    state_stack.pop()
            else:
                children = [{"symbol": EPS, "lexeme": EPS, "terminal": True,
                             "prod": None, "children": []}]
            node_stack.append({
                "symbol": lhs, "lexeme": lhs, "terminal": False,
                "prod": prod, "children": children,
            })
            goto_state = goto.get(state_stack[-1], {}).get(lhs)
            if goto_state is None:
                return None, trace, False, f"faaaah: no GOTO for {lhs}"
            state_stack.append(goto_state)


# ───────────────────── Attribute evaluation ────────────────────────────

def _record_assignment(node: dict, symtab: Dict[str, object]):
    """If this node is an assignment `<id> rakho <expr> ...` (e.g. DECL/ASG),
    store the assigned value in the symbol table so later uses see it."""
    children = node["children"]
    for k, c in enumerate(children):
        if c.get("terminal") and c.get("lexeme") == "rakho":
            target = None
            for j in range(k):                 # the id before 'rakho' is the target
                if children[j].get("symbol") == "id":
                    target = children[j].get("lexeme")
            value = None
            for j in range(k + 1, len(children)):   # first valued child after 'rakho'
                a = children[j].get("attrs") or {}
                if "val" in a:
                    value = a["val"]
                    break
            if target is not None and value is not None:
                symtab[target] = value
            return


def _coerce_terminal(symbol: str, lexeme: str):
    """Built-in `.val` for a terminal leaf."""
    if symbol == "num":
        return float(lexeme) if "." in lexeme else int(lexeme)
    if symbol == "bool":
        return lexeme in ("bilkul",)          # SMILE: bilkul = true, nahi = false
    if symbol == "id":
        return 0                               # no symbol table yet -> treat variables as 0
    return lexeme                              # str / literal word -> text


def _child_env(node: dict, head_symbol: str) -> Tuple[Dict[str, _AttrRef], Dict[str, object]]:
    """Build the rule namespace for one internal node.

    head  -> bare symbol (e.g. E)        : the attributes we are about to set
    child -> subscripted per repeat       : E1, T, joro ...  (bare when unique &
                                            different from the head)
    """
    rhs = node["children"]
    counts: Dict[str, int] = {}
    for c in rhs:
        counts[c["symbol"]] = counts.get(c["symbol"], 0) + 1

    env: Dict[str, _AttrRef] = {}
    seen: Dict[str, int] = {}
    for c in rhs:
        sym = c["symbol"]
        seen[sym] = seen.get(sym, 0) + 1
        attrs = c.get("attrs", {})
        ref = _AttrRef(f"{sym}{seen[sym]}", attrs)
        env[f"{sym}{seen[sym]}"] = ref          # always: E1, E2, ...
        if counts[sym] == 1 and sym != head_symbol:
            env[sym] = ref                      # bare when unambiguous

    head_attrs: Dict[str, object] = {}
    env[head_symbol] = _AttrRef(head_symbol, head_attrs)
    return env, head_attrs


_RELOPS = {
    "zyada": lambda a, b: a > b,
    "kam": lambda a, b: a < b,
    "barabar": lambda a, b: a == b,
    "zyada ya barabar": lambda a, b: a >= b,
    "kam ya barabar": lambda a, b: a <= b,
    "na barabar": lambda a, b: a != b,
}


def annotate(tree: dict, rules_by_prod: Dict[int, dict], g: Grammar):
    """Walk the parse tree as an INTERPRETER: it executes control flow
    (if/else, while, for) and keeps a symbol table, decorating each node with
    its computed value. So only the taken branch runs and loops actually loop --
    the annotated values are the real ones. Returns (steps, errors, used_prods).

    For pure expression grammars this is just the classic bottom-up SDD walk."""
    steps: List[dict] = []
    errors: List[str] = []
    used_prods: set = set()
    symtab: Dict[str, object] = {}

    def child(node, sym):
        return next((c for c in node["children"] if c["symbol"] == sym), None)

    def apply_rule(node):
        """Default node handling: evaluate children's SDD rule, decorate."""
        head_symbol = node["symbol"]
        env, head_attrs = _child_env(node, head_symbol)
        rule = rules_by_prod.get(node["prod"])
        if rule is None:
            real = [c for c in node["children"] if c["symbol"] != EPS]
            if len(real) == 1 and "val" in real[0].get("attrs", {}):
                head_attrs["val"] = real[0]["attrs"]["val"]
            node["attrs"] = dict(head_attrs)
            node["rule"] = None
        else:
            applied = []
            for attr, expr in rule["assigns"]:
                try:
                    head_attrs[attr] = _safe_eval(expr, env)
                    applied.append(f"{head_symbol}.{attr} = {_fmt(head_attrs[attr])}")
                except SemanticError as e:
                    errors.append(f"[{production_str(g, node['prod'])}] {e}")
                    applied.append(f"{head_symbol}.{attr} = ⚠")
            node["attrs"] = dict(head_attrs)
            node["rule"] = rule["line"]
            used_prods.add(node["prod"])
            steps.append({
                "production": production_str(g, node["prod"]),
                "rule": rule["line"],
                "result": "   ".join(applied) if applied else "(no assignment)",
            })
        return head_attrs.get("val")

    def block_value(blk):
        """The value of a block = the value of its last statement (its STMTS)."""
        if blk is None:
            return 0
        for c in blk["children"]:
            if c["symbol"] == "STMTS":
                return (c.get("attrs") or {}).get("val", 0)
        return 0

    def cond_true(cond_node):
        """Evaluate a COND ( EXPR REL EXPR ) to a bool (used to pick the branch)."""
        exprs = [c for c in cond_node["children"] if c["symbol"] == "EXPR"]
        relnode = child(cond_node, "REL")
        a = ev(exprs[0]) if exprs else 0
        b = ev(exprs[1]) if len(exprs) > 1 else 0
        relt = "barabar"
        if relnode:
            ev(relnode)
            if relnode["children"]:
                relt = relnode["children"][0]["lexeme"]
        try:
            res = bool(_RELOPS.get(relt, lambda x, y: x == y)(a, b))
        except TypeError:
            res = False
        cond_node["attrs"] = {}            # no true/false badge — values flow up instead
        cond_node["rule"] = None
        return res

    def do_if(node):
        ch = node["children"]
        guards, i = [], 0          # list of (cond_node_or_None, block_node)
        while i < len(ch):
            c = ch[i]
            if c["terminal"] and c["symbol"] in ("agar", "warna_agar"):
                guards.append((ch[i + 1], ch[i + 2]))
                i += 3
            elif c["terminal"] and c["symbol"] == "warna":
                guards.append((None, ch[i + 1]))
                i += 2
            else:
                i += 1
        result = 0
        for cond, blk in guards:
            if cond is None:           # else
                ev(blk)
                result = block_value(blk)
                break
            if cond_true(cond):        # taken branch
                ev(blk)
                result = block_value(blk)
                break
        node["attrs"] = {"val": result}    # the if carries the value of the taken branch
        node["rule"] = None
        return result

    def do_while(node):
        cond = child(node, "COND")
        blk = child(node, "BLOCK")
        guard = 0
        ran = False
        while cond is not None and cond_true(cond):
            if blk is not None:
                ev(blk)
                ran = True
            guard += 1
            if guard > 100000:
                errors.append("faaaah: while loop bahut der chala (infinite loop?)")
                break
        result = block_value(blk) if ran else 0
        node["attrs"] = {"val": result}
        node["rule"] = None
        return result

    def do_for(node):
        ch = node["children"]
        for c in ch:                   # decorate the structural terminals
            if c["terminal"]:
                ev(c)
        ids = [c for c in ch if c["symbol"] == "id"]
        exprs = [c for c in ch if c["symbol"] == "EXPR"]
        cond = child(node, "COND")
        blk = child(node, "BLOCK")
        if ids and exprs:
            symtab[ids[0]["lexeme"]] = ev(exprs[0])          # init
        guard = 0
        ran = False
        while cond is not None and cond_true(cond):
            if blk is not None:
                ev(blk)
                ran = True
            if len(ids) > 1 and len(exprs) > 1:
                symtab[ids[1]["lexeme"]] = ev(exprs[1])      # update
            guard += 1
            if guard > 100000:
                errors.append("faaaah: for loop bahut der chala (infinite loop?)")
                break
        result = block_value(blk) if ran else 0
        node["attrs"] = {"val": result}
        node["rule"] = None
        return result

    def ev(node):
        if node["terminal"]:
            if node["symbol"] == EPS:
                node["attrs"] = {}
                return 0
            if node["symbol"] == "id":
                v = symtab.get(node["lexeme"], 0)
                node["attrs"] = {"val": v, "lexeme": node["lexeme"]}
                return v
            val = _coerce_terminal(node["symbol"], node["lexeme"])
            node["attrs"] = {"val": val, "lexeme": node["lexeme"]}
            return val

        sym = node["symbol"]
        if sym == "IF":
            return do_if(node)
        if sym == "WHILE":
            return do_while(node)
        if sym == "FOR":
            return do_for(node)
        if sym == "COND":
            return 1 if cond_true(node) else 0

        for c in node["children"]:     # default: evaluate children in order
            ev(c)
        val = apply_rule(node)
        _record_assignment(node, symtab)
        return val

    ev(tree)
    return steps, errors, used_prods


def _fmt(v) -> str:
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


# ─────────────────────────── Entry point ───────────────────────────────

def analyze_semantics(code: str,
                      grammar_text: str = DEFAULT_GRAMMAR_TEXT,
                      semantic_text: str = DEFAULT_SEMANTIC_TEXT) -> dict:
    """Full semantic phase: validate grammar + SDD, parse, build the annotated
    parse tree by evaluating synthesized attributes bottom-up."""
    g, gerrors, gwarnings, ginfo = parse_grammar(grammar_text or DEFAULT_GRAMMAR_TEXT)

    base = {
        "grammar_errors": gerrors,
        "grammar_warnings": gwarnings,
        "grammar_info": ginfo,
    }

    if g is None:
        base.update({
            "accepted": False,
            "error": "faaaah: grammar theek karo pehle -- neeche errors dekho",
            "grammar": [], "sdd": [], "trace": [], "tree": None,
            "steps": [], "semantic_errors": [],
        })
        return base

    base["grammar"] = grammar_listing(g)

    # Rules & regulations of the grammar (the SDD).
    rules_by_prod, rule_errors = parse_semantic_rules(semantic_text or "", g)
    base["sdd"] = [
        {
            "index": i,
            "production": production_str(g, i),
            "rule": rules_by_prod.get(i, {}).get("line", "").split("{", 1)[-1].rsplit("}", 1)[0].strip()
                    if i in rules_by_prod else ("" if i == 0 else "(koi rule nahi)"),
        }
        for i in range(len(g.productions))
    ]
    base["rule_errors"] = rule_errors

    # Map the input to terminals.
    terminals, display, terr = tokens_to_terminals(code, g)
    if terr is not None:
        base.update({"accepted": False, "error": terr,
                     "trace": [], "tree": None, "steps": [], "semantic_errors": []})
        return base

    base["input_tokens"] = [
        {"value": d, "terminal": t} for d, t in zip(display, terminals)
    ] + [{"value": "$", "terminal": "$"}]

    # Build SLR tables, parse to a tree.
    tables = build_slr(g)
    if tables["conflicts"]:
        base["parser_conflicts"] = tables["conflicts"]

    tree, trace, accepted, perr = build_annotated_tree(
        g, tables["action"], tables["goto"], terminals, display
    )
    base["trace"] = trace
    base["accepted"] = accepted

    if not accepted:
        base.update({"error": perr, "tree": None, "steps": [], "semantic_errors": []})
        return base

    # Annotate: evaluate synthesized attributes bottom-up.
    steps, sem_errors, used_prods = annotate(tree, rules_by_prod, g)
    base["tree"] = tree
    base["steps"] = steps
    base["semantic_errors"] = sem_errors
    base["error"] = None

    # The SDD subset actually used by THIS program (rules that fired).
    base["used_sdd"] = [entry for entry in base["sdd"] if entry["index"] in used_prods]

    # The value of the whole program = start symbol's attributes.
    base["result"] = {k: _fmt(v) for k, v in tree.get("attrs", {}).items()}
    return base


# ─── Quick CLI test ───
if __name__ == "__main__":
    out = analyze_semantics("2 joro 3 guna 4")
    print("accepted:", out["accepted"], "result:", out.get("result"))
    for s in out["steps"]:
        print(f"  {s['production']:20s} {s['result']}")
    for e in out["semantic_errors"]:
        print(e)
