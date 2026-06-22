"""
SMILE Code Optimizer -- the optimization phase.

Takes the three-address code from the previous phase and applies the classic
**local (machine-independent) optimizations** (ref: GeeksforGeeks "Code
Optimization in Compiler Design"):

  * Constant folding          -- t = 3 * 4        => t = 12
  * Algebraic simplification  -- t = x * 1        => t = x   ;  x + 0 => x ; x*0 => 0
  * Constant / copy propagation -- x = 5 ; y = x + 1  =>  y = 5 + 1
  * Common subexpression elimination -- t2 = a+b (already in t1) => t2 = t1
  * Dead code elimination     -- drop a temporary that is never used

The passes run to a **fixpoint** (repeat until nothing changes) so optimizations
cascade (fold -> propagate -> fold again -> eliminate). Propagation / CSE are
**block-local**: their state resets at every label and jump, so control flow
stays correct. If nothing can be improved, the code is returned unchanged.
"""

from threeaddr import build_instructions, _fmt_line, _quads, _triples


SYM_OP = {
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "*": lambda a, b: a * b,
    "/": lambda a, b: a / b,
    "%": lambda a, b: a % b,
}
COMMUTATIVE = {"+", "*"}
BOUNDARY = {"label", "goto", "if", "return"}     # block boundaries for propagation/CSE


def _is_num(s):
    if not isinstance(s, str):
        return False
    try:
        float(s)
        return True
    except ValueError:
        return False


def _num(s):
    f = float(s)
    return int(f) if f.is_integer() else f


def _numstr(v):
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v)


def _copy(result, src):
    return {"op": "=", "arg1": src, "arg2": None, "result": result, "relop": None}


def _line(ins):
    return _fmt_line(ins).strip()


# ─────────────────── Pass 1: constant folding + algebra ───────────────────

def _algebraic(op, a1, a2, r):
    """x+0, 0+x, x-0, x*1, 1*x, x*0, 0*x, x/1 -> simpler form, else None."""
    if op == "+":
        if a2 == "0":
            return _copy(r, a1)
        if a1 == "0":
            return _copy(r, a2)
    elif op == "-":
        if a2 == "0":
            return _copy(r, a1)
    elif op == "*":
        if a1 == "1":
            return _copy(r, a2)
        if a2 == "1":
            return _copy(r, a1)
        if a1 == "0" or a2 == "0":
            return _copy(r, "0")
    elif op == "/":
        if a2 == "1":
            return _copy(r, a1)
    return None


def fold_and_simplify(code):
    out, changed, log = [], False, []
    for ins in code:
        op, a1, a2, r = ins["op"], ins["arg1"], ins["arg2"], ins["result"]
        new = ins
        if op in SYM_OP:
            if _is_num(a1) and _is_num(a2):
                if op in ("/", "%") and _num(a2) == 0:
                    pass                                   # don't fold division by zero
                else:
                    new = _copy(r, _numstr(SYM_OP[op](_num(a1), _num(a2))))
                    log.append({"type": "Constant folding", "before": _line(ins), "after": _line(new)})
                    changed = True
            else:
                simp = _algebraic(op, a1, a2, r)
                if simp is not None:
                    new = simp
                    log.append({"type": "Algebraic simplification", "before": _line(ins), "after": _line(new)})
                    changed = True
        elif op == "uminus" and _is_num(a1):
            new = _copy(r, _numstr(-_num(a1)))
            log.append({"type": "Constant folding", "before": _line(ins), "after": _line(new)})
            changed = True
        out.append(new)
    return out, changed, log


# ─────────────── Pass 2: constant / copy propagation (block-local) ───────────────

def propagate(code):
    out, changed, log = [], False, []
    env = {}                                               # var -> known value (const or var)

    def sub(x):
        return env.get(x, x) if isinstance(x, str) else x

    for ins in code:
        op = ins["op"]

        if op == "label":
            env = {}
            out.append(ins)
            continue
        if op == "goto":
            out.append(ins)
            env = {}
            continue
        if op in ("if", "return", "print"):
            ni = dict(ins)
            ni["arg1"] = sub(ins["arg1"])
            if op == "if":
                ni["arg2"] = sub(ins["arg2"])
            if ni["arg1"] != ins["arg1"] or ni.get("arg2") != ins.get("arg2"):
                changed = True
                log.append({"type": "Copy/constant propagation", "before": _line(ins), "after": _line(ni)})
            out.append(ni)
            if op in ("if", "return"):
                env = {}                                   # block terminator
            continue

        # defining instruction: =, binary, uminus
        r = ins["result"]
        ni = dict(ins)
        ni["arg1"] = sub(ins["arg1"])
        ni["arg2"] = sub(ins["arg2"]) if ins["arg2"] is not None else None
        if ni["arg1"] != ins["arg1"] or ni["arg2"] != ins["arg2"]:
            changed = True
            log.append({"type": "Copy/constant propagation", "before": _line(ins), "after": _line(ni)})

        env = {k: v for k, v in env.items() if v != r and k != r}   # invalidate
        if ni["op"] == "=":
            env[r] = ni["arg1"]                             # a copy makes result a known value
        out.append(ni)
    return out, changed, log


