"""
SMILE Compiler — FastAPI Backend
Provides a /tokenize endpoint that accepts SMILE source code and returns tokens.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from lexer import tokenize
from parsers import parse as parse_smile
from parsers import analyze_grammar, DEFAULT_GRAMMAR_TEXT
from semantic import analyze_semantics, DEFAULT_SEMANTIC_TEXT
from threeaddr import generate_tac
from optimizer import optimize as optimize_code
from codegen import generate_asm

app = FastAPI(
    title="SMILE Compiler API",
    description="Backend API for the SMILE (Syntax Memes In Lahori English) tokenizer",
    version="1.0.0",
)

# Allow React dev server to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TokenizeRequest(BaseModel):
    code: str


class TokenizeResponse(BaseModel):
    tokens: list
    errors: list
    total_tokens: int
    total_errors: int


@app.get("/")
def root():
    return {"message": "SMILE Compiler API is running 🚀"}


@app.post("/tokenize", response_model=TokenizeResponse)
def tokenize_code(request: TokenizeRequest):
    """Tokenize SMILE source code and return the list of tokens."""
    result = tokenize(request.code)
    return result


class ParseRequest(BaseModel):
    code: str
    method: str                      # "lr0" | "slr" | "ll1"
    grammar: str = DEFAULT_GRAMMAR_TEXT
    reduced: bool = True             # build tables from only the productions the code uses


class GrammarRequest(BaseModel):
    grammar: str


@app.post("/parse")
def parse_code(request: ParseRequest):
    """Parse SMILE source with the chosen parser (LR(0) / SLR(1) / LL(1)).
    When `reduced` is set, FIRST/FOLLOW, the parse table and item sets are built
    from the sub-grammar of just the productions this program uses."""
    return parse_smile(request.code, request.method, request.grammar, request.reduced)


@app.post("/validate_grammar")
def validate_grammar(request: GrammarRequest):
    """Validate a user-supplied grammar: report errors, warnings and the
    detected start symbol / terminals / nonterminals."""
    return analyze_grammar(request.grammar)


class SemanticRequest(BaseModel):
    code: str
    grammar: str = DEFAULT_GRAMMAR_TEXT
    semantics: str = DEFAULT_SEMANTIC_TEXT


@app.post("/analyze_semantics")
def analyze_semantics_endpoint(request: SemanticRequest):
    """Semantic phase: validate the grammar + its semantic rules (SDD), parse
    the input, and return the annotated parse tree built by evaluating the
    synthesized attributes bottom-up."""
    return analyze_semantics(request.code, request.grammar, request.semantics)


class TACRequest(BaseModel):
    code: str


@app.post("/generate_tac")
def generate_tac_endpoint(request: TACRequest):
    """Intermediate-code phase: generate three-address code from SMILE source,
    returned as linear TAC plus quadruple and triple tables."""
    return generate_tac(request.code)


@app.post("/optimize")
def optimize_endpoint(request: TACRequest):
    """Optimization phase: generate TAC from SMILE source, then apply local
    optimizations (folding, propagation, CSE, dead-code) and report what changed."""
    return optimize_code(request.code)


@app.post("/generate_asm")
def generate_asm_endpoint(request: TACRequest):
    """Code-generation phase: SMILE source -> optimized TAC -> x86-64 assembly
    (NASM, Linux), with the expected program output for testing."""
    return generate_asm(request.code)


@app.get("/health")
def health():
    return {"status": "ok"}
