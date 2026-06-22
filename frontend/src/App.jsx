import { useState } from "react";
import "./index.css";

const API_URL = "http://127.0.0.1:8000";

const SAMPLE_PROGRAMS = [
  {
    name: "Expression",
    code: `shuru karo
  adad x rakho 2 joro 3 guna 4 bas
  batao x bas
khatam`,
  },
  {
    name: "If / Else",
    code: `shuru karo
  adad n rakho 7 bas
  agar n zyada 5 shuru
    batao 1 bas
  banda warna shuru
    batao 0 bas
  banda
khatam`,
  },
  {
    name: "While Loop",
    code: `shuru karo
  adad i rakho 0 bas
  jab tak i kam 5 shuru
    batao i bas
    i rakho i joro 1 bas
  banda
khatam`,
  },
];

/* ── Compiler Phase Definitions ── */
const COMPILER_PHASES = [
  {
    id: "tokenizer",
    name: "Tokenizer",
    icon: "⚡",
    description: "Classifies each token by type — KEYWORD, IDENTIFIER, OPERATOR, etc.",
    color: "#06b6d4",
    gradient: "linear-gradient(135deg, #06b6d4, #0891b2)",
    glowColor: "rgba(6, 182, 212, 0.3)",
  },
  {
    id: "syntax",
    name: "Syntax Analyzer",
    icon: "🌳",
    description: "Checks grammatical structure and builds the parse tree",
    color: "#22c55e",
    gradient: "linear-gradient(135deg, #22c55e, #16a34a)",
    glowColor: "rgba(34, 197, 94, 0.3)",
  },
  {
    id: "semantic",
    name: "Semantic Analyzer",
    icon: "🧠",
    description: "Validates meaning — type checking, scope resolution, and more",
    color: "#ec4899",
    gradient: "linear-gradient(135deg, #ec4899, #db2777)",
    glowColor: "rgba(236, 72, 153, 0.3)",
  },
  {
    id: "threeaddr",
    name: "3-Address Code",
    icon: "🧾",
    description: "Generates three-address intermediate code (quadruples & triples)",
    color: "#0ea5e9",
    gradient: "linear-gradient(135deg, #0ea5e9, #0284c7)",
    glowColor: "rgba(14, 165, 233, 0.3)",
  },
  {
    id: "optimizer",
    name: "Code Optimizer",
    icon: "🚀",
    description: "Optimizes intermediate code for better performance",
    color: "#a855f7",
    gradient: "linear-gradient(135deg, #a855f7, #9333ea)",
    glowColor: "rgba(168, 85, 247, 0.3)",
  },
  {
    id: "codegen",
    name: "Code Generator",
    icon: "💻",
    description: "Generates target code from the optimized representation",
    color: "#14b8a6",
    gradient: "linear-gradient(135deg, #14b8a6, #0d9488)",
    glowColor: "rgba(20, 184, 166, 0.3)",
  },
];

/* ══════════════════════════════════════════════
   Tokenizer Page Component
   ══════════════════════════════════════════════ */