# ─────────────── Pass 3: common subexpression elimination (block-local) ───────────────

def cse(code):
    out, changed, log = [], False, []
    avail = {}                                             # (op, a1, a2) -> result var

    def invalidate(v):
        for k in list(avail):
            o, a, b = k
            if a == v or b == v or avail[k] == v:
                del avail[k]

    for ins in code:
        op = ins["op"]
        if op in BOUNDARY:
            avail = {}
            out.append(ins)
            continue
        if op == "print":
            out.append(ins)
            continue

        r = ins["result"]
        if op in SYM_OP:
            a1, a2 = ins["arg1"], ins["arg2"]
            keys = [(op, a1, a2)] + ([(op, a2, a1)] if op in COMMUTATIVE else [])
            found = next((avail[k] for k in keys if k in avail), None)
            invalidate(r)
            if found is not None:
                ni = _copy(r, found)
                log.append({"type": "Common subexpression elimination", "before": _line(ins), "after": _line(ni)})
                changed = True
                out.append(ni)
            else:
                avail[(op, a1, a2)] = r
                out.append(ins)
        else:                                              # copy / uminus
            invalidate(r)
            out.append(ins)
    return out, changed, log


# ─────────────── Pass 4: dead code elimination (unused temporaries) ───────────────

def dead_code(code):
    used = set()
    for ins in code:
        op = ins["op"]
        if op == "if":
            used.add(ins["arg1"])
            used.add(ins["arg2"])
        elif op in ("print", "return", "uminus", "="):
            used.add(ins["arg1"])
        elif op in SYM_OP:
            used.add(ins["arg1"])
            used.add(ins["arg2"])

    out, changed, log = [], False, []
    defining = {"=", "uminus", *SYM_OP}
    for ins in code:
        r = ins["result"]
        if (ins["op"] in defining and isinstance(r, str)
                and r.startswith("t") and r not in used):
            log.append({"type": "Dead code elimination", "before": _line(ins), "after": "(removed)"})
            changed = True
            continue
        out.append(ins)
    return out, changed, log


# ─────────────────────────── driver ───────────────────────────

def optimize_instructions(code):
    cur = [dict(i) for i in code]
    log = []
    for _ in range(30):                                    # fixpoint (guarded)
        changed = False
        for pass_fn in (fold_and_simplify, propagate, cse, dead_code):
            cur, c, l = pass_fn(cur)
            changed = changed or c
            log.extend(l)
        if not changed:
            break
    return cur, log


def optimize(code: str) -> dict:
    """Full optimization phase: generate TAC, optimize it, report what changed."""
    instrs, error = build_instructions(code)
    if error is not None:
        return {"ok": False, "error": error,
                "original_tac": [], "optimized_tac": [],
                "optimizations": [], "changed": False,
                "quadruples": [], "triples": []}

    original = [dict(i) for i in instrs]
    optimized, log = optimize_instructions(instrs)

    return {
        "ok": True,
        "error": None,
        "original_tac": [_fmt_line(i) for i in original],
        "optimized_tac": [_fmt_line(i) for i in optimized],
        "original_count": len(original),
        "optimized_count": len(optimized),
        "optimizations": log,
        "changed": len(log) > 0,
        "quadruples": _quads(optimized),
        "triples": _triples(optimized),
    }


# ─── CLI test ───
if __name__ == "__main__":
    tests = [
        "shuru karo adad x rakho 2 joro 3 guna 4 bas khatam",
        "shuru karo adad x rakho a joro b bas adad y rakho a joro b bas khatam",
        "shuru karo adad x rakho a guna 1 bas khatam",
        "shuru karo batao a bas khatam",
    ]
    for code in tests:
        print("=" * 56)
        out = optimize(code)
        print("BEFORE:", out["original_tac"])
        print("AFTER :", out["optimized_tac"])
        for o in out["optimizations"]:
            print(f"   [{o['type']}] {o['before']}  ->  {o['after']}")
