"""
SMILE Three-Address Code (TAC) -- the intermediate-code generation phase.

After semantic analysis, the compiler lowers the program to **three-address
code**: a linear sequence of simple instructions, each with at most one
operator and (at most) three addresses. SMILE supports these TAC forms:

    x = y op z            binary operation      (joro + , ghata - , guna * , ...)
    x = op y              unary operation       (ulta -> unary minus)
    x = y                 copy / assignment     (rakho)
    if x relop y goto L   conditional goto      (agar / jab tak conditions)
    goto L                unconditional goto
    A[i] = x  /  y = A[i] array indexing         (form supported; SMILE has no arrays yet)
    p = addr x / y = *p   pointer operations     (form supported; SMILE has no pointers yet)

We generate code by a small **recursive-descent + syntax-directed translation**
pass over the lexer's tokens, creating temporaries (t1, t2, ...) and labels
(L1, L2, ...). The same instruction list is then shown three ways:
the linear TAC, a **Quadruple** table (op, arg1, arg2, result) and a
**Triple** table (op, arg1, arg2) where temporaries become (index) references.
"""

from lexer import tokenize

# SMILE operator words -> TAC symbols
BINOP = {"joro": "+", "ghata": "-", "guna": "*", "taqseem": "/", "bacha": "%"}
RELOP = {
    "zyada": ">", "kam": "<", "barabar": "==",
    "zyada ya barabar": ">=", "kam ya barabar": "<=", "na barabar": "!=",
}
TYPES = {"adad", "desi", "baat", "khaali"}

# Reference table shown in the UI (the TAC statement forms).
TAC_TYPES = [
    {"form": "x = y op z", "meaning": "Binary operation", "smile": "yes"},
    {"form": "x = op y", "meaning": "Unary operation", "smile": "yes (ulta)"},
    {"form": "x = y", "meaning": "Assignment / copy", "smile": "yes (rakho)"},
    {"form": "if x relop y goto L", "meaning": "Conditional goto", "smile": "yes (agar / jab tak)"},
    {"form": "goto L", "meaning": "Unconditional goto", "smile": "yes"},
    {"form": "A[i] = x   /   y = A[i]", "meaning": "Array indexing", "smile": "form only"},
    {"form": "p = addr x  /  y = *p  /  *p = z", "meaning": "Pointer operations", "smile": "form only"},
]


class TACError(Exception):
    """Raised on a parse/codegen problem (faaaah: ... message)."""