function TokenizerPage({ code, onBack }) {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleTokenize = async () => {
    if (!code.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch(`${API_URL}/tokenize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code }),
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(
        err.message.includes("Failed to fetch")
          ? "Backend server is not running! Start it with: uvicorn main:app --reload"
          : err.message
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="analysis-page">
      <div className="analysis-page-header">
        <button className="btn btn-back" onClick={onBack}>
          <span className="back-arrow">←</span> Back to Home
        </button>
        <div className="analysis-page-title">
          <span className="analysis-icon" style={{ background: "linear-gradient(135deg, #06b6d4, #0891b2)" }}>⚡</span>
          <div>
            <h2>Tokenizer</h2>
            <span className="analysis-subtitle">Classifies each token by type</span>
          </div>
        </div>
        <button
          id="tokenize-btn"
          className="btn btn-primary btn-run"
          onClick={handleTokenize}
          disabled={loading || !code.trim()}
        >
          {loading ? (
            <>
              <span className="loading-spinner" /> Tokenizing…
            </>
          ) : (
            <>⚡ Run Tokenizer</>
          )}
        </button>
      </div>

      <div className="analysis-page-body">
        {/* Code Preview */}
        <div className="code-preview-section">
          <div className="code-preview-label">Source Code Input</div>
          <pre className="code-preview">{code}</pre>
        </div>

        {/* Results */}
        <div className="analysis-results">
          {/* Connection Error */}
          {error && (
            <div className="errors-section">
              <div className="error-card">{error}</div>
            </div>
          )}

          {/* Empty State */}
          {!result && !error && (
            <div className="output-empty">
              <div className="empty-icon">⚡</div>
              <p>
                Click <strong>Run Tokenizer</strong> to see the lexical analysis output.
              </p>
            </div>
          )}

          {/* Stats */}
          {result && (
            <div className="result-stats-bar">
              <div className="stat tokens">
                ✓ {result.total_tokens} tokens
              </div>
              {result.total_errors > 0 && (
                <div className="stat errors">
                  ✗ {result.total_errors} error
                  {result.total_errors > 1 ? "s" : ""}
                </div>
              )}
            </div>
          )}

          {/* Errors from tokenizer */}
          {result && result.errors.length > 0 && (
            <div className="errors-section">
              {result.errors.map((err, i) => (
                <div key={i} className="error-card">
                  {err.message}
                </div>
              ))}
            </div>
          )}

          {/* Token Table */}
          {result && result.tokens.length > 0 && (
            <div className="token-table-wrapper">
              <table className="token-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Type</th>
                    <th>Value</th>
                    <th>Position</th>
                  </tr>
                </thead>
                <tbody>
                  {result.tokens.map((token, i) => (
                    <tr
                      key={i}
                      className="token-row"
                      style={{ animationDelay: `${i * 20}ms` }}
                    >
                      <td className="token-position">{i + 1}</td>
                      <td>
                        <span
                          className={`token-badge ${token.type}`}
                        >
                          {token.type}
                        </span>
                      </td>
                      <td className="token-value">
                        {token.value}
                      </td>
                      <td className="token-position">
                        Ln {token.line}, Col {token.column}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ── Parser definitions ── */
const PARSER_METHODS = [
  { id: "lr0", name: "LR(0)", blurb: "Bottom-up; reductions on ALL terminals (no lookahead)" },
  { id: "slr", name: "SLR(1)", blurb: "Bottom-up; LR(0) automaton + FOLLOW sets decide reductions" },
  { id: "ll1", name: "LL(1)", blurb: "Top-down predictive; FIRST/FOLLOW build the parse table" },
];

/* The fixed SMILE language grammar (LL(1) form). Built into the project — the
   parser uses this directly, there is no runtime grammar input. Keep in sync
   with SMILE_GRAMMAR in backend/parsers.py. */
const SMILE_GRAMMAR = `PROG  -> shuru_karo STMTS khatam
STMTS -> STMT SREST
SREST -> STMT SREST | ε
STMT  -> DECL | ASG | IF | WHILE | FOR | PRINT | RET | rok bas | agla bas
DECL  -> TYPE id rakho EXPR bas
ASG   -> id rakho EXPR bas
PRINT -> batao EXPR bas
RET   -> wapas_de EXPR bas
TYPE  -> adad | desi | baat | khaali
BLOCK -> shuru STMTS banda
IF    -> agar COND BLOCK ELSE
ELSE  -> warna BLOCK | warna_agar COND BLOCK ELSE | ε
WHILE -> jab_tak COND BLOCK
FOR   -> baar_baar id rakho EXPR bas COND bas id rakho EXPR BLOCK
COND  -> EXPR REL EXPR
REL   -> zyada | kam | barabar | zyada_ya_barabar | kam_ya_barabar | na_barabar
EXPR  -> T EREST
EREST -> joro T EREST | ghata T EREST | ε
T     -> F TREST
TREST -> guna F TREST | taqseem F TREST | bacha F TREST | ε
F     -> id | num | str`;

const PARSER_SAMPLES = [
  { name: "If / else", code: `shuru karo
adad x rakho 5 bas
agar x zyada 3 shuru
batao x bas
banda warna shuru
batao x bas
banda
khatam` },
  { name: "While loop", code: `shuru karo
adad i rakho 0 bas
jab tak i kam 5 shuru
batao i bas
i rakho i joro 1 bas
banda
khatam` },
  { name: "For loop", code: `shuru karo
baar baar i rakho 0 bas i kam 5 bas i rakho i joro 1 shuru
batao i bas
banda
khatam` },
  { name: "Else-if chain", code: `shuru karo
adad m rakho 75 bas
agar m zyada 80 shuru
batao m bas
banda warna agar m zyada 60 shuru
batao m bas
banda warna shuru
batao m bas
banda
khatam` },
  { name: "Expression", code: `shuru karo
adad y rakho 2 joro 3 guna 4 bas
batao y bas
khatam` },
];

/* small helper: render a "key → sorted set" map as rows */
function SetTable({ title, data }) {
  if (!data) return null;
  return (
    <div className="parse-section">
      <div className="parse-section-title">{title}</div>
      <table className="token-table compact">
        <tbody>
          {Object.keys(data).map((k) => (
            <tr key={k}>
              <td className="set-key">{k}</td>
              <td className="token-value">{"{ " + data[k].join(", ") + " }"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* recursive parse-tree node — terminals are leaves, nonterminals branch */
function TreeNode({ node }) {
  if (!node) return null;
  const hasChildren = node.children && node.children.length > 0;
  return (
    <li className="tree-node">
      <span className={node.terminal ? "tree-label tree-terminal" : "tree-label tree-nonterminal"}>
        {node.label}
      </span>
      {hasChildren && (
        <ul className="tree-children">
          {node.children.map((c, i) => <TreeNode key={i} node={c} />)}
        </ul>
      )}
    </li>
  );
}

/* ══════════════════════════════════════════════
   Parser Page Component (LR(0) / SLR(1) / Operator Precedence)
   ══════════════════════════════════════════════ */
function ParserPage({ code, onBack }) {
  const [showGrammar, setShowGrammar] = useState(false);
  const [method, setMethod] = useState("ll1");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const networkError = (err) =>
    err.message.includes("Failed to fetch")
      ? "Backend server is not running! Start it with: uvicorn main:app --reload"
      : err.message;

  const runParse = async (chosen) => {
    const m = chosen || method;
    if (!code.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await fetch(`${API_URL}/parse`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: code, method: m, grammar: SMILE_GRAMMAR, reduced: true }),
      });
      if (!response.ok) throw new Error(`Server error: ${response.status}`);
      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(networkError(err));
    } finally {
      setLoading(false);
    }
  };

  const isLR = result && result.parser_kind === "lr";
  const isLL = result && result.parser_kind === "ll";
  const terminals = result ? (result.terminals || result.ll_terminals || []) : [];
  const goNonterms = (result && result.nonterminals) || [];
  const llNonterms = (result && result.ll_nonterminals) || [];
  const llTerms = (result && result.ll_terminals) || [];

  return (
    <div className="analysis-page">
      <div className="analysis-page-header">
        <button className="btn btn-back" onClick={onBack}>
          <span className="back-arrow">←</span> Back to Home
        </button>
        <div className="analysis-page-title">
          <span className="analysis-icon" style={{ background: "linear-gradient(135deg, #f59e0b, #d97706)" }}>🧩</span>
          <div>
            <h2>Parser — Syntax Analysis</h2>
            <span className="analysis-subtitle">Bottom-up parsing of SMILE expressions</span>
          </div>
        </div>
        <button
          className="btn btn-primary btn-run"
          onClick={() => runParse()}
          disabled={loading || !code.trim()}
        >
          {loading ? (<><span className="loading-spinner" /> Parsing…</>) : (<>🧩 Run Parser</>)}
        </button>
      </div>

      <div className="parser-body">
        {/* ── Controls ── */}
        <div className="parser-controls">
          <div className="parser-io-label">Source program <span className="grammar-fixed-tag">from editor</span></div>
          <pre className="grammar-block source-preview">{code}</pre>

          <div className="parser-io-label">
            SMILE Grammar
            <span className="grammar-fixed-tag">built-in · fixed</span>
          </div>
          <div className="grammar-fixed-note">
            The parser uses the SMILE language grammar defined in the project (LL(1) form).
          </div>
          <button className="btn btn-load grammar-toggle" onClick={() => setShowGrammar((s) => !s)}>
            {showGrammar ? "▾ Hide grammar" : "▸ Show grammar"}
          </button>
          {showGrammar && <pre className="grammar-block">{SMILE_GRAMMAR}</pre>}

          <div className="parser-io-label">Parser Algorithm</div>
          <div className="method-selector">
            {PARSER_METHODS.map((pm) => (
              <button
                key={pm.id}
                className={`method-btn ${method === pm.id ? "active" : ""}`}
                onClick={() => { setMethod(pm.id); runParse(pm.id); }}
              >
                <strong>{pm.name}</strong>
                <span>{pm.blurb}</span>
              </button>
            ))}
          </div>

          {method === "ll1" && (
            <div className="parser-note">
              Note: LL(1) is <strong>top-down</strong> (predictive). It expands nonterminals using the
              FIRST/FOLLOW parse table and matches terminals against the input — the opposite direction
              to the bottom-up LR parsers. The SMILE grammar is left-factored and non-left-recursive
              so the LL(1) table has no conflicts.
            </div>
          )}
          {method === "slr" && (
            <div className="parser-note">
              Note: SLR(1) is <strong>bottom-up</strong>. It builds the LR(0) automaton and uses FOLLOW
              sets to decide reductions — handles the full SMILE grammar with no conflicts.
            </div>
          )}
          {method === "lr0" && (
            <div className="parser-note">
              Note: LR(0) reduces on every terminal regardless of lookahead, so a grammar this size
              shows many shift/reduce conflicts — exactly why SLR(1) adds FOLLOW sets. Any conflicts
              are listed above the trace.
            </div>
          )}
        </div>

        {/* ── Output ── */}
        <div className="parser-output">
          {error && (
            <div className="errors-section"><div className="error-card">{error}</div></div>
          )}

          {!result && !error && (
            <div className="output-empty">
              <div className="empty-icon">🧩</div>
              <p>Pick an algorithm and click <strong>Run Parser</strong> to see the parse tables and step-by-step trace.</p>
            </div>
          )}

          {result && (
            <>
              {/* Verdict */}
              <div className="result-stats-bar">
                <div className={`stat ${result.accepted ? "tokens" : "errors"}`}>
                  {result.accepted ? "✓ ACCEPTED" : "✗ REJECTED"} · {result.method}
                </div>
                {result.conflicts && result.conflicts.length > 0 && (
                  <div className="stat errors">⚠ {result.conflicts.length} conflict(s)</div>
                )}
              </div>

              {result.error && (
                <div className="errors-section"><div className="error-card">{result.error}</div></div>
              )}

              {/* Parser conflicts — row & column of each clash; tree NOT generated */}
              {result.conflicts && result.conflicts.length > 0 && (
                <div className="parse-section">
                  <div className="parse-section-title">
                    Parser Conflicts ({result.conflicts.length})
                    <span className="tree-note"> · parse tree not generated — grammar is not {result.method} for these cells</span>
                  </div>
                  <div className="token-table-wrapper">
                    <table className="token-table compact">
                      <thead>
                        <tr>
                          <th>#</th>
                          <th>Row ({isLL ? "Nonterminal" : "State"})</th>
                          <th>Column ({isLL ? "Terminal" : "Symbol"})</th>
                          <th>Conflict</th>
                        </tr>
                      </thead>
                      <tbody>
                        {result.conflicts.map((c, i) => (
                          <tr key={i} className="row-error">
                            <td className="set-key">{i + 1}</td>
                            <td className="token-value mono">{c.row}</td>
                            <td className="token-value mono">{c.column}</td>
                            <td className="token-value mono">{c.detail}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Grammar used by this program (reduced to the productions it needs) */}
              {result.grammar && result.grammar.length > 0 && (
                <div className="parse-section">
                  <div className="parse-section-title">
                    Grammar — used by this program
                    <span className="tree-note"> · {result.grammar.length} productions (augmented)</span>
                  </div>
                  <pre className="grammar-block used-grammar-block">{result.grammar.join("\n")}</pre>
                </div>
              )}

              {/* Input token mapping */}
              {result.input_tokens && (
                <div className="parse-section">
                  <div className="parse-section-title">Input → Terminals</div>
                  <div className="terminal-chips">
                    {result.input_tokens.map((t, i) => (
                      <span key={i} className="terminal-chip">
                        <span className="chip-val">{t.value}</span>
                        <span className="chip-term">{t.terminal}</span>
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Parse trace */}
              {result.trace && result.trace.length > 0 && (
              <div className="parse-section">
                <div className="parse-section-title">Parse Trace</div>
                <div className="token-table-wrapper">
                  <table className="token-table">
                    <thead>
                      <tr><th>#</th><th>Stack</th><th>Input</th><th>{isLL ? "Action (top-down)" : "Action"}</th></tr>
                    </thead>
                    <tbody>
                      {result.trace.map((row, i) => (
                        <tr key={i} className={row.action.startsWith("accept") ? "row-accept" : row.action.startsWith("error") ? "row-error" : ""}>
                          <td className="token-position">{row.step}</td>
                          <td className="token-value mono">{row.stack}</td>
                          <td className="token-value mono">{row.input}</td>
                          <td className="mono">{row.action}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
              )}

              {/* Parse tree */}
              {result.accepted && result.tree && (
                <div className="parse-section">
                  <div className="parse-section-title">
                    Parse Tree
                    {isLL && <span className="tree-note"> · built top-down (LL(1))</span>}
                  </div>
                  <div className="tree-wrapper">
                    <ul className="tree-root">
                      <TreeNode node={result.tree} />
                    </ul>
                  </div>
                </div>
              )}

              {/* FIRST / FOLLOW (LR and LL) */}
              {(isLR || isLL) && <SetTable title="FIRST sets" data={result.first} />}
              {(isLR || isLL) && result.follow && <SetTable title="FOLLOW sets" data={result.follow} />}

              {/* LR: parsing table */}
              {isLR && (
                <div className="parse-section">
                  <div className="parse-section-title">Parsing Table (ACTION | GOTO)</div>
                  <div className="token-table-wrapper">
                    <table className="token-table grid-table">
                      <thead>
                        <tr>
                          <th>State</th>
                          {terminals.map((t) => <th key={t}>{t}</th>)}
                          {goNonterms.map((nt) => <th key={nt} className="goto-col">{nt}</th>)}
                        </tr>
                      </thead>
                      <tbody>
                        {result.states.map((st) => (
                          <tr key={st.id}>
                            <td className="token-position">{st.id}</td>
                            {terminals.map((t) => (
                              <td key={t} className="mono cell">{(result.action[st.id] || {})[t] || ""}</td>
                            ))}
                            {goNonterms.map((nt) => (
                              <td key={nt} className="mono cell goto-col">{(result.goto[st.id] || {})[nt] ?? ""}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* LR: canonical item sets */}
              {isLR && (
                <div className="parse-section">
                  <div className="parse-section-title">Canonical Collection of Item Sets ({result.states.length} states)</div>
                  <div className="item-sets">
                    {result.states.map((st) => (
                      <div key={st.id} className="item-set">
                        <div className="item-set-id">I{st.id}</div>
                        <div className="item-set-items">
                          {st.items.map((it, i) => <div key={i} className="mono">{it}</div>)}
                        </div>
                        {st.transitions && st.transitions.length > 0 && (
                          <div className="item-set-goto">
                            {st.transitions.map((t, i) => (
                              <div key={i} className="goto-edge">
                                <span className="goto-sym">{t.symbol}</span>
                                <span className="goto-arrow"> → </span>
                                <span className="goto-target">I{t.to}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* LL(1): predictive parse table  M[nonterminal, terminal] */}
              {isLL && result.ll_table && (
                <div className="parse-section">
                  <div className="parse-section-title">LL(1) Predictive Parse Table</div>
                  <div className="token-table-wrapper">
                    <table className="token-table grid-table">
                      <thead>
                        <tr>
                          <th>NT \ term</th>
                          {llTerms.map((t) => <th key={t}>{t}</th>)}
                        </tr>
                      </thead>
                      <tbody>
                        {llNonterms.map((nt) => (
                          <tr key={nt}>
                            <td className="token-position">{nt}</td>
                            {llTerms.map((t) => {
                              const cell = (result.ll_table[nt] || {})[t];
                              return <td key={t} className="mono cell ll-cell" title={cell || ""}>{cell || ""}</td>;
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════════
   Semantic Analyzer Page  (Syntax-Directed Translation)
   ══════════════════════════════════════════════ */

/* The grammar the Semantic page uses. It is the SAME SMILE language as the
   Parser page, but written **left-recursive** (EXPR -> EXPR joro T ...). Value
   computation with synthesized attributes is natural on a left-recursive
   grammar, and the bottom-up SLR parser (which the semantic phase uses) handles
   left recursion with no conflicts. (The Parser page's SMILE_GRAMMAR is the
   right-recursive LL(1) form — same language, different shape.) */
const SEMANTIC_GRAMMAR = `PROG -> shuru_karo STMTS khatam
STMTS -> STMTS STMT | STMT
STMT -> DECL | ASG | IF | WHILE | FOR | PRINT | RET | rok bas | agla bas
DECL -> TYPE id rakho EXPR bas
ASG -> id rakho EXPR bas
PRINT -> batao EXPR bas
RET -> wapas_de EXPR bas
TYPE -> adad | desi | baat | khaali
BLOCK -> shuru STMTS banda
IF -> agar COND BLOCK | agar COND BLOCK warna BLOCK | agar COND BLOCK warna_agar COND BLOCK warna BLOCK
WHILE -> jab_tak COND BLOCK
FOR -> baar_baar id rakho EXPR bas COND bas id rakho EXPR BLOCK
COND -> EXPR REL EXPR
REL -> zyada | kam | barabar | zyada_ya_barabar | kam_ya_barabar | na_barabar
EXPR -> EXPR joro T | EXPR ghata T | T
T -> T guna F | T taqseem F | T bacha F | F
F -> id | num | str`;

/* default SDD — synthesized attribute `val` that EVALUATES expressions
   (joro=+, ghata=-, guna=*, taqseem=/, bacha=%), flowing bottom-up. Each
   statement carries the value of its expression; PROG.val is the last one.
   Control-flow statements (if/while/for) have no single value, so they give 0.
   Note: `id.val` is just the variable name (no symbol table yet), so doing
   arithmetic on identifiers gives a type error — use numbers. */
const DEFAULT_SEMANTICS = `PROG -> shuru_karo STMTS khatam { PROG.val = STMTS.val }
STMTS -> STMTS STMT { STMTS.val = STMT.val }
STMTS -> STMT { STMTS.val = STMT.val }
STMT -> DECL { STMT.val = DECL.val }
STMT -> ASG { STMT.val = ASG.val }
STMT -> PRINT { STMT.val = PRINT.val }
STMT -> RET { STMT.val = RET.val }
STMT -> IF { STMT.val = IF.val }
STMT -> WHILE { STMT.val = WHILE.val }
STMT -> FOR { STMT.val = FOR.val }
STMT -> rok bas { STMT.val = 0 }
STMT -> agla bas { STMT.val = 0 }
DECL -> TYPE id rakho EXPR bas { DECL.val = EXPR.val }
ASG -> id rakho EXPR bas { ASG.val = EXPR.val }
PRINT -> batao EXPR bas { PRINT.val = EXPR.val }
RET -> wapas_de EXPR bas { RET.val = EXPR.val }
EXPR -> EXPR joro T { EXPR.val = EXPR1.val + T.val }
EXPR -> EXPR ghata T { EXPR.val = EXPR1.val - T.val }
EXPR -> T { EXPR.val = T.val }
T -> T guna F { T.val = T1.val * F.val }
T -> T taqseem F { T.val = T1.val / F.val }
T -> T bacha F { T.val = T1.val % F.val }
T -> F { T.val = F.val }
F -> num { F.val = num.val }
F -> id { F.val = id.val }
F -> str { F.val = str.val }`;

const SEMANTIC_SAMPLES = [
  { name: "Print 2 joro 3", code: `shuru karo
batao 2 joro 3 bas
khatam` },
  { name: "Precedence", code: `shuru karo
batao 2 joro 3 guna 4 bas
khatam` },
  { name: "Declare value", code: `shuru karo
adad x rakho 10 ghata 4 bas
khatam` },
  { name: "Mixed", code: `shuru karo
batao 20 taqseem 4 joro 1 bas
khatam` },
];

/* render an attribute bag {val: 14, ...} as little badges */
function AttrBadges({ attrs }) {
  if (!attrs) return null;
  const keys = Object.keys(attrs).filter((k) => k !== "lexeme");
  if (!keys.length) return null;
  return (
    <span className="attr-badges">
      {keys.map((k) => (
        <span key={k} className="attr-badge">
          {k}=<b>{String(attrs[k])}</b>
        </span>
      ))}
    </span>
  );
}

/* recursive annotated-tree node — every node carries its attribute values */
function AnnotatedNode({ node }) {
  if (!node) return null;
  const hasChildren = node.children && node.children.length > 0;
  const label = node.terminal ? node.lexeme : node.symbol;
  return (
    <li className="tree-node">
      <span className={node.terminal ? "tree-label tree-terminal" : "tree-label tree-nonterminal"}>
        {label}
      </span>
      <AttrBadges attrs={node.attrs} />
      {hasChildren && (
        <ul className="tree-children">
          {node.children.map((c, i) => <AnnotatedNode key={i} node={c} />)}
        </ul>
      )}
    </li>
  );
}

function SemanticPage({ code, onBack }) {
  const [showGrammar, setShowGrammar] = useState(false);
  const [semantics, setSemantics] = useState(DEFAULT_SEMANTICS);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const networkError = (err) =>
    err.message.includes("Failed to fetch")
      ? "Backend server is not running! Start it with: uvicorn main:app --reload"
      : err.message;

  const runSemantics = async () => {
    if (!code.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await fetch(`${API_URL}/analyze_semantics`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: code, grammar: SEMANTIC_GRAMMAR, semantics }),
      });
      if (!response.ok) throw new Error(`Server error: ${response.status}`);
      setResult(await response.json());
    } catch (err) {
      setError(networkError(err));
    } finally {
      setLoading(false);
    }
  };

  const gErrors = (result && result.grammar_errors) || [];
  const rErrors = (result && result.rule_errors) || [];
  const semErrors = (result && result.semantic_errors) || [];

  return (
    <div className="analysis-page">
      <div className="analysis-page-header">
        <button className="btn btn-back" onClick={onBack}>
          <span className="back-arrow">←</span> Back to Home
        </button>
        <div className="analysis-page-title">
          <span className="analysis-icon" style={{ background: "linear-gradient(135deg, #ec4899, #db2777)" }}>🧠</span>
          <div>
            <h2>Semantic Analyzer — Syntax-Directed Translation</h2>
            <span className="analysis-subtitle">SDD on the SMILE grammar — annotate the parse tree with the expression value</span>
          </div>
        </div>
        <button className="btn btn-primary btn-run" onClick={runSemantics} disabled={loading || !code.trim()}>
          {loading ? "Analyzing…" : "▶ Annotate"}
        </button>
      </div>

      <div className="parser-layout">
        {/* ── Left: grammar + semantic rules + input ── */}
        <div className="parser-col parser-col-input">
          <div className="parse-section">
            <div className="parse-section-title">
              ① Grammar (rules & regulations)
              <span className="grammar-fixed-tag">built-in · fixed</span>
            </div>
            <div className="grammar-fixed-note">
              The semantic phase attaches rules to the SMILE grammar (left-recursive form, fixed in the project).
            </div>
            <button className="btn btn-load grammar-toggle" onClick={() => setShowGrammar((s) => !s)}>
              {showGrammar ? "▾ Hide grammar" : "▸ Show grammar"}
            </button>
            {showGrammar && <pre className="grammar-block">{SEMANTIC_GRAMMAR}</pre>}
          </div>

          <div className="parse-section">
            <div className="parse-section-title">② Semantic rules — the SDD (synthesized attributes)</div>
            <p className="sdd-hint">
              One rule per production: <code>HEAD.attr = expr</code>. The head is bare (<code>EXPR</code>),
              a child sharing the head's symbol is subscripted (<code>EXPR1</code>). The default SDD
              evaluates the expression value (<code>joro</code>=+, <code>guna</code>=×, …).
            </p>
            <textarea
              className="grammar-input"
              value={semantics}
              onChange={(e) => setSemantics(e.target.value)}
              spellCheck={false}
              rows={9}
            />
          </div>

          <div className="parse-section">
            <div className="parse-section-title">③ SMILE program <span className="grammar-fixed-tag">from editor</span></div>
            <pre className="grammar-block source-preview">{code}</pre>
          </div>
        </div>

        {/* ── Right: results ── */}
        <div className="parser-col parser-col-output">
          {error && <div className="error-banner">{error}</div>}

          {gErrors.length > 0 && (
            <div className="parse-section">
              <div className="parse-section-title">Grammar errors</div>
              {gErrors.map((e, i) => <div key={i} className="error-line">{e}</div>)}
            </div>
          )}

          {rErrors.length > 0 && (
            <div className="parse-section">
              <div className="parse-section-title">Semantic-rule errors</div>
              {rErrors.map((e, i) => <div key={i} className="error-line">{e}</div>)}
            </div>
          )}

          {result && result.used_sdd && result.used_sdd.length > 0 && (
            <div className="parse-section">
              <div className="parse-section-title">
                SDD Rules Used in This Program
                <span className="tree-note"> · only the {result.used_sdd.length} rules that fired for this input</span>
              </div>
              <table className="token-table compact sdd-table used-sdd-table">
                <thead>
                  <tr><th>#</th><th>Production</th><th>Semantic Rule</th></tr>
                </thead>
                <tbody>
                  {result.used_sdd.map((r) => (
                    <tr key={r.index}>
                      <td className="set-key">{r.index}</td>
                      <td className="token-value">{r.production}</td>
                      <td className="token-value sdd-rule">{r.rule}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {result && result.sdd && result.sdd.length > 0 && (
            <div className="parse-section">
              <div className="parse-section-title">
                Full Syntax-Directed Definition
                <span className="tree-note"> · all {result.sdd.length} rules (same for every program)</span>
              </div>
              <table className="token-table compact sdd-table">
                <thead>
                  <tr><th>#</th><th>Production</th><th>Semantic Rule</th></tr>
                </thead>
                <tbody>
                  {result.sdd.map((r) => {
                    const used = result.used_sdd && result.used_sdd.some((u) => u.index === r.index);
                    return (
                      <tr key={r.index} className={used ? "sdd-row-used" : ""}>
                        <td className="set-key">{r.index}</td>
                        <td className="token-value">{r.production}</td>
                        <td className="token-value sdd-rule">{r.rule}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {result && (
            <div className={`verdict ${result.accepted ? "verdict-accept" : "verdict-reject"}`}>
              {result.accepted ? "✓ ACCEPTED" : "✗ REJECTED"}
              {result.accepted && result.result && Object.keys(result.result).length > 0 && (
                <span className="verdict-value">
                  {" — " + Object.entries(result.result).map(([k, v]) => `${k} = ${v}`).join(", ")}
                </span>
              )}
            </div>
          )}

          {result && result.error && <div className="error-banner">{result.error}</div>}

          {semErrors.length > 0 && (
            <div className="parse-section">
              <div className="parse-section-title">Semantic errors (during evaluation)</div>
              {semErrors.map((e, i) => <div key={i} className="error-line">{e}</div>)}
            </div>
          )}

          {result && result.tree && (
            <div className="parse-section">
              <div className="parse-section-title">Annotated parse tree</div>
              <div className="tree-wrap">
                <ul className="tree-root">
                  <AnnotatedNode node={result.tree} />
                </ul>
              </div>
            </div>
          )}

          {result && result.steps && result.steps.length > 0 && (
            <div className="parse-section">
              <div className="parse-section-title">Attribute evaluation (bottom-up)</div>
              <table className="token-table compact">
                <thead>
                  <tr><th>#</th><th>Production</th><th>Result</th></tr>
                </thead>
                <tbody>
                  {result.steps.map((s, i) => (
                    <tr key={i}>
                      <td className="set-key">{i + 1}</td>
                      <td className="token-value">{s.production}</td>
                      <td className="token-value sdd-rule">{s.result}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════════
   3-Address Code Page (intermediate code generation)
   ══════════════════════════════════════════════ */
const TAC_SAMPLES = [
  { name: "Expression", code: `shuru karo
adad x rakho 2 joro 3 guna 4 bas
khatam` },
  { name: "If / else", code: `shuru karo
agar a kam b shuru
batao a bas
banda warna shuru
batao b bas
banda
khatam` },
  { name: "While loop", code: `shuru karo
adad i rakho 0 bas
jab tak i kam 5 shuru
batao i bas
i rakho i joro 1 bas
banda
khatam` },
  { name: "Mixed", code: `shuru karo
adad a rakho 5 bas
adad b rakho a guna 2 joro 1 bas
agar b zyada a shuru
batao b bas
banda
khatam` },
];

function ThreeAddrPage({ code, onBack }) {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const generate = async () => {
    if (!code.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await fetch(`${API_URL}/generate_tac`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code }),
      });
      if (!response.ok) throw new Error(`Server error: ${response.status}`);
      setResult(await response.json());
    } catch (err) {
      setError(
        err.message.includes("Failed to fetch")
          ? "Backend server is not running! Start it with: uvicorn main:app --reload"
          : err.message
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="analysis-page">
      <div className="analysis-page-header">
        <button className="btn btn-back" onClick={onBack}>
          <span className="back-arrow">←</span> Back to Home
        </button>
        <div className="analysis-page-title">
          <span className="analysis-icon" style={{ background: "linear-gradient(135deg, #0ea5e9, #0284c7)" }}>🧾</span>
          <div>
            <h2>3-Address Code — Intermediate Code Generation</h2>
            <span className="analysis-subtitle">Lower SMILE to TAC, shown as quadruples and triples</span>
          </div>
        </div>
        <button className="btn btn-primary btn-run" onClick={generate} disabled={loading || !code.trim()}>
          {loading ? "Generating…" : "▶ Generate TAC"}
        </button>
      </div>

      <div className="parser-layout">
        {/* ── Left: input ── */}
        <div className="parser-col parser-col-input">
          <div className="parse-section">
            <div className="parse-section-title">SMILE Program <span className="grammar-fixed-tag">from editor</span></div>
            <pre className="grammar-block source-preview">{code}</pre>
          </div>

          <div className="parse-section">
            <div className="parse-section-title">Three-Address Code Forms</div>
            <table className="token-table compact tac-types-table">
              <thead>
                <tr><th>Statement</th><th>Meaning</th></tr>
              </thead>
              <tbody>
                {result && result.types && result.types.map((t, i) => (
                  <tr key={i}>
                    <td className="token-value mono">{t.form}</td>
                    <td className="token-value">{t.meaning}</td>
                  </tr>
                ))}
                {!result && (
                  <>
                    <tr><td className="token-value mono">x = y op z</td><td className="token-value">Binary operation</td></tr>
                    <tr><td className="token-value mono">x = op y</td><td className="token-value">Unary operation</td></tr>
                    <tr><td className="token-value mono">x = y</td><td className="token-value">Assignment</td></tr>
                    <tr><td className="token-value mono">if x relop y goto L</td><td className="token-value">Conditional goto</td></tr>
                    <tr><td className="token-value mono">goto L</td><td className="token-value">Unconditional goto</td></tr>
                  </>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* ── Right: output ── */}
        <div className="parser-col parser-col-output">
          {error && <div className="error-banner">{error}</div>}
          {result && !result.ok && <div className="error-banner">{result.error}</div>}

          {result && result.ok && (
            <>
              <div className="verdict verdict-accept">
                ✓ TAC GENERATED
                <span className="verdict-value"> — {result.tac.length} instructions, {result.temps} temps, {result.labels} labels</span>
              </div>

              {/* Linear TAC */}
              <div className="parse-section">
                <div className="parse-section-title">Three-Address Code</div>
                <pre className="grammar-block tac-block">{result.tac.join("\n")}</pre>
              </div>

              {/* Quadruples */}
              <div className="parse-section">
                <div className="parse-section-title">Quadruples <span className="tree-note">· (op, arg1, arg2, result)</span></div>
                <div className="token-table-wrapper">
                  <table className="token-table compact">
                    <thead>
                      <tr><th>#</th><th>op</th><th>arg1</th><th>arg2</th><th>result</th></tr>
                    </thead>
                    <tbody>
                      {result.quadruples.map((q) => (
                        <tr key={q.index}>
                          <td className="set-key">{q.index}</td>
                          <td className="token-value mono tac-op">{q.op}</td>
                          <td className="token-value mono">{q.arg1}</td>
                          <td className="token-value mono">{q.arg2}</td>
                          <td className="token-value mono tac-res">{q.result}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Triples */}
              <div className="parse-section">
                <div className="parse-section-title">Triples <span className="tree-note">· (op, arg1, arg2) — temporaries become (index) references</span></div>
                <div className="token-table-wrapper">
                  <table className="token-table compact">
                    <thead>
                      <tr><th>#</th><th>op</th><th>arg1</th><th>arg2</th></tr>
                    </thead>
                    <tbody>
                      {result.triples.map((t) => (
                        <tr key={t.index}>
                          <td className="set-key">{t.index}</td>
                          <td className="token-value mono tac-op">{t.op}</td>
                          <td className="token-value mono">{t.arg1}</td>
                          <td className="token-value mono">{t.arg2}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}

          {!result && !error && (
            <div className="output-empty">
              <div className="empty-icon">🧾</div>
              <p>Write a SMILE program and click <strong>Generate TAC</strong> to see the three-address code, quadruples and triples.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════════
   Code Optimizer Page (local TAC optimizations)
   ══════════════════════════════════════════════ */
const OPTIMIZER_SAMPLES = [
  { name: "Constant folding", code: `shuru karo
adad x rakho 2 joro 3 guna 4 bas
khatam` },
  { name: "Common subexpr", code: `shuru karo
adad x rakho a joro b bas
adad y rakho a joro b bas
khatam` },
  { name: "Algebraic", code: `shuru karo
adad x rakho a guna 1 bas
adad y rakho b joro 0 bas
khatam` },
  { name: "No change", code: `shuru karo
batao a bas
khatam` },
];

function OptimizerPage({ code, onBack }) {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const run = async () => {
    if (!code.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await fetch(`${API_URL}/optimize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code }),
      });
      if (!response.ok) throw new Error(`Server error: ${response.status}`);
      setResult(await response.json());
    } catch (err) {
      setError(
        err.message.includes("Failed to fetch")
          ? "Backend server is not running! Start it with: uvicorn main:app --reload"
          : err.message
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="analysis-page">
      <div className="analysis-page-header">
        <button className="btn btn-back" onClick={onBack}>
          <span className="back-arrow">←</span> Back to Home
        </button>
        <div className="analysis-page-title">
          <span className="analysis-icon" style={{ background: "linear-gradient(135deg, #a855f7, #9333ea)" }}>🚀</span>
          <div>
            <h2>Code Optimizer — Local TAC Optimizations</h2>
            <span className="analysis-subtitle">Folding, propagation, CSE & dead-code elimination on the 3-address code</span>
          </div>
        </div>
        <button className="btn btn-primary btn-run" onClick={run} disabled={loading || !code.trim()}>
          {loading ? "Optimizing…" : "▶ Optimize"}
        </button>
      </div>

      <div className="parser-layout">
        {/* ── Left: input ── */}
        <div className="parser-col parser-col-input">
          <div className="parse-section">
            <div className="parse-section-title">SMILE Program <span className="grammar-fixed-tag">from editor</span></div>
            <pre className="grammar-block source-preview">{code}</pre>
          </div>

          <div className="parse-section">
            <div className="parse-section-title">Optimizations Applied</div>
            <p className="sdd-hint">
              Local, machine-independent optimizations: <code>constant folding</code>,
              <code>algebraic simplification</code>, <code>copy/constant propagation</code>,
              <code>common subexpression elimination</code>, <code>dead code elimination</code>.
              If nothing improves, the code stays the same.
            </p>
          </div>
        </div>

        {/* ── Right: output ── */}
        <div className="parser-col parser-col-output">
          {error && <div className="error-banner">{error}</div>}
          {result && !result.ok && <div className="error-banner">{result.error}</div>}

          {result && result.ok && (
            <>
              <div className={`verdict ${result.changed ? "verdict-accept" : "verdict-reject"}`}>
                {result.changed ? "✓ OPTIMIZED" : "○ NO OPTIMIZATION POSSIBLE"}
                <span className="verdict-value">
                  {result.changed
                    ? ` — ${result.optimizations.length} optimizations, ${result.original_count} → ${result.optimized_count} instructions`
                    : " — code is already optimal / unchanged"}
                </span>
              </div>

              {/* Before / After */}
              <div className="parse-section">
                <div className="parse-section-title">Before vs After</div>
                <div className="opt-compare">
                  <div className="opt-col">
                    <div className="opt-col-label">Original TAC ({result.original_count})</div>
                    <pre className="grammar-block tac-block">{result.original_tac.join("\n")}</pre>
                  </div>
                  <div className="opt-col">
                    <div className="opt-col-label opt-col-label-after">Optimized TAC ({result.optimized_count})</div>
                    <pre className="grammar-block tac-block opt-after-block">{result.optimized_tac.join("\n")}</pre>
                  </div>
                </div>
              </div>

              {/* Optimizations log */}
              {result.optimizations.length > 0 && (
                <div className="parse-section">
                  <div className="parse-section-title">Steps ({result.optimizations.length})</div>
                  <div className="token-table-wrapper">
                    <table className="token-table compact">
                      <thead>
                        <tr><th>#</th><th>Optimization</th><th>Change</th></tr>
                      </thead>
                      <tbody>
                        {result.optimizations.map((o, i) => (
                          <tr key={i}>
                            <td className="set-key">{i + 1}</td>
                            <td className="token-value opt-type">{o.type}</td>
                            <td className="token-value mono">{o.before} <span className="opt-arrow">→</span> {o.after}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Optimized quadruples */}
              <div className="parse-section">
                <div className="parse-section-title">Optimized Quadruples</div>
                <div className="token-table-wrapper">
                  <table className="token-table compact">
                    <thead>
                      <tr><th>#</th><th>op</th><th>arg1</th><th>arg2</th><th>result</th></tr>
                    </thead>
                    <tbody>
                      {result.quadruples.map((q) => (
                        <tr key={q.index}>
                          <td className="set-key">{q.index}</td>
                          <td className="token-value mono tac-op">{q.op}</td>
                          <td className="token-value mono">{q.arg1}</td>
                          <td className="token-value mono">{q.arg2}</td>
                          <td className="token-value mono tac-res">{q.result}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}

          {!result && !error && (
            <div className="output-empty">
              <div className="empty-icon">🚀</div>
              <p>Write a SMILE program and click <strong>Optimize</strong> to see the original vs optimized three-address code.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════════
   Code Generator Page (x86-64 assembly)
   ══════════════════════════════════════════════ */
const CODEGEN_SAMPLES = [
  { name: "Expression", code: `t1 = 3 * 4
t2 = 2 + t1
x = t2
print x` },
  { name: "While loop", code: `    i = 0
L1:
    if i < 3 goto L2
    goto L3
L2:
    print i
    t1 = i + 1
    i = t1
    goto L1
L3:` },
  { name: "If / else", code: `    if a > 5 goto L1
    goto L2
L1:
    print 1
    goto L3
L2:
    print 0
L3:` },
];

function CodeGenPage({ code, onBack }) {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);

  const copyAsm = () => {
    if (result && result.assembly) {
      navigator.clipboard.writeText(result.assembly.join("\n"));
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    }
  };

  const run = async () => {
    if (!code.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await fetch(`${API_URL}/generate_asm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code }),
      });
      if (!response.ok) throw new Error(`Server error: ${response.status}`);
      setResult(await response.json());
    } catch (err) {
      setError(
        err.message.includes("Failed to fetch")
          ? "Backend server is not running! Start it with: uvicorn main:app --reload"
          : err.message
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="analysis-page">
      <div className="analysis-page-header">
        <button className="btn btn-back" onClick={onBack}>
          <span className="back-arrow">←</span> Back to Home
        </button>
        <div className="analysis-page-title">
          <span className="analysis-icon" style={{ background: "linear-gradient(135deg, #14b8a6, #0d9488)" }}>💻</span>
          <div>
            <h2>Code Generator — 8051 Assembly</h2>
            <span className="analysis-subtitle">8051 (A51) assembly for Keil µVision, generated from the optimized code</span>
          </div>
        </div>
        <button className="btn btn-primary btn-run" onClick={run} disabled={loading || !code.trim()}>
          {loading ? "Generating…" : "▶ Generate Assembly"}
        </button>
      </div>

      <div className="parser-layout">
        {/* ── Left: source ── */}
        <div className="parser-col parser-col-input">
          <div className="parse-section">
            <div className="parse-section-title">SMILE Program <span className="grammar-fixed-tag">from editor</span></div>
            <pre className="grammar-block source-preview">{code}</pre>
          </div>
        </div>

        {/* ── Right: output ── */}
        <div className="parser-col parser-col-output">
          {error && <div className="error-banner">{error}</div>}
          {result && !result.ok && <div className="error-banner">{result.error}</div>}

          {result && result.ok && (
            <>
              {/* Generated assembly */}
              <div className="parse-section">
                <div className="parse-section-title">
                  8051 Assembly (Keil µVision, A51)
                  <button className="btn btn-load asm-copy-btn" onClick={copyAsm}>{copied ? "✓ Copied" : "⧉ Copy"}</button>
                </div>
                <p className="sdd-hint">
                  Copy into a <code>.a51</code> file in a Keil µVision project (8051 device, e.g. AT89C51),
                  build (F7), then Debug (Ctrl+F5) and watch A / B / RAM (var_* at 30H) in the debugger.
                  8-bit values (0–255). Full steps are in the comment header below.
                </p>
                <pre className="grammar-block asm-block">{result.assembly.join("\n")}</pre>
              </div>

              {/* TAC -> Assembly mapping */}
              <div className="parse-section">
                <div className="parse-section-title">Optimized TAC → Assembly</div>
                <div className="token-table-wrapper">
                  <table className="token-table compact">
                    <thead>
                      <tr><th>Three-Address Code</th><th>Assembly</th></tr>
                    </thead>
                    <tbody>
                      {result.mapping.map((m, i) => (
                        <tr key={i}>
                          <td className="token-value mono tac-op">{m.tac}</td>
                          <td className="token-value mono asm-cell">{m.asm.join("\n")}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}

          {!result && !error && (
            <div className="output-empty">
              <div className="empty-icon">💻</div>
              <p>Paste three-address code and click <strong>Generate Assembly</strong> to convert it into assembly.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════════
   Generic Analysis Page (Coming Soon)
   ══════════════════════════════════════════════ */
function AnalysisPage({ phase, code, onBack }) {
  return (
    <div className="analysis-page">
      <div className="analysis-page-header">
        <button className="btn btn-back" onClick={onBack}>
          <span className="back-arrow">←</span> Back to Home
        </button>
        <div className="analysis-page-title">
          <span className="analysis-icon" style={{ background: phase.gradient }}>{phase.icon}</span>
          <div>
            <h2>{phase.name}</h2>
            <span className="analysis-subtitle">{phase.description}</span>
          </div>
        </div>
        <div className="analysis-badge-coming">Coming Soon</div>
      </div>

      <div className="analysis-page-body">
        {/* Code Preview */}
        <div className="code-preview-section">
          <div className="code-preview-label">Source Code Input</div>
          <pre className="code-preview">{code}</pre>
        </div>

        <div className="coming-soon-container">
          <div className="coming-soon-icon" style={{ background: phase.gradient, boxShadow: `0 0 60px ${phase.glowColor}` }}>
            {phase.icon}
          </div>
          <h3>{phase.name}</h3>
          <p>This compiler phase is under development. Check back soon for the full {phase.name.toLowerCase()} implementation!</p>
          <div className="coming-soon-features">
            <div className="feature-dot" style={{ background: phase.color }}></div>
            <span>Will analyze: {phase.description.toLowerCase()}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════════
   Main App Component
   ══════════════════════════════════════════════ */
function App() {
  const [code, setCode] = useState(SAMPLE_PROGRAMS[0].code);
  const [currentPage, setCurrentPage] = useState("home"); // 'home' | phase.id
  const [hoveredPhase, setHoveredPhase] = useState(null);

  const lineCount = code.split("\n").length;

  const handleClear = () => {
    setCode("");
  };

  const loadSample = (sample) => {
    setCode(sample.code);
  };

  const openPhase = (phaseId) => {
    if (!code.trim()) return;                       // every phase uses the editor's code
    if (phaseId === "syntax" || phaseId === "parser") {
      setCurrentPage("parser");
      return;
    }
    if (phaseId === "lexical" || phaseId === "tokenizer") {
      setCurrentPage("tokenizer");
      return;
    }
    setCurrentPage(phaseId);                         // semantic / threeaddr / optimizer / codegen / others
  };

  const goHome = () => {
    setCurrentPage("home");
  };

  /* ── Render Analysis Pages ── */
  if (currentPage !== "home") {
    const phase = COMPILER_PHASES.find((p) => p.id === currentPage);

    return (
      <div className="app">
        <header className="header">
          <div className="header-logo">
            <div className="logo-icon">S</div>
            <div>
              <h1>SMILE Compiler</h1>
              <span className="tagline">Syntax Memes In Lahori English</span>
            </div>
          </div>
          <div className="header-badge">Compiler Construction Lab</div>
        </header>

        {currentPage === "tokenizer" ? (
          <TokenizerPage code={code} onBack={goHome} />
        ) : currentPage === "parser" ? (
          <ParserPage code={code} onBack={goHome} />
        ) : currentPage === "semantic" ? (
          <SemanticPage code={code} onBack={goHome} />
        ) : currentPage === "threeaddr" ? (
          <ThreeAddrPage code={code} onBack={goHome} />
        ) : currentPage === "optimizer" ? (
          <OptimizerPage code={code} onBack={goHome} />
        ) : currentPage === "codegen" ? (
          <CodeGenPage code={code} onBack={goHome} />
        ) : (
          <AnalysisPage phase={phase} code={code} onBack={goHome} />
        )}
      </div>
    );
  }

  /* ── Render Home Page ── */
  return (
    <div className="app">
      {/* ── Header ── */}
      <header className="header">
        <div className="header-logo">
          <div className="logo-icon">S</div>
          <div>
            <h1>SMILE Compiler</h1>
            <span className="tagline">Syntax Memes In Lahori English</span>
          </div>
        </div>
        <div className="header-badge">Compiler Construction Lab</div>
      </header>

      {/* ── Main Split Panel ── */}
      <main className="main-content">
        {/* ── Left: Editor Panel ── */}
        <section className="panel editor-panel">
          <div className="panel-header">
            <div className="panel-title">
              <span className="dot"></span>
              Source Code Editor
            </div>
            <div className="btn-group">
              {SAMPLE_PROGRAMS.map((s, i) => (
                <button
                  key={i}
                  className="btn btn-load"
                  onClick={() => loadSample(s)}
                  title={`Load: ${s.name}`}
                >
                  {s.name}
                </button>
              ))}
            </div>
          </div>

          <div className="panel-body editor-container">
            <textarea
              id="code-editor"
              className="code-editor"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder={`~ Apna SMILE code yahan likho ~\nshuru karo\n  batao "Hello duniya!" bas\nkhatam`}
              spellCheck={false}
              autoComplete="off"
              autoCorrect="off"
            />
          </div>

          <div className="editor-actions">
            <span className="line-count">
              {lineCount} line{lineCount !== 1 ? "s" : ""} &middot;{" "}
              {code.length} chars
            </span>
            <button
              className="btn btn-secondary"
              onClick={handleClear}
            >
              Clear
            </button>
          </div>
        </section>

        {/* ── Right: Compiler Phases Panel ── */}
        <section className="panel phases-panel">
          <div className="panel-header">
            <div className="panel-title">
              <span className="dot dot-purple"></span>
              Compiler Phases
            </div>
            <span className="phase-count">{COMPILER_PHASES.length} phases</span>
          </div>

          <div className="panel-body phases-body">
            <div className="phases-intro">
              <p>Write your SMILE code in the editor, then select a compiler phase to analyze it.</p>
            </div>

            <div className="phases-grid">
              {COMPILER_PHASES.map((phase, i) => (
                <button
                  key={phase.id}
                  id={`phase-${phase.id}`}
                  className={`phase-card ${hoveredPhase === phase.id ? "hovered" : ""}`}
                  onClick={() => openPhase(phase.id)}
                  onMouseEnter={() => setHoveredPhase(phase.id)}
                  onMouseLeave={() => setHoveredPhase(null)}
                  style={{
                    "--phase-color": phase.color,
                    "--phase-gradient": phase.gradient,
                    "--phase-glow": phase.glowColor,
                    animationDelay: `${i * 60}ms`,
                  }}
                  disabled={!code.trim()}
                >
                  <div className="phase-card-icon" style={{ background: phase.gradient, boxShadow: `0 0 20px ${phase.glowColor}` }}>
                    {phase.icon}
                  </div>
                  <div className="phase-card-content">
                    <h3>{phase.name}</h3>
                    <p>{phase.description}</p>
                  </div>
                  <div className="phase-card-arrow">→</div>
                </button>
              ))}
            </div>

            <div className="phases-pipeline">
              <div className="pipeline-label">Compilation Pipeline</div>
              <div className="pipeline-flow">
                {COMPILER_PHASES.map((phase, i) => (
                  <div key={phase.id} className="pipeline-step">
                    <div
                      className="pipeline-dot"
                      style={{ background: phase.gradient, boxShadow: `0 0 10px ${phase.glowColor}` }}
                    >
                      {phase.icon}
                    </div>
                    <span className="pipeline-name">{phase.name.split(" ")[0]}</span>
                    {i < COMPILER_PHASES.length - 1 && (
                      <div className="pipeline-connector"></div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
