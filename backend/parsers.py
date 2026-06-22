"""
SMILE Parsers -- Syntax analysis for the SMILE language.

The grammar is **user-supplied**: the student types a context-free grammar in
SMILE-flavoured BNF, e.g.

    E -> E joro T | E ghata T | T
    T -> T guna F | T taqseem F | F
    F -> id | num

Rules:
  * One production per line, `->` separates the head, `|` separates alternatives.
  * The head (left-hand side) is a single nonterminal.
  * Any symbol that appears as a head is a NONTERMINAL; every other symbol must
    be a valid SMILE terminal (see TERMINAL VOCABULARY below) -- otherwise the
    grammar is rejected.
  * The head of the FIRST production is the start symbol.
  * Epsilon (empty) productions: write `ε`, `eps`, `epsilon` or `''`.

The grammar is validated first (`parse_grammar`). If it is well-formed we build
the parsers over it; otherwise we report the errors.

Three parsers (all bottom-up):
  * LR(0)               -- LR(0) automaton; reductions on ALL terminals (no
                          lookahead). Weakest -- exposes shift/reduce and
                          reduce/reduce conflicts that SLR(1) later resolves.
  * SLR(1)              -- same LR(0) automaton + FOLLOW sets gate reductions.
  * Operator Precedence -- leading/trailing -> precedence relation table.

INPUT  to a parser : SMILE source, tokenised by the lexer and mapped to the
                     grammar's terminals (id, num, joro, agar, ...).
OUTPUT of a parser : ACCEPT / REJECT  +  a step-by-step parse trace plus the
                     tables that were built from the grammar.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from lexer import TOKEN_SPEC, tokenize

END = "$"
EPS = "ε"
EPSILON_TOKENS = {"ε", "eps", "epsilon", "''", '""', "lambda"}


# ───────────────────── SMILE terminal vocabulary ───────────────────
# The grammar's terminals must be things the lexer can actually produce, so the
# vocabulary is derived straight from the lexer's TOKEN_SPEC. Literal-word
# categories (keywords / operators / delimiters) become terminals named after
# the word itself (spaces -> underscores, e.g. "shuru karo" -> "shuru_karo").
# The open-ended literal categories collapse to: id, num, str, bool.

def _derive_literal_terminals() -> Dict[str, str]:
    """symbol -> the normalised lexer value it matches (for the token mapping)."""
    literal_categories = {"KEYWORD", "OPERATOR", "DELIMITER"}
    vocab: Dict[str, str] = {}
    for name, pattern in TOKEN_SPEC:
        if name not in literal_categories:
            continue
        word = pattern.replace(r"\b", "").replace(r"\s+", " ").strip()
        symbol = word.replace(" ", "_")
        vocab[symbol] = word
    return vocab


LITERAL_TERMINALS = _derive_literal_terminals()          # e.g. {"joro": "joro", ...}
CATEGORY_TERMINALS = {"id", "num", "str", "bool"}
VALID_TERMINALS: Set[str] = set(LITERAL_TERMINALS) | CATEGORY_TERMINALS


def _map_token(tok: dict) -> str:
    """Map one lexer token to its grammar terminal symbol."""
    ttype, value = tok["type"], tok["value"]
    if ttype == "IDENTIFIER":
        return "id"
    if ttype == "NUMBER":
        return "num"
    if ttype == "STRING":
        return "str"
    if ttype == "BOOLEAN":
        return "bool"
    # KEYWORD / OPERATOR / DELIMITER -> the literal word (spaces -> underscores)
    return value.replace(" ", "_")


DEFAULT_GRAMMAR_TEXT = (
    "E -> E joro T | E ghata T | T\n"
    "T -> T guna F | T taqseem F | F\n"
    "F -> id | num"
)


# ─────────────────────── The SMILE language grammar ────────────────────
# The fixed, generic grammar for *whole SMILE programs* — declarations,
# assignment, if / else-if / else, while (jab tak), for (baar baar),
# print, return, break/continue, functions calls, and expressions.
#
# It is written in **LL(1) form** (left recursion eliminated + left-factored)
# so the top-down LL(1) parser can drive it; the same grammar is also accepted
# by the bottom-up SLR(1) parser. Blocks are braced with `shuru ... banda`
# (SMILE has no parentheses), so the dangling-else is resolved without
# ambiguity. This lives in code — the parser uses it directly (no runtime
# grammar input). If you edit it, keep SMILE_GRAMMAR in App.jsx in sync.
SMILE_GRAMMAR = (
    "PROG  -> shuru_karo STMTS khatam\n"
    "STMTS -> STMT SREST\n"
    "SREST -> STMT SREST | ε\n"
    "STMT  -> DECL | ASG | IF | WHILE | FOR | PRINT | RET | rok bas | agla bas\n"
    "DECL  -> TYPE id rakho EXPR bas\n"
    "ASG   -> id rakho EXPR bas\n"
    "PRINT -> batao EXPR bas\n"
    "RET   -> wapas_de EXPR bas\n"
    "TYPE  -> adad | desi | baat | khaali\n"
    "BLOCK -> shuru STMTS banda\n"
    "IF    -> agar COND BLOCK ELSE\n"
    "ELSE  -> warna BLOCK | warna_agar COND BLOCK ELSE | ε\n"
    "WHILE -> jab_tak COND BLOCK\n"
    "FOR   -> baar_baar id rakho EXPR bas COND bas id rakho EXPR BLOCK\n"
    "COND  -> EXPR REL EXPR\n"
    "REL   -> zyada | kam | barabar | zyada_ya_barabar | kam_ya_barabar | na_barabar\n"
    "EXPR  -> T EREST\n"
    "EREST -> joro T EREST | ghata T EREST | ε\n"
    "T     -> F TREST\n"
    "TREST -> guna F TREST | taqseem F TREST | bacha F TREST | ε\n"
    "F     -> id | num | str"
)


# ─────────────────────────── Grammar model ─────────────────────────

@dataclass
class Grammar:
    productions: List[Tuple[str, List[str]]]   # index 0 = augmented start S' -> start
    start: str                                 # augmented start symbol (e.g. E')
    real_start: str                            # the user's start symbol (e.g. E)
    nonterminals: Set[str]
    terminals: Set[str]
    display_nonterminals: List[str] = field(default_factory=list)  # real NTs, in order
    lexer_mode: bool = True       # True -> parse input via SMILE lexer;
                                  # False -> input is a raw space-separated terminal stream


def production_str(g: Grammar, i: int) -> str:
    lhs, rhs = g.productions[i]
    body = " ".join(rhs) if rhs else EPS
    return f"{lhs} -> {body}"


def _used_listing(g: Grammar, used) -> List[str]:
    """The sub-grammar actually used to derive one input: the productions that
    fired during the parse, plus the augmentation (rule 0), in grammar order."""
    return [f"{i}: {production_str(g, i)}" for i in sorted(set(used) | {0})]


def grammar_listing(g: Grammar) -> List[str]:
    return [f"{i}: {production_str(g, i)}" for i in range(len(g.productions))]


# ───────────────────── Grammar text -> Grammar ─────────────────────

def parse_grammar(text: str):
    """
    Parse and validate a SMILE-BNF grammar.

    Returns (grammar_or_None, errors, warnings, info).
      * grammar is None when there is any hard error.
      * info always carries whatever we could detect (start / nonterminals /
        terminals) so the UI can show it even for a rejected grammar.
    """
    errors: List[str] = []
    warnings: List[str] = []

    raw_prods: List[Tuple[str, List[str]]] = []
    lhs_order: List[str] = []

    for n, line in enumerate(text.splitlines(), 1):
        ln = line.strip()
        if not ln or ln.startswith("#"):
            continue
        if "->" not in ln:
            errors.append(
                f"faaaah: line {n}: '->' missing -- har production aise likho:  A -> X Y | Z"
            )
            continue
        lhs_part, rhs_part = ln.split("->", 1)
        lhs = lhs_part.strip()
        if not lhs or len(lhs.split()) != 1:
            errors.append(
                f"faaaah: line {n}: left side '{lhs_part.strip()}' ek single nonterminal hona chahiye"
            )
            continue
        if lhs not in lhs_order:
            lhs_order.append(lhs)

        for alt in rhs_part.split("|"):
            syms = alt.split()
            if not syms or (len(syms) == 1 and syms[0] in EPSILON_TOKENS):
                raw_prods.append((lhs, []))               # epsilon production
            elif any(s in EPSILON_TOKENS for s in syms):
                errors.append(
                    f"faaaah: line {n}: epsilon ko kisi aur symbol ke saath mat milao"
                )
            else:
                raw_prods.append((lhs, syms))

    if not raw_prods and not errors:
        errors.append("faaaah: koi production nahi mila -- grammar khaali hai")

    # Any symbol that never appears as a head is a terminal (textbook BNF rule).
    # Terminals may be abstract (a, b, +, id, ...) — they need not be SMILE tokens.
    nonterminals = set(lhs_order)
    terminals: Set[str] = set()
    for lhs, rhs in raw_prods:
        for s in rhs:
            if s not in nonterminals:
                terminals.add(s)

    # Input mode: if every terminal is a real SMILE token we can drive the parse
    # straight from the lexer; otherwise the input is a raw terminal stream.
    lexer_mode = all(t in VALID_TERMINALS for t in terminals)

    start = lhs_order[0] if lhs_order else None
    info = {
        "start": start,
        "nonterminals": lhs_order,
        "terminals": sorted(terminals),
        "input_mode": "lexer" if lexer_mode else "raw",
    }

    if errors or start is None:
        return None, errors, warnings, info

    # Augment: S' -> start  (pick an unused primed name)
    aug = start + "'"
    while aug in nonterminals:
        aug += "'"
    productions = [(aug, [start])] + raw_prods
    nonterminals.add(aug)

    g = Grammar(
        productions=productions,
        start=aug,
        real_start=start,
        nonterminals=nonterminals,
        terminals=terminals,
        display_nonterminals=lhs_order,
        lexer_mode=lexer_mode,
    )

    warnings.extend(_reachability_warnings(g))
    info["augmented"] = aug
    return g, errors, warnings, info


def _reachability_warnings(g: Grammar) -> List[str]:
    warnings: List[str] = []

    # Productive: can derive a string of terminals (epsilon counts as productive).
    productive: Set[str] = set()
    changed = True
    while changed:
        changed = False
        for lhs, rhs in g.productions:
            if lhs in productive:
                continue
            if all(s in g.terminals or s in productive for s in rhs):
                productive.add(lhs)
                changed = True
    for nt in g.display_nonterminals:
        if nt not in productive:
            warnings.append(
                f"faaaah (warning): '{nt}' kabhi terminal string mein nahi badalta "
                f"(unproductive) -- infinite recursion ya missing rule"
            )

    # Reachable from the start symbol.
    reachable: Set[str] = {g.real_start}
    changed = True
    while changed:
        changed = False
        for lhs, rhs in g.productions:
            if lhs == g.start or lhs in reachable:
                for s in rhs:
                    if s in g.nonterminals and s not in reachable:
                        reachable.add(s)
                        changed = True
    for nt in g.display_nonterminals:
        if nt not in reachable:
            warnings.append(
                f"faaaah (warning): '{nt}' start symbol se reachable nahi -- ye rule kabhi use nahi hoga"
            )

    return warnings


# ───────────────────────── FIRST / FOLLOW ──────────────────────────


def compute_first(g: Grammar) -> Dict[str, Set[str]]:
    first: Dict[str, Set[str]] = {nt: set() for nt in g.nonterminals}
    for t in g.terminals:
        first[t] = {t}

    changed = True
    while changed:
        changed = False
        for lhs, rhs in g.productions:
            before = len(first[lhs])
            if not rhs:                       # A -> ε
                first[lhs].add(EPS)
            else:
                nullable_prefix = True
                for sym in rhs:
                    fsym = first.get(sym, {sym})
                    first[lhs] |= (fsym - {EPS})
                    if EPS not in fsym:
                        nullable_prefix = False
                        break
                if nullable_prefix:
                    first[lhs].add(EPS)
            if len(first[lhs]) != before:
                changed = True
    return first


def first_of_sequence(symbols: List[str], first: Dict[str, Set[str]]) -> Set[str]:
    """FIRST of a string of grammar symbols (may include EPS if all are nullable)."""
    result: Set[str] = set()
    for sym in symbols:
        fsym = first.get(sym, {sym})
        result |= (fsym - {EPS})
        if EPS not in fsym:
            return result
    result.add(EPS)
    return result


def compute_follow(g: Grammar, first: Dict[str, Set[str]]) -> Dict[str, Set[str]]:
    follow: Dict[str, Set[str]] = {nt: set() for nt in g.nonterminals}
    follow[g.start].add(END)

    changed = True
    while changed:
        changed = False
        for lhs, rhs in g.productions:
            for idx, sym in enumerate(rhs):
                if sym not in g.nonterminals:
                    continue
                beta = rhs[idx + 1:]
                add = first_of_sequence(beta, first) if beta else {EPS}
                # terminals from FIRST(beta)
                new = (add - {EPS})
                # if beta is nullable (or empty), FOLLOW(lhs) flows in
                if EPS in add or not beta:
                    new = new | follow[lhs]
                if not new <= follow[sym]:
                    follow[sym] |= new
                    changed = True
    return follow


# ─────────────────────── LR(0) item machinery ──────────────────────
# An LR(0) item is (production_index, dot_position).

def lr0_closure(g: Grammar, items: Set[Tuple[int, int]]) -> Set[Tuple[int, int]]:
    closure = set(items)
    changed = True
    while changed:
        changed = False
        for prod, dot in list(closure):
            _, rhs = g.productions[prod]
            if dot < len(rhs):
                B = rhs[dot]
                if B in g.nonterminals:
                    for p, (lhs2, _) in enumerate(g.productions):
                        if lhs2 == B and (p, 0) not in closure:
                            closure.add((p, 0))
                            changed = True
    return closure


def lr0_goto(g: Grammar, items: Set[Tuple[int, int]], symbol: str) -> Set[Tuple[int, int]]:
    moved = set()
    for prod, dot in items:
        _, rhs = g.productions[prod]
        if dot < len(rhs) and rhs[dot] == symbol:
            moved.add((prod, dot + 1))
    return lr0_closure(g, moved) if moved else set()


def build_lr0_collection(g: Grammar):
    start_state = lr0_closure(g, {(0, 0)})
    states = [start_state]
    transitions: Dict[Tuple[int, str], int] = {}

    symbols = sorted(g.nonterminals) + sorted(g.terminals)
    changed = True
    while changed:
        changed = False
        for i, state in enumerate(list(states)):
            for sym in symbols:
                target = lr0_goto(g, state, sym)
                if not target:
                    continue
                if target in states:
                    j = states.index(target)
                else:
                    states.append(target)
                    j = len(states) - 1
                    changed = True
                if (i, sym) not in transitions:
                    transitions[(i, sym)] = j
                    changed = True
    return states, transitions


def lr0_item_str(g: Grammar, prod: int, dot: int) -> str:
    lhs, rhs = g.productions[prod]
    body = rhs[:dot] + ["."] + rhs[dot:]
    return f"{lhs} -> {' '.join(body)}"


# ───────────────────── Generic LR table-driven parse ───────────────

def lr_parse(g: Grammar,
             action: Dict[int, Dict[str, str]],
             goto: Dict[int, Dict[str, int]],
             input_terminals: List[str],
             display_tokens: List[str]) -> dict:
    """Drive an LR parse using ACTION/GOTO tables shared by LR(0) and SLR(1)."""
    state_stack = [0]
    symbol_stack: List[str] = []
    node_stack: List[dict] = []
    pointer = 0
    trace: List[dict] = []
    step = 0
    guard = 0
    used: Set[int] = set()

    tokens = list(input_terminals) + [END]
    disp = list(display_tokens) + [END]

    while True:
        step += 1
        guard += 1
        if guard > 10000:
            return {"accepted": False,
                    "error": "faaaah: parser loop mein phans gaya (grammar/table conflict?)",
                    "trace": trace, "used_grammar": _used_listing(g, used)}
        state = state_stack[-1]
        lookahead = tokens[pointer]
        act = action.get(state, {}).get(lookahead)

        stack_repr = "0 " + " ".join(
            f"{symbol_stack[k]} {state_stack[k + 1]}" for k in range(len(symbol_stack))
        )
        input_repr = " ".join(disp[pointer:])

        if act is None:
            trace.append({"step": step, "stack": stack_repr.strip(),
                          "input": input_repr,
                          "action": f"error: unexpected '{disp[pointer]}'"})
            return {"accepted": False,
                    "error": f"faaaah: syntax error -> '{disp[pointer]}' yahan nahi aana chahiye tha",
                    "trace": trace, "used_grammar": _used_listing(g, used)}

        if act == "acc":
            trace.append({"step": step, "stack": stack_repr.strip(),
                          "input": input_repr, "action": "accept"})
            tree = node_stack[-1] if node_stack else None
            return {"accepted": True, "error": None, "trace": trace, "tree": tree,
                    "used_grammar": _used_listing(g, used), "used_prods": used}

        if act.startswith("s"):
            next_state = int(act[1:])
            trace.append({"step": step, "stack": stack_repr.strip(),
                          "input": input_repr, "action": f"shift -> state {next_state}"})
            symbol_stack.append(disp[pointer])
            node_stack.append({"label": disp[pointer], "terminal": True, "children": []})
            state_stack.append(next_state)
            pointer += 1

        elif act.startswith("r"):
            prod = int(act[1:])
            used.add(prod)
            lhs, rhs = g.productions[prod]
            trace.append({"step": step, "stack": stack_repr.strip(),
                          "input": input_repr,
                          "action": f"reduce by {prod}: {production_str(g, prod)}"})
            if rhs:
                children = node_stack[len(node_stack) - len(rhs):]
                del node_stack[len(node_stack) - len(rhs):]
                for _ in rhs:
                    state_stack.pop()
                    symbol_stack.pop()
            else:
                children = [{"label": EPS, "terminal": True, "children": []}]
            node_stack.append({"label": lhs, "terminal": False, "children": children})
            symbol_stack.append(lhs)
            goto_state = goto.get(state_stack[-1], {}).get(lhs)
            if goto_state is None:
                return {"accepted": False,
                        "error": f"faaaah: no GOTO for {lhs} from state {state_stack[-1]}",
                        "trace": trace, "used_grammar": _used_listing(g, used)}
            state_stack.append(goto_state)


def _make_lr_tables(g: Grammar, reduce_on):
    """
    Build ACTION/GOTO over the LR(0) automaton.
    `reduce_on(prod)` returns the set of terminals a completed item reduces on:
      * LR(0): every terminal + $
      * SLR(1): FOLLOW(lhs)
    Shifts win conflicts (assigned first; set_action keeps the first action).
    """
    states, transitions = build_lr0_collection(g)
    action: Dict[int, Dict[str, str]] = {i: {} for i in range(len(states))}
    goto: Dict[int, Dict[str, int]] = {i: {} for i in range(len(states))}
    conflicts: List[str] = []

    def set_action(i, sym, val):
        existing = action[i].get(sym)
        if existing is not None and existing != val:
            conflicts.append({
                "row": f"State {i}",
                "column": sym,
                "detail": f"{existing} vs {val}",
            })
            return                       # keep first (shifts assigned first)
        action[i][sym] = val

    for (i, sym), j in transitions.items():
        if sym in g.nonterminals:
            goto[i][sym] = j
        else:
            set_action(i, sym, f"s{j}")

    for i, state in enumerate(states):
        for prod, dot in state:
            _, rhs = g.productions[prod]
            if dot == len(rhs):                       # complete item
                if prod == 0:
                    set_action(i, END, "acc")
                else:
                    for a in reduce_on(prod):
                        set_action(i, a, f"r{prod}")

    # outgoing GOTO edges per state: state i --on symbol--> state j
    edges_by_state: Dict[int, list] = {i: [] for i in range(len(states))}
    for (i, sym), j in transitions.items():
        edges_by_state[i].append({"symbol": sym, "to": j})
    for i in edges_by_state:
        edges_by_state[i].sort(key=lambda e: e["symbol"])

    state_items = [
        {"id": i,
         "items": [lr0_item_str(g, p, d) for (p, d) in sorted(state)],
         "transitions": edges_by_state[i]}
        for i, state in enumerate(states)
    ]
    return states, action, goto, conflicts, state_items


def build_lr0(g: Grammar):
    first = compute_first(g)
    all_terms = sorted(g.terminals) + [END]
    states, action, goto, conflicts, state_items = _make_lr_tables(
        g, reduce_on=lambda prod: all_terms
    )
    return {"first": first, "states": state_items,
            "action": action, "goto": goto, "conflicts": conflicts}


def build_slr(g: Grammar):
    first = compute_first(g)
    follow = compute_follow(g, first)
    states, action, goto, conflicts, state_items = _make_lr_tables(
        g, reduce_on=lambda prod: follow[g.productions[prod][0]]
    )
    return {"first": first, "follow": follow, "states": state_items,
            "action": action, "goto": goto, "conflicts": conflicts}


# ────────────────────── Operator Precedence ────────────────────────

def is_operator_grammar(g: Grammar):
    """An operator grammar has no ε-production and no two adjacent nonterminals."""
    for lhs, rhs in g.productions[1:]:        # skip augmented S' -> start
        if not rhs:
            return False, f"production '{lhs} -> ε' epsilon hai"
        for k in range(len(rhs) - 1):
            if rhs[k] in g.nonterminals and rhs[k + 1] in g.nonterminals:
                return False, f"'{lhs} -> {' '.join(rhs)}' mein do nonterminal saath saath hain"
    return True, None


def compute_leading(g: Grammar) -> Dict[str, Set[str]]:
    leading: Dict[str, Set[str]] = {nt: set() for nt in g.nonterminals}
    changed = True
    while changed:
        changed = False
        for lhs, rhs in g.productions:
            if not rhs:
                continue
            sym = rhs[0]
            if sym in g.terminals:
                if sym not in leading[lhs]:
                    leading[lhs].add(sym)
                    changed = True
            else:
                before = len(leading[lhs])
                leading[lhs] |= leading[sym]
                if len(rhs) > 1 and rhs[1] in g.terminals:
                    leading[lhs].add(rhs[1])
                if len(leading[lhs]) != before:
                    changed = True
    return leading


def compute_trailing(g: Grammar) -> Dict[str, Set[str]]:
    trailing: Dict[str, Set[str]] = {nt: set() for nt in g.nonterminals}
    changed = True
    while changed:
        changed = False
        for lhs, rhs in g.productions:
            if not rhs:
                continue
            sym = rhs[-1]
            if sym in g.terminals:
                if sym not in trailing[lhs]:
                    trailing[lhs].add(sym)
                    changed = True
            else:
                before = len(trailing[lhs])
                trailing[lhs] |= trailing[sym]
                if len(rhs) > 1 and rhs[-2] in g.terminals:
                    trailing[lhs].add(rhs[-2])
                if len(trailing[lhs]) != before:
                    changed = True
    return trailing


def build_precedence_table(g: Grammar):
    leading = compute_leading(g)
    trailing = compute_trailing(g)
    rel: Dict[str, Dict[str, str]] = {a: {} for a in sorted(g.terminals) + [END]}

    def put(a, b, r):
        rel[a][b] = r

    for lhs, rhs in g.productions:
        for k in range(len(rhs) - 1):
            x, y = rhs[k], rhs[k + 1]
            if x in g.terminals and y in g.terminals:
                put(x, y, "=")
            if x in g.terminals and y in g.nonterminals and k + 2 < len(rhs) \
                    and rhs[k + 2] in g.terminals:
                put(x, rhs[k + 2], "=")
            if x in g.terminals and y in g.nonterminals:
                for b in leading[y]:
                    put(x, b, "<")
            if x in g.nonterminals and y in g.terminals:
                for a in trailing[x]:
                    put(a, y, ">")

    for b in leading[g.real_start]:
        put(END, b, "<")
    for a in trailing[g.real_start]:
        put(a, END, ">")

    return leading, trailing, rel


def _valid_handles(g: Grammar) -> Dict[Tuple[str, ...], int]:
    """Map each production's terminal/N-projection to its index. Lone-nonterminal
    unit productions are skipped -- operator precedence never reduces a bare NT."""
    handles: Dict[Tuple[str, ...], int] = {}
    for i, (lhs, rhs) in enumerate(g.productions):
        if i == 0:
            continue
        pattern = tuple("N" if s in g.nonterminals else s for s in rhs)
        if len(pattern) == 1 and pattern[0] == "N":
            continue
        handles[pattern] = i
    return handles


def topmost_terminal(stack: List[str]) -> str:
    for sym in reversed(stack):
        if sym != "N":
            return sym
    return END


def parse_operator_precedence(g: Grammar,
                              input_terminals: List[str],
                              display_tokens: List[str]) -> dict:
    leading, trailing, rel = build_precedence_table(g)
    handles = _valid_handles(g)
    stack = [END]
    disp_stack = [END]
    node_stack: List[Optional[dict]] = [None]
    tokens = list(input_terminals) + [END]
    disp = list(display_tokens) + [END]
    pointer = 0
    trace: List[dict] = []
    step = 0

    while True:
        step += 1
        a = topmost_terminal(stack)
        b = tokens[pointer]
        stack_repr = " ".join(disp_stack)
        input_repr = " ".join(disp[pointer:])

        if a == END and b == END:
            trace.append({"step": step, "stack": stack_repr, "relation": "",
                          "input": input_repr, "action": "accept"})
            tree = node_stack[-1] if len(node_stack) > 1 else None
            return {"accepted": True, "error": None, "trace": trace, "tree": tree}

        relation = rel.get(a, {}).get(b)
        if relation is None:
            trace.append({"step": step, "stack": stack_repr, "relation": "",
                          "input": input_repr,
                          "action": f"error: no relation between '{a}' and '{b}'"})
            return {"accepted": False,
                    "error": f"faaaah: '{a}' aur '{b}' ke darmiyan koi relation nahi -- galat expression",
                    "trace": trace}

        if relation in ("<", "="):
            trace.append({"step": step, "stack": stack_repr, "relation": relation,
                          "input": input_repr, "action": f"shift '{disp[pointer]}'"})
            stack.append(b)
            disp_stack.append(disp[pointer])
            node_stack.append({"label": disp[pointer], "terminal": True, "children": []})
            pointer += 1
        else:                                            # '>' -> reduce the handle
            handle: List[str] = []
            handle_nodes: List[dict] = []
            while len(stack) > 1:
                sym = stack[-1]
                if sym == "N":
                    handle.insert(0, stack.pop())
                    disp_stack.pop()
                    handle_nodes.insert(0, node_stack.pop())
                    continue
                handle.insert(0, stack.pop())
                disp_stack.pop()
                handle_nodes.insert(0, node_stack.pop())
                below = topmost_terminal(stack)
                if rel.get(below, {}).get(sym) == "<":
                    break
            while len(stack) > 1 and stack[-1] == "N":
                handle.insert(0, stack.pop())
                disp_stack.pop()
                handle_nodes.insert(0, node_stack.pop())

            pattern = tuple("N" if s == "N" else s for s in handle)
            prod = handles.get(pattern)
            if prod is None:
                trace.append({"step": step, "stack": stack_repr, "relation": relation,
                              "input": input_repr,
                              "action": f"error: '{' '.join(handle)}' kisi rule se match nahi karta"})
                return {"accepted": False,
                        "error": f"faaaah: '{' '.join(handle)}' valid handle nahi -- "
                                 f"ye kisi grammar rule se match nahi karta",
                        "trace": trace}
            stack.append("N")
            disp_stack.append("N")
            node_stack.append({"label": g.productions[prod][0], "terminal": False,
                               "children": handle_nodes})
            trace.append({"step": step, "stack": stack_repr, "relation": relation,
                          "input": input_repr,
                          "action": f"reduce by {prod}: {production_str(g, prod)}"})


# ─────────────────────────── LL(1) parser ──────────────────────────
# Top-down predictive parsing. Build the LL(1) table M[A][a] from FIRST/FOLLOW,
# then drive a stack: expand nonterminals via the table, match terminals against
# the input. Builds the parse tree top-down. Requires a non-left-recursive,
# left-factored grammar (e.g. SMILE_GRAMMAR) — otherwise the table has conflicts.

def build_ll1(g: Grammar):
    """Build the LL(1) predictive parsing table for grammar g.

    Returns {"first","follow","table","conflicts"} where
      table : {nonterminal: {terminal: production_index}}.
    A cell filled twice => the grammar is not LL(1) (conflict recorded).
    """
    first = compute_first(g)
    follow = compute_follow(g, first)

    table: Dict[str, Dict[str, int]] = {nt: {} for nt in g.nonterminals}
    conflicts: List[str] = []

    def put(nt, term, prod):
        if term in table[nt] and table[nt][term] != prod:
            conflicts.append({
                "row": nt,
                "column": term,
                "detail": f"{production_str(g, table[nt][term])}  vs  {production_str(g, prod)}",
            })
            return                                   # keep first
        table[nt][term] = prod

    for i, (lhs, rhs) in enumerate(g.productions):
        first_alpha = first_of_sequence(rhs, first) if rhs else {EPS}
        for term in first_alpha - {EPS}:
            put(lhs, term, i)
        if EPS in first_alpha:                       # nullable: use FOLLOW(lhs)
            for term in follow[lhs]:
                put(lhs, term, i)

    return {"first": first, "follow": follow, "table": table, "conflicts": conflicts}


def ll1_parse(g: Grammar,
              table: Dict[str, Dict[str, int]],
              input_terminals: List[str],
              display_tokens: List[str]) -> dict:
    """Drive an LL(1) parse with the predictive table; build the parse tree."""
    root = {"label": g.real_start, "terminal": False, "children": []}
    # stack of (symbol, node) — bottom-of-stack END sentinel has no node.
    stack: List[Tuple[str, Optional[dict]]] = [(END, None), (g.real_start, root)]

    tokens = list(input_terminals) + [END]
    disp = list(display_tokens) + [END]
    pointer = 0
    trace: List[dict] = []
    step = 0
    guard = 0
    used: Set[int] = set()

    while stack:
        step += 1
        guard += 1
        if guard > 10000:
            return {"accepted": False, "error": "faaaah: LL(1) parser loop mein phans gaya",
                    "trace": trace, "tree": None, "used_grammar": _used_listing(g, used)}

        top_sym, top_node = stack[-1]
        lookahead = tokens[pointer]
        stack_repr = " ".join(s for s, _ in stack)
        input_repr = " ".join(disp[pointer:])

        # bottom of stack
        if top_sym == END:
            if lookahead == END:
                trace.append({"step": step, "stack": stack_repr,
                              "input": input_repr, "action": "accept"})
                return {"accepted": True, "error": None, "trace": trace, "tree": root,
                        "used_grammar": _used_listing(g, used)}
            trace.append({"step": step, "stack": stack_repr, "input": input_repr,
                          "action": f"error: extra input '{disp[pointer]}'"})
            return {"accepted": False,
                    "error": f"faaaah: input khatam hona chahiye tha par '{disp[pointer]}' "
                             f"abhi bhi bacha hai",
                    "trace": trace, "tree": None, "used_grammar": _used_listing(g, used)}

        # terminal on top -> must match the input
        if top_sym in g.terminals or top_sym == EPS:
            if top_sym == EPS:
                stack.pop()
                continue
            if top_sym == lookahead:
                trace.append({"step": step, "stack": stack_repr, "input": input_repr,
                              "action": f"match '{disp[pointer]}'"})
                if top_node is not None:
                    top_node["label"] = disp[pointer]   # leaf shows the lexeme
                stack.pop()
                pointer += 1
                continue
            trace.append({"step": step, "stack": stack_repr, "input": input_repr,
                          "action": f"error: expected '{top_sym}', got '{disp[pointer]}'"})
            return {"accepted": False,
                    "error": f"faaaah: '{top_sym}' chahiye tha par '{disp[pointer]}' mila",
                    "trace": trace, "tree": None, "used_grammar": _used_listing(g, used)}

        # nonterminal on top -> consult the table
        prod = table.get(top_sym, {}).get(lookahead)
        if prod is None:
            trace.append({"step": step, "stack": stack_repr, "input": input_repr,
                          "action": f"error: no rule M[{top_sym}, {disp[pointer]}]"})
            return {"accepted": False,
                    "error": f"faaaah: '{top_sym}' ke liye '{disp[pointer]}' par koi rule "
                             f"nahi (LL(1) table khaali hai) -- syntax error",
                    "trace": trace, "tree": None, "used_grammar": _used_listing(g, used)}

        lhs, rhs = g.productions[prod]
        used.add(prod)
        trace.append({"step": step, "stack": stack_repr, "input": input_repr,
                      "action": f"output {prod}: {production_str(g, prod)}"})
        stack.pop()
        if rhs:
            child_nodes = [{"label": s, "terminal": s in g.terminals, "children": []}
                           for s in rhs]
            top_node["children"] = child_nodes
            for sym, node in zip(reversed(rhs), reversed(child_nodes)):
                stack.append((sym, node))
        else:                                        # A -> ε
            top_node["children"] = [{"label": EPS, "terminal": True, "children": []}]

    return {"accepted": False, "error": "faaaah: stack khaali ho gaya unexpectedly",
            "trace": trace, "tree": None}


def _ll1_table_serialise(g: Grammar, table: Dict[str, Dict[str, int]]) -> dict:
    """Table as {nt: {term: 'A -> α'}} for the UI grid."""
    return {
        nt: {term: production_str(g, prod) for term, prod in row.items()}
        for nt, row in table.items()
    }


# ───────────────────── Token -> terminal mapping ───────────────────

def tokens_to_terminals(code: str, g: Grammar):
    """Turn the input string into this grammar's terminals.
    Returns (terminals, display_values, error_or_None).

      * lexer_mode : run the SMILE lexer, then map each token to a terminal.
      * raw  mode  : the input is a space-separated stream of terminals
                     (textbook style, e.g. `a a b b`)."""
    if not g.lexer_mode:
        pieces = code.split()
        terminals: List[str] = []
        for p in pieces:
            if p not in g.terminals:
                return [], [], (
                    f"faaaah: '{p}' tumhari grammar ka terminal nahi -- "
                    f"valid terminals: {', '.join(sorted(g.terminals))}"
                )
            terminals.append(p)
        if not terminals:
            return [], [], (
                "faaaah: koi input nahi mila -- terminals ko space se likho, e.g.  a a b b"
            )
        return terminals, list(terminals), None

    lex = tokenize(code)
    if lex["errors"]:
        return [], [], lex["errors"][0]["message"]

    terminals = []
    display: List[str] = []
    for tok in lex["tokens"]:
        term = _map_token(tok)
        if term not in g.terminals:
            return [], [], (
                f"faaaah: '{tok['value']}' -> terminal '{term}' tumhari grammar mein "
                f"use nahi hota -- sirf ye terminals chalte hain: "
                f"{', '.join(sorted(g.terminals))}"
            )
        terminals.append(term)
        display.append(tok["value"])

    if not terminals:
        return [], [], "faaaah: koi input nahi mila -- kuch likho yaar"
    return terminals, display, None


# ─────────────────────────── Dispatcher ────────────────────────────

def _sets_to_lists(d: Dict[str, Set[str]], keys: List[str]) -> Dict[str, List[str]]:
    return {k: sorted(d[k]) for k in keys if k in d}


def _conflict_block(base: dict, conflicts: list) -> dict:
    """When the parsing table has conflicts we do NOT parse / build a tree --
    the grammar isn't deterministic for this parser. Report the conflicts (each
    carries its table row + column) instead."""
    base.update({
        "accepted": False,
        "conflict": True,
        "error": (f"faaaah: parser table mein {len(conflicts)} conflict(s) hain -- "
                  f"is grammar ka parse tree nahi banega (neeche row/column dekho)"),
        "trace": [],
        "tree": None,
    })
    return base


def analyze_grammar(grammar_text: str) -> dict:
    """Validate a grammar only (for the /validate_grammar endpoint)."""
    g, errors, warnings, info = parse_grammar(grammar_text)
    out = {
        "valid": g is not None,
        "errors": errors,
        "warnings": warnings,
        "start": info.get("start"),
        "nonterminals": info.get("nonterminals", []),
        "terminals": info.get("terminals", []),
        "input_mode": info.get("input_mode", "lexer"),
    }
    if g is not None:
        out["grammar"] = grammar_listing(g)
    return out


def _derive_used(g: Grammar, terminals, display):
    """Parse the input with SLR(1) on the FULL grammar and return the set of
    production indices used to derive it (None if it doesn't parse)."""
    tables = build_slr(g)
    res = lr_parse(g, tables["action"], tables["goto"], terminals, display)
    if not res.get("accepted"):
        return None
    return res.get("used_prods")


def _reduced_grammar(g_full: Grammar, used: set) -> Grammar:
    """Build a smaller grammar containing only the productions actually used to
    derive the current program (plus a fresh augmentation). FIRST/FOLLOW, the
    parse table and the item sets are then computed over THIS sub-grammar, so
    they only mention the terminals/nonterminals the program needs."""
    prods = [g_full.productions[i] for i in sorted(used) if i != 0]   # drop old augment
    real_start = g_full.real_start
    aug_start = real_start + "'"

    nonterminals = {aug_start} | {lhs for lhs, _ in prods}
    productions = [(aug_start, [real_start])] + prods

    terminals = set()
    for _, rhs in prods:
        for s in rhs:
            if s not in nonterminals and s != EPS:
                terminals.add(s)

    # real nonterminals in first-appearance order, start symbol first
    display_nts: List[str] = []
    for lhs, _ in [(real_start, None)] + prods:
        if lhs in nonterminals and lhs != aug_start and lhs not in display_nts:
            display_nts.append(lhs)

    return Grammar(productions, aug_start, real_start, nonterminals, terminals,
                   display_nts, g_full.lexer_mode)


def parse(code: str, method: str, grammar_text: str = DEFAULT_GRAMMAR_TEXT,
          reduced: bool = True) -> dict:
    """Top-level entry: validate grammar, tokenise, map to terminals, run parser.

    If `reduced` is set, the tables/FIRST/FOLLOW/item-sets are built from the
    sub-grammar of just the productions this program uses (so everything is
    "according to the code")."""
    method = (method or "").lower()
    g, gerrors, gwarnings, ginfo = parse_grammar(grammar_text or DEFAULT_GRAMMAR_TEXT)

    base = {
        "method": method,
        "grammar_errors": gerrors,
        "grammar_warnings": gwarnings,
        "grammar_info": ginfo,
    }

    if g is None:
        base.update({
            "accepted": False,
            "error": "faaaah: grammar theek karo pehle -- neeche errors dekho",
            "trace": [],
            "grammar": [],
        })
        return base

    # map the program to terminals using the full grammar's vocabulary
    terminals, display, err = tokens_to_terminals(code, g)

    # reduce the grammar to ONLY the productions this program uses
    base["reduced"] = False
    if reduced and err is None:
        used = _derive_used(g, terminals, display)
        if used:
            g = _reduced_grammar(g, used)
            terminals, display, err = tokens_to_terminals(code, g)
            base["reduced"] = True

    base["grammar"] = grammar_listing(g)
    base["terminals"] = sorted(g.terminals) + [END]
    base["nonterminals"] = g.display_nonterminals
    base["input_mode"] = "lexer" if g.lexer_mode else "raw"
    base["input_tokens"] = [
        {"value": d, "terminal": t} for d, t in zip(display, terminals)
    ] + [{"value": "$", "terminal": "$"}]

    nt_keys = g.display_nonterminals

    if method in ("lr0", "lr(0)", "lr"):
        tables = build_lr0(g)
        base.update({
            "method": "LR(0)",
            "parser_kind": "lr",
            "first": _sets_to_lists(tables["first"], nt_keys),
            "states": tables["states"],
            "action": tables["action"], "goto": tables["goto"],
            "conflicts": tables["conflicts"],
        })
        if tables["conflicts"]:
            return _conflict_block(base, tables["conflicts"])
        if not err:
            base.update(lr_parse(g, tables["action"], tables["goto"], terminals, display))
        else:
            base.update({"accepted": False, "error": err, "trace": []})
        return base

    if method in ("slr", "slr1", "slr(1)"):
        tables = build_slr(g)
        base.update({
            "method": "SLR(1)",
            "parser_kind": "lr",
            "first": _sets_to_lists(tables["first"], nt_keys),
            "follow": _sets_to_lists(tables["follow"], nt_keys),
            "states": tables["states"],
            "action": tables["action"], "goto": tables["goto"],
            "conflicts": tables["conflicts"],
        })
        if tables["conflicts"]:
            return _conflict_block(base, tables["conflicts"])
        if not err:
            base.update(lr_parse(g, tables["action"], tables["goto"], terminals, display))
        else:
            base.update({"accepted": False, "error": err, "trace": []})
        return base

    if method in ("ll1", "ll(1)", "ll"):
        tables = build_ll1(g)
        base.update({
            "method": "LL(1)",
            "parser_kind": "ll",
            "first": _sets_to_lists(tables["first"], nt_keys),
            "follow": _sets_to_lists(tables["follow"], nt_keys),
            "ll_table": _ll1_table_serialise(g, tables["table"]),
            "ll_terminals": sorted(g.terminals) + [END],
            "ll_nonterminals": nt_keys,
            "conflicts": tables["conflicts"],
        })
        if tables["conflicts"]:
            return _conflict_block(base, tables["conflicts"])
        if not err:
            base.update(ll1_parse(g, tables["table"], terminals, display))
        else:
            base.update({"accepted": False, "error": err, "trace": []})
        return base

    base.update({"accepted": False,
                 "error": f"Unknown parser method: {method}", "trace": []})
    return base


# ───────────────────────────── CLI test ────────────────────────────

if __name__ == "__main__":
    for m in ("lr0", "slr", "op"):
        print("=" * 64)
        print(f"  {m.upper()}  on  'x joro y guna z'")
        print("=" * 64)
        res = parse("x joro y guna z", m)
        print("accepted:", res.get("accepted"), "| error:", res.get("error"))
        print("conflicts:", res.get("conflicts"))
        for row in res.get("trace", []):
            if res.get("parser_kind") == "opprec":
                print(f'{row["step"]:>3}  {row["stack"]:<22} {row.get("relation",""):<2}'
                      f'  {row["input"]:<22} {row["action"]}')
            else:
                print(f'{row["step"]:>3}  {row["stack"]:<30} {row["input"]:<22} {row["action"]}')
        print()

    print("Invalid grammar (typo + missing arrow):")
    bad = "E -> E plus T\nT - F"
    a = analyze_grammar(bad)
    print(a["valid"], a["errors"])

    print("\nEpsilon grammar FIRST/FOLLOW:")
    g, e, w, info = parse_grammar("S -> a A\nA -> b | ε")
    if g:
        f = compute_first(g)
        fo = compute_follow(g, f)
        print("FIRST:", {k: sorted(f[k]) for k in g.display_nonterminals})
        print("FOLLOW:", {k: sorted(fo[k]) for k in g.display_nonterminals})