class _Gen:
    """Recursive-descent parser over lexer tokens that emits TAC."""

    def __init__(self, tokens):
        self.toks = tokens
        self.i = 0
        self.code = []
        self.tmp = 0
        self.lbl = 0

    # ── token cursor ──
    def _peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else None

    def _val(self):
        t = self._peek()
        return t["value"] if t else None

    def _type(self):
        t = self._peek()
        return t["type"] if t else None

    def _at_end(self):
        return self.i >= len(self.toks)

    def _advance(self):
        t = self.toks[self.i]
        self.i += 1
        return t

    def _expect(self, value):
        if self._val() != value:
            raise TACError(f"faaaah: '{value}' chahiye tha par '{self._val() or 'END'}' mila")
        return self._advance()

    # ── fresh names ──
    def _temp(self):
        self.tmp += 1
        return f"t{self.tmp}"

    def _label(self):
        self.lbl += 1
        return f"L{self.lbl}"

    def _emit(self, op, arg1=None, arg2=None, result=None, relop=None):
        self.code.append({"op": op, "arg1": arg1, "arg2": arg2,
                          "result": result, "relop": relop})

    # ── grammar ──
    def program(self):
        self._expect("shuru karo")
        while not self._at_end() and self._val() != "khatam":
            self.statement()
        self._expect("khatam")
        return self.code

    def block(self):
        self._expect("shuru")
        while not self._at_end() and self._val() != "banda":
            self.statement()
        self._expect("banda")

    def statement(self):
        v, t = self._val(), self._type()
        if v in TYPES:
            self.declaration()
        elif t == "IDENTIFIER":
            self.assignment()
        elif v == "batao":
            self.print_stmt()
        elif v == "agar":
            self.if_stmt()
        elif v == "jab tak":
            self.while_stmt()
        elif v == "baar baar":
            self.for_stmt()
        elif v == "wapas de":
            self._advance()
            place = self.expr()
            self._expect("bas")
            self._emit("return", place)
        else:
            raise TACError(f"faaaah: '{v or 'END'}' se koi statement start nahi hoti")

    def declaration(self):
        self._advance()                       # type keyword
        if self._type() != "IDENTIFIER":
            raise TACError("faaaah: declaration mein variable ka naam chahiye")
        name = self._advance()["value"]
        self._expect("rakho")
        place = self.expr()
        self._expect("bas")
        self._emit("=", place, None, name)

    def assignment(self):
        name = self._advance()["value"]
        self._expect("rakho")
        place = self.expr()
        self._expect("bas")
        self._emit("=", place, None, name)

    def print_stmt(self):
        self._advance()
        place = self.expr()
        self._expect("bas")
        self._emit("print", place)

    def condition(self):
        x = self.expr()
        v = self._val()
        if v not in RELOP:
            raise TACError(f"faaaah: condition mein relational operator chahiye, '{v}' mila")
        relop = RELOP[v]
        self._advance()
        y = self.expr()
        return x, relop, y

    def if_stmt(self):
        self._advance()                       # agar
        x, relop, y = self.condition()
        l_true, l_false = self._label(), self._label()
        self._emit("if", x, y, l_true, relop=relop)
        self._emit("goto", None, None, l_false)
        self._emit("label", None, None, l_true)
        self.block()
        if self._val() == "warna":
            self._advance()
            l_end = self._label()
            self._emit("goto", None, None, l_end)
            self._emit("label", None, None, l_false)
            self.block()
            self._emit("label", None, None, l_end)
        else:
            self._emit("label", None, None, l_false)

    def while_stmt(self):
        self._advance()                       # jab tak
        l_start = self._label()
        self._emit("label", None, None, l_start)
        x, relop, y = self.condition()
        l_body, l_end = self._label(), self._label()
        self._emit("if", x, y, l_body, relop=relop)
        self._emit("goto", None, None, l_end)
        self._emit("label", None, None, l_body)
        self.block()
        self._emit("goto", None, None, l_start)
        self._emit("label", None, None, l_end)

    def for_stmt(self):
        # baar_baar id rakho EXPR bas COND bas id rakho EXPR BLOCK
        self._advance()                       # baar baar
        # init:  id rakho EXPR bas
        if self._type() != "IDENTIFIER":
            raise TACError("faaaah: for loop mein init variable chahiye")
        init_var = self._advance()["value"]
        self._expect("rakho")
        self._emit("=", self.expr(), None, init_var)
        self._expect("bas")
        # condition bas
        l_start = self._label()
        self._emit("label", None, None, l_start)
        x, relop, y = self.condition()
        l_body, l_end = self._label(), self._label()
        self._emit("if", x, y, l_body, relop=relop)
        self._emit("goto", None, None, l_end)
        self._expect("bas")
        # update:  id rakho EXPR  -> buffered, emitted AFTER the body
        if self._type() != "IDENTIFIER":
            raise TACError("faaaah: for loop mein update variable chahiye")
        upd_var = self._advance()["value"]
        self._expect("rakho")
        saved = self.code
        self.code = []
        self._emit("=", self.expr(), None, upd_var)
        update_code = self.code
        self.code = saved
        # body, then the update, then loop back
        self._emit("label", None, None, l_body)
        self.block()
        self.code.extend(update_code)
        self._emit("goto", None, None, l_start)
        self._emit("label", None, None, l_end)

    # ── expressions (precedence: + - below * / %) ──
    def expr(self):
        place = self.term()
        while self._val() in ("joro", "ghata"):
            op = BINOP[self._advance()["value"]]
            right = self.term()
            t = self._temp()
            self._emit(op, place, right, t)
            place = t
        return place

    def term(self):
        place = self.factor()
        while self._val() in ("guna", "taqseem", "bacha"):
            op = BINOP[self._advance()["value"]]
            right = self.factor()
            t = self._temp()
            self._emit(op, place, right, t)
            place = t
        return place

    def factor(self):
        v, t = self._val(), self._type()
        if v == "ulta":                       # unary
            self._advance()
            operand = self.factor()
            tmp = self._temp()
            self._emit("uminus", operand, None, tmp)
            return tmp
        if t in ("NUMBER", "IDENTIFIER", "STRING", "BOOLEAN"):
            return self._advance()["value"]
        raise TACError(f"faaaah: expression mein '{v or 'END'}' nahi aana chahiye")


# ─────────────────────── renderers ───────────────────────

