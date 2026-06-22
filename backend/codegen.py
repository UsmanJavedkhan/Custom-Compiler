"""
SMILE Code Generator -- convert a SMILE program into 8051 assembly for Keil.

Input is SMILE source (the same program used by every other phase). We build its
three-address code (via the 3-address-code phase) and translate each TAC
statement into 8051 / MCS-51 assembly in **Keil A51 syntax** (EQU / ORG / MOV A
/ ADD A / MUL AB / DIV AB / CJNE / SJMP / END), ready to run in the Keil uVision
8051 simulator.

8051 model (8-bit!): the accumulator A and register B hold one byte (0-255).
Every SMILE variable / temporary gets a byte of internal RAM, assigned with EQU
starting at 30H. Each TAC instruction loads operands into A (and B for MUL/DIV),
computes, and stores the result to its RAM byte. `print x` leaves the value in A
-- the bare simulator has no console, so you watch A / B / RAM in the debugger.
"""

from threeaddr import build_instructions, _fmt_line
from optimizer import optimize_instructions

OP_NAMES = {"+", "-", "*", "/", "%"}


def _is_num(s):
    if not isinstance(s, str):
        return False
    try:
        int(s)
        return True
    except ValueError:
        return False


def _opnd(x):
    """8051 operand: '#imm' for a constant, or the variable's RAM symbol."""
    return f"#{int(x)}" if _is_num(x) else f"var_{x}"


def _collect_names(instrs):
    names, seen = [], set()

    def add(x):
        if isinstance(x, str) and not _is_num(x) and x not in seen:
            seen.add(x)
            names.append(x)

    for ins in instrs:
        op = ins["op"]
        if op in ("label", "goto"):
            continue
        if op == "if":
            add(ins["arg1"])
            add(ins["arg2"])
            continue
        if op in ("print", "return"):
            add(ins["arg1"])
            continue
        add(ins["arg1"])
        add(ins["arg2"])
        add(ins["result"])
    return names


def _body_for(ins, idx):
    """Translate one TAC instruction into 8051 (A51) assembly lines."""
    op, a1, a2, r, rel = ins["op"], ins["arg1"], ins["arg2"], ins["result"], ins["relop"]

    if op == "label":
        return [f"{r}:"]
    if op == "goto":
        return [f"        LJMP    {r}"]
    if op == "if":
        x, y, L = _opnd(a1), _opnd(a2), r
        if rel == "==":
            return [f"        MOV     A, {x}", f"        CJNE    A, {y}, SKIP_{idx}",
                    f"        LJMP    {L}", f"SKIP_{idx}:"]
        if rel == "!=":
            return [f"        MOV     A, {x}", f"        CJNE    A, {y}, {L}"]
        if rel == "<":
            return [f"        MOV     A, {x}", "        CLR     C",
                    f"        SUBB    A, {y}", f"        JC      {L}"]
        if rel == ">=":
            return [f"        MOV     A, {x}", "        CLR     C",
                    f"        SUBB    A, {y}", f"        JNC     {L}"]
        if rel == ">":
            return [f"        MOV     A, {y}", "        CLR     C",
                    f"        SUBB    A, {x}", f"        JC      {L}"]
        if rel == "<=":
            return [f"        MOV     A, {y}", "        CLR     C",
                    f"        SUBB    A, {x}", f"        JNC     {L}"]
    if op == "print":
        return [f"        MOV     A, {_opnd(a1)}",
                "        ; print -> value is in A (watch A / RAM in debugger)"]
    if op == "return":
        return [f"        MOV     A, {_opnd(a1)}", "        ; return value in A"]
    if op == "=":
        return [f"        MOV     A, {_opnd(a1)}", f"        MOV     var_{r}, A"]
    if op == "uminus":
        return [f"        MOV     A, {_opnd(a1)}", "        CPL     A", "        INC     A",
                f"        MOV     var_{r}, A"]
    # binary
    a, b = _opnd(a1), _opnd(a2)
    if op == "+":
        return [f"        MOV     A, {a}", f"        ADD     A, {b}", f"        MOV     var_{r}, A"]
    if op == "-":
        return [f"        MOV     A, {a}", "        CLR     C", f"        SUBB    A, {b}",
                f"        MOV     var_{r}, A"]
    if op == "*":
        return [f"        MOV     A, {a}", f"        MOV     B, {b}", "        MUL     AB",
                f"        MOV     var_{r}, A    ; low byte (8-bit)"]
    if op == "/":
        return [f"        MOV     A, {a}", f"        MOV     B, {b}", "        DIV     AB",
                f"        MOV     var_{r}, A    ; quotient"]
    if op == "%":
        return [f"        MOV     A, {a}", f"        MOV     B, {b}", "        DIV     AB",
                f"        MOV     var_{r}, B    ; remainder"]
    return [f"        ; (unsupported op {op})"]


HEADER = """
;==================================================================
;  SMILE -> 8051 (MCS-51) assembly   --  Keil uVision, A51 syntax
;
;  HOW TO RUN IN KEIL uVISION:
;   1. Project > New uVision Project; choose an 8051 device
;      (e.g. Atmel > AT89C51, or Generic / NXP 8051).
;   2. Add this file (.a51 / .asm) to 'Source Group 1'.
;   3. Build (F7), then Start/Stop Debug Session (Ctrl+F5) -> simulator.
;   4. Run / single-step (F11).  8-bit values (0-255).  No console --
;      watch A, B, R0-R7 and Data RAM (var_* at 30H..) in the debugger.
;==================================================================
""".strip("\n").split("\n")


def generate_asm(code: str) -> dict:
    """Convert a SMILE program into a Keil-ready 8051 (A51) program
    (SMILE -> three-address code -> OPTIMIZED TAC -> 8051 assembly)."""
    instrs, error = build_instructions(code)
    if error is not None:
        return {"ok": False, "error": error, "tac": [], "assembly": [], "mapping": []}

    # use the optimized three-address code (same passes as the optimizer phase)
    instrs, _ = optimize_instructions(instrs)

    names = _collect_names(instrs)

    lines = list(HEADER)
    if names:
        lines += ["", "; ---- variables in internal RAM (one byte each) ----"]
        for i, n in enumerate(names):
            addr = 0x30 + i
            lines.append(f"{('var_' + n):<10}EQU     {addr:02X}H")

    lines += ["", "        ORG     0000H"]

    tac, mapping = [], []
    for idx, ins in enumerate(instrs):
        body = _body_for(ins, idx)
        tac.append(_fmt_line(ins))
        mapping.append({"tac": _fmt_line(ins).strip(), "asm": body})
        lines += body

    lines += ["", "HALT:   SJMP    HALT        ; stop (loop forever)", "        END"]

    return {"ok": True, "error": None, "tac": tac, "assembly": lines, "mapping": mapping}


# ─── CLI test ───
if __name__ == "__main__":
    out = generate_asm("shuru karo adad x rakho 2 joro 3 guna 4 bas batao x bas khatam")
    print("\n".join(out["assembly"]))