def _fmt_line(ins):
    op, a1, a2, r, rel = ins["op"], ins["arg1"], ins["arg2"], ins["result"], ins["relop"]
    if op == "label":
        return f"{r}:"
    if op == "goto":
        return f"    goto {r}"
    if op == "if":
        return f"    if {a1} {rel} {a2} goto {r}"
    if op == "=":
        return f"    {r} = {a1}"
    if op == "uminus":
        return f"    {r} = - {a1}"
    if op == "print":
        return f"    print {a1}"
    if op == "return":
        return f"    return {a1}"
    return f"    {r} = {a1} {op} {a2}"        # binary


def _quads(code):
    rows = []
    for idx, ins in enumerate(code):
        op = ins["op"]
        if op == "if":
            disp_op = f"if {ins['relop']}"
        else:
            disp_op = op
        rows.append({
            "index": idx,
            "op": disp_op,
            "arg1": ins["arg1"] if ins["arg1"] is not None else "",
            "arg2": ins["arg2"] if ins["arg2"] is not None else "",
            "result": ins["result"] if ins["result"] is not None else "",
        })
    return rows


def _triples(code):
    # temp -> index of the triple that produces it
    tmpdef = {}
    for idx, ins in enumerate(code):
        r = ins["result"]
        if r and isinstance(r, str) and r.startswith("t") and ins["op"] in ("uminus", *BINOP.values()):
            tmpdef[r] = idx

    def ref(x):
        if isinstance(x, str) and x in tmpdef:
            return f"({tmpdef[x]})"
        return "" if x is None else x

    rows = []
    for idx, ins in enumerate(code):
        op = ins["op"]
        if op == "label":
            rows.append({"index": idx, "op": "label", "arg1": ins["result"], "arg2": ""})
        elif op == "goto":
            rows.append({"index": idx, "op": "goto", "arg1": ins["result"], "arg2": ""})
        elif op == "if":
            rows.append({"index": idx, "op": "if",
                         "arg1": f"{ref(ins['arg1'])} {ins['relop']} {ref(ins['arg2'])}",
                         "arg2": ins["result"]})           # arg2 = target label
        elif op == "=":
            rows.append({"index": idx, "op": "=", "arg1": ins["result"], "arg2": ref(ins["arg1"])})
        elif op == "uminus":
            rows.append({"index": idx, "op": "uminus", "arg1": ref(ins["arg1"]), "arg2": ""})
        elif op == "print":
            rows.append({"index": idx, "op": "print", "arg1": ref(ins["arg1"]), "arg2": ""})
        elif op == "return":
            rows.append({"index": idx, "op": "return", "arg1": ref(ins["arg1"]), "arg2": ""})
        else:                                              # binary
            rows.append({"index": idx, "op": op,
                         "arg1": ref(ins["arg1"]), "arg2": ref(ins["arg2"])})
    return rows


def build_instructions(code: str):
    """Parse SMILE source to the raw TAC instruction list. Returns
    (instructions, error_or_None). Used by both generate_tac and the optimizer."""
    lex = tokenize(code)
    if lex["errors"]:
        return None, lex["errors"][0]["message"]
    gen = _Gen(lex["tokens"])
    try:
        return gen.program(), None
    except TACError as e:
        return None, str(e)


def generate_tac(code: str) -> dict:
    """Generate three-address code from SMILE source. Returns the linear TAC,
    plus quadruple and triple tables."""
    instrs, error = build_instructions(code)
    if error is not None:
        return {"ok": False, "error": error,
                "tac": [], "quadruples": [], "triples": [], "types": TAC_TYPES}
    return {
        "ok": True,
        "error": None,
        "tac": [_fmt_line(i) for i in instrs],
        "quadruples": _quads(instrs),
        "triples": _triples(instrs),
        "temps": len({i["result"] for i in instrs
                      if i["result"] and str(i["result"]).startswith("t")}),
        "labels": sum(1 for i in instrs if i["op"] == "label"),
        "types": TAC_TYPES,
    }


# ─── CLI test ───
if __name__ == "__main__":
    samples = [
        "shuru karo adad x rakho 2 joro 3 guna 4 bas khatam",
        "shuru karo\nagar a kam b shuru\nbatao a bas\nbanda warna shuru\nbatao b bas\nbanda\nkhatam",
        "shuru karo\nadad i rakho 0 bas\njab tak i kam 5 shuru\nbatao i bas\ni rakho i joro 1 bas\nbanda\nkhatam",
    ]
    for s in samples:
        print("=" * 50)
        out = generate_tac(s)
        if not out["ok"]:
            print("ERROR:", out["error"])
            continue
        for line in out["tac"]:
            print(line)
