#!/usr/bin/env python3
"""
  ██████╗ ██╗      █████╗ ███████╗███████╗
  ██╔══██╗██║     ██╔══██╗╚══███╔╝██╔════╝
  ██████╔╝██║     ███████║  ███╔╝ █████╗
  ██╔══██╗██║     ██╔══██║ ███╔╝  ██╔══╝
  ██████╔╝███████╗██║  ██║███████╗███████╗
  ╚═════╝ ╚══════╝╚═╝  ╚═╝╚══════╝╚══════╝

  Blaze v0.1 — Pipeline-First Programming Language
  ─────────────────────────────────────────────────
  ✓ Zero external dependencies   ✓ Python 3.8+
  ✓ Open Source (MIT)            ✓ One file. Run anywhere.

  Usage:
    python blaze.py              → Interactive REPL
    python blaze.py script.blz  → Run a file
    python blaze.py -e "1..10 | sum"  → Eval expression

  Language highlights:
    • Pipe-everything syntax  |
    • Auto-inferred types     no type annotations needed
    • Built-in statistics     mean, std, percentile...
    • Built-in data tables    load CSV, query, transform
    • Smart string interp     "Hello, {name}!"
    • Pattern matching        match / | arms
    • 60+ built-in functions  batteries truly included
"""

import sys, math, statistics, os, json, re
from typing import Any, Dict, List, Optional

VERSION = "0.1.0"

# ════════════════════════════════════════════════════════════════
#  TOKEN TYPES
# ════════════════════════════════════════════════════════════════

(NUM, STR, ID, KW, PIPE, ARROW, ASSIGN,
 PLUS, MINUS, MUL, DIV, MOD, POW,
 EQ, NEQ, LT, GT, LEQ, GEQ,
 LP, RP, LB, RB, LC, RC,
 COMMA, COLON, DOT, DOTDOT, SPREAD,
 NL, INDENT, DEDENT, EOF) = (
    'NUM','STR','ID','KW','PIPE','ARROW','ASSIGN',
    'PLUS','MINUS','MUL','DIV','MOD','POW',
    'EQ','NEQ','LT','GT','LEQ','GEQ',
    'LP','RP','LB','RB','LC','RC',
    'COMMA','COLON','DOT','DOTDOT','SPREAD',
    'NL','INDENT','DEDENT','EOF')

KWSET = {
    'if','then','elif','else','match','for','in','while',
    'true','false','null','and','or','not','return','fn',
    'show','load','use','from','as','break','continue',
    'sort','desc','asc','each','where','select',
    'group','by','agg','try','catch','import','table'
}

class Tok:
    __slots__ = ('t','v','ln')
    def __init__(self, t, v, ln=1): self.t=t; self.v=v; self.ln=ln
    def __repr__(self): return f"Tok({self.t!r},{self.v!r})"

# ════════════════════════════════════════════════════════════════
#  LEXER
# ════════════════════════════════════════════════════════════════

class BlazeError(Exception):
    def __init__(self, msg, line=0):
        self.msg=msg; self.line=line
        super().__init__(f"  ❌ Line {line}: {msg}" if line else f"  ❌ {msg}")

class Lexer:
    def __init__(self, src):
        self.src=src; self.i=0; self.ln=1

    def c(self, o=0):
        p=self.i+o
        return self.src[p] if p<len(self.src) else ''

    def eat(self):
        ch=self.src[self.i]; self.i+=1
        if ch=='\n': self.ln+=1
        return ch

    def tokenize(self):
        toks=[]; ind=[0]
        add = lambda t,v: toks.append(Tok(t,v,self.ln))

        while self.i < len(self.src):
            ch = self.c()

            if ch in ' \t\r': self.eat(); continue

            if ch == '#':
                while self.i<len(self.src) and self.c()!='\n': self.eat()
                continue

            if ch == '\n':
                self.eat(); add(NL,'\n')
                sp=0
                while self.i<len(self.src) and self.c()==' ': sp+=1; self.eat()
                if self.i>=len(self.src) or self.c() in '\n#': continue
                if sp>ind[-1]: ind.append(sp); add(INDENT,sp)
                elif sp<ind[-1]:
                    while ind[-1]>sp: ind.pop(); add(DEDENT,'')
                continue

            ln=self.ln

            # Strings with {interpolation}
            if ch in '"\'':
                q=self.eat(); parts=[]; cur=[]
                while self.i<len(self.src) and self.c()!=q:
                    x=self.eat()
                    if x=='\\':
                        n=self.eat()
                        cur.append({'n':'\n','t':'\t','\\':'\\','"':'"',"'":"'"}.get(n,n))
                    elif x=='{':
                        if cur: parts.append(('s',''.join(cur))); cur=[]
                        expr=[]; depth=1
                        while self.i<len(self.src) and depth>0:
                            nx=self.eat()
                            if nx=='{': depth+=1
                            elif nx=='}': depth-=1
                            if depth>0: expr.append(nx)
                        parts.append(('e',''.join(expr)))
                    else:
                        cur.append(x)
                if self.i<len(self.src): self.eat()
                if cur: parts.append(('s',''.join(cur)))
                toks.append(Tok(STR,parts,ln)); continue

            # Numbers
            if ch.isdigit():
                n=[]
                while self.i<len(self.src) and (self.c().isdigit() or
                      (self.c()=='.' and self.c(1)!='.')):
                    n.append(self.eat())
                x=''.join(n)
                toks.append(Tok(NUM,float(x) if '.' in x else int(x),ln)); continue

            # Identifiers / keywords
            if ch.isalpha() or ch=='_':
                n=[]
                while self.i<len(self.src) and (self.c().isalnum() or self.c() in '_?!'):
                    n.append(self.eat())
                x=''.join(n)
                toks.append(Tok(KW if x in KWSET else ID,x,ln)); continue

            # Multi-char operators
            matched=False
            for sym,tok in [('->',ARROW),('...',SPREAD),('..',DOTDOT),
                            ('==',EQ),('!=',NEQ),('<=',LEQ),('>=',GEQ),('**',POW)]:
                if self.src[self.i:self.i+len(sym)]==sym:
                    self.i+=len(sym); toks.append(Tok(tok,sym,ln)); matched=True; break
            if matched: continue

            # Single-char operators
            SING={'|':PIPE,'+':PLUS,'-':MINUS,'*':MUL,'/':DIV,
                  '%':MOD,'^':POW,'<':LT,'>':GT,'=':ASSIGN,
                  '(':LP,')':RP,'[':LB,']':RB,'{':LC,'}':RC,
                  ',':COMMA,':':COLON,'.':DOT}
            if ch in SING: toks.append(Tok(SING[ch],ch,ln)); self.eat(); continue

            raise BlazeError(f"Unexpected character '{ch}'", self.ln)

        while len(ind)>1: ind.pop(); toks.append(Tok(DEDENT,'',self.ln))
        toks.append(Tok(EOF,'',self.ln))
        return toks

# ════════════════════════════════════════════════════════════════
#  AST NODES
# ════════════════════════════════════════════════════════════════

class N: pass  # base node

class Num(N):
    def __init__(self,v): self.v=v
class Str(N):
    def __init__(self,p): self.parts=p   # [('s',str)|('e',src)]
class Bool(N):
    def __init__(self,v): self.v=v
class Null(N): pass

class List_(N):
    def __init__(self,items): self.items=items
class Dict_(N):
    def __init__(self,pairs): self.pairs=pairs
class Range(N):
    def __init__(self,s,e,step=None): self.s=s;self.e=e;self.step=step

class Var(N):
    def __init__(self,n): self.name=n
class Assign(N):
    def __init__(self,n,v): self.name=n;self.val=v
class BinOp(N):
    def __init__(self,op,l,r): self.op=op;self.l=l;self.r=r
class UnOp(N):
    def __init__(self,op,v): self.op=op;self.v=v

class Call(N):
    def __init__(self,fn,args,kw=None): self.fn=fn;self.args=args;self.kw=kw or {}
class Pipe(N):
    def __init__(self,l,r): self.l=l;self.r=r
class Index(N):
    def __init__(self,obj,idx): self.obj=obj;self.idx=idx
class Field(N):
    def __init__(self,obj,f): self.obj=obj;self.f=f

class Lambda(N):
    def __init__(self,p,b): self.params=p;self.body=b
class FuncDef(N):
    def __init__(self,n,p,b,d=None): self.name=n;self.params=p;self.body=b;self.defs=d or {}

class If(N):
    def __init__(self,c,t,ei,el): self.cond=c;self.then=t;self.elifs=ei;self.else_=el
class Match(N):
    def __init__(self,v,arms): self.v=v;self.arms=arms
class For(N):
    def __init__(self,var,it,b): self.var=var;self.iter=it;self.body=b
class While(N):
    def __init__(self,c,b): self.cond=c;self.body=b
class Return(N):
    def __init__(self,v): self.val=v
class Break(N): pass
class Continue(N): pass
class Block(N):
    def __init__(self,s): self.stmts=s
class ListComp(N):
    def __init__(self,e,v,it,c=None): self.expr=e;self.var=v;self.iter=it;self.cond=c
class DictComp(N):
    def __init__(self,k,v,var,it,c=None): self.k=k;self.v=v;self.var=var;self.iter=it;self.cond=c
class Show(N):
    def __init__(self,v): self.val=v
class Import(N):
    def __init__(self,m,a=None): self.mod=m;self.alias=a
class TryCatch(N):
    def __init__(self,b,v,h): self.body=b;self.var=v;self.handler=h

# ════════════════════════════════════════════════════════════════
#  PARSER
# ════════════════════════════════════════════════════════════════

class Parser:
    def __init__(self, toks):
        self.toks=toks; self.i=0

    def cur(self): return self.toks[self.i]
    def peek(self, o=1):
        p=self.i+o
        return self.toks[p] if p<len(self.toks) else Tok(EOF,'')

    def eat(self, *ts):
        t=self.cur()
        if ts and t.t not in ts and t.v not in ts:
            raise BlazeError(f"Expected {ts}, got {t.t!r}({t.v!r})", t.ln)
        self.i+=1; return t

    def skip(self):
        while self.cur().t in (NL,INDENT,DEDENT): self.i+=1

    def at(self, *x): t=self.cur(); return t.t in x or t.v in x
    def atnl(self): return self.at(NL,EOF,DEDENT)

    # ── program ──────────────────────────────────────────────

    def parse(self):
        stmts=[]
        while not self.at(EOF):
            while self.at(NL,INDENT,DEDENT): self.eat()
            if self.at(EOF): break
            s=self.stmt()
            if s: stmts.append(s)
        return Block(stmts)

    def stmt(self):
        t=self.cur()
        if t.t in (NL,INDENT,DEDENT): self.eat(); return None

        if t.v=='return':
            self.eat(); val=None if self.atnl() else self.expr()
            return Return(val)
        if t.v=='break': self.eat(); return Break()
        if t.v=='continue': self.eat(); return Continue()
        if t.v=='show': self.eat(); return Show(self.expr())
        if t.v=='print':
            self.eat()
            val = self.expr()
            return Call(Var('print'), [val], {})
        if t.v=='for': return self.for_stmt()
        if t.v=='while': return self.while_stmt()
        if t.v in ('use','import'): return self.import_stmt()
        if t.v=='try': return self.try_stmt()

        # function def: name(params) ->
        if t.t==ID and self.peek().t==LP:
            j=self.i; depth=0
            while j<len(self.toks):
                if self.toks[j].t==LP: depth+=1
                elif self.toks[j].t==RP:
                    depth-=1
                    if depth==0: break
                j+=1
            if j+1<len(self.toks) and self.toks[j+1].t==ARROW:
                return self.func_def()

        # assignment: name = expr
        if t.t==ID and self.peek().t==ASSIGN:
            name=self.eat(ID).v; self.eat(ASSIGN)
            return Assign(name, self.expr())

        return self.expr()

    def func_def(self):
        name=self.eat(ID).v; self.eat(LP)
        params,defs=self.param_list()
        self.eat(RP); self.eat(ARROW)
        body=self.func_body()
        return FuncDef(name,params,body,defs)

    def param_list(self):
        params=[]; defs={}
        while not self.at(RP,EOF):
            p=self.eat(ID).v; params.append(p)
            if self.at(ASSIGN): self.eat(ASSIGN); defs[p]=self.expr()
            if self.at(COMMA): self.eat(COMMA)
        return params,defs

    def func_body(self):
        while self.at(NL): self.eat()
        if self.at(INDENT):
            self.eat(INDENT); stmts=[]
            while not self.at(DEDENT,EOF):
                while self.at(NL): self.eat()
                if self.at(DEDENT,EOF): break
                s=self.stmt()
                if s: stmts.append(s)
            if self.at(DEDENT): self.eat(DEDENT)
            return Block(stmts)
        return self.expr()

    def indented_block(self):
        while self.at(NL): self.eat()
        self.eat(INDENT); stmts=[]
        while not self.at(DEDENT,EOF):
            while self.at(NL): self.eat()
            if self.at(DEDENT,EOF): break
            s=self.stmt()
            if s: stmts.append(s)
        if self.at(DEDENT): self.eat(DEDENT)
        return Block(stmts)

    def for_stmt(self):
        self.eat()  # for
        var=self.eat(ID).v; self.eat('in'); it=self.expr()
        self.eat(COLON)
        return For(var,it,self.indented_block())

    def while_stmt(self):
        self.eat()  # while
        c=self.expr(); self.eat(COLON)
        return While(c,self.indented_block())

    def import_stmt(self):
        self.eat(); mod=self.eat(ID).v; alias=None
        if self.at('as'): self.eat(); alias=self.eat(ID).v
        return Import(mod,alias)

    def try_stmt(self):
        self.eat(); self.eat(COLON)
        body=self.indented_block()
        while self.at(NL): self.eat()
        self.eat('catch'); var=None
        if self.at(LP): self.eat(LP); var=self.eat(ID).v; self.eat(RP)
        self.eat(COLON)
        return TryCatch(body,var,self.indented_block())

    # ── expressions ──────────────────────────────────────────

    def expr(self): return self.pipe_expr()

    def pipe_expr(self):
        l=self.or_expr()
        while self.at(PIPE):
            self.eat(PIPE); l=Pipe(l,self.pipe_rhs())
        return l

    def pipe_rhs(self):
        t=self.cur()
        # sort desc / sort asc  (without parens)
        if t.v=='sort' and self.peek().v in ('desc','asc'):
            self.eat(); order=self.eat().v
            return Call(Var('__sort__'),[],{'order':Str([('s',order)])})
        # bare identifier → treat as function to call on piped value
        if t.t in (ID,KW) and t.v not in ('if','match','for','while','true','false','null','and','or','not'):
            next_t = self.peek()
            # bare name: | sum, | upper, | reverse
            if next_t.t in (NL,EOF,PIPE,DEDENT,RP,RB,RC,COMMA):
                self.eat(); return Var(t.v)
            # fn with args/lambda: | join "-", | take 3, | map x -> x*2
            # Detect whether next tokens form args (STR/NUM literals or lambda pattern)
            if next_t.t in (STR, NUM) or next_t.t == ID:
                # Check for lambda: ID ID* ARROW
                j = self.i + 1
                while j < len(self.toks) and self.toks[j].t == ID:
                    j += 1
                is_lambda = j < len(self.toks) and self.toks[j].t == ARROW
                if is_lambda or next_t.t in (STR, NUM):
                    fname = self.eat().v
                    args = []
                    if is_lambda:
                        # | map x -> expr, | filter x -> expr
                        params = []
                        while not self.at(ARROW, NL, EOF):
                            params.append(self.eat(ID).v)
                        self.eat(ARROW)
                        args.append(Lambda(params, self.or_expr()))
                    else:
                        # | join "-", | take 3 — one literal arg
                        args.append(self.primary())
                        # additional literal args: | chunk 3
                        while self.cur().t in (STR, NUM) and not self.at(NL,EOF,PIPE,DEDENT):
                            args.append(self.primary())
                    return Call(Var(fname), args, {})
        return self.or_expr()

    def or_expr(self):
        l=self.and_expr()
        while self.at('or'):
            op=self.eat().v; l=BinOp(op,l,self.and_expr())
        return l

    def and_expr(self):
        l=self.not_expr()
        while self.at('and'):
            op=self.eat().v; l=BinOp(op,l,self.not_expr())
        return l

    def not_expr(self):
        if self.at('not'): self.eat(); return UnOp('not',self.not_expr())
        return self.cmp_expr()

    def cmp_expr(self):
        l=self.add_expr()
        while self.at(EQ,NEQ,LT,GT,LEQ,GEQ):
            op=self.eat().v; l=BinOp(op,l,self.add_expr())
        return l

    def add_expr(self):
        l=self.mul_expr()
        while self.at(PLUS,MINUS):
            op=self.eat().v; l=BinOp(op,l,self.mul_expr())
        return l

    def mul_expr(self):
        l=self.pow_expr()
        while self.at(MUL,DIV,MOD):
            op=self.eat().v; l=BinOp(op,l,self.pow_expr())
        return l

    def pow_expr(self):
        l=self.unary()
        while self.at(POW):
            op=self.eat().v; l=BinOp(op,l,self.unary())
        return l

    def unary(self):
        if self.at(MINUS): self.eat(); return UnOp('-',self.unary())
        return self.postfix()

    def postfix(self):
        n=self.primary()
        while True:
            if self.at(LP):
                self.eat(LP); args,kw=self.arg_list(); self.eat(RP)
                n=Call(n,args,kw)
            elif self.at(LB):
                self.eat(LB); idx=self.expr(); self.eat(RB)
                n=Index(n,idx)
            elif self.at(DOT):
                self.eat(DOT); f=self.eat(ID).v; n=Field(n,f)
            elif self.at(DOTDOT):
                # range: start..end
                self.eat(DOTDOT); e=self.primary()
                n=Range(n,e)
            else: break
        return n

    def arg_list(self):
        args=[]; kw={}
        while not self.at(RP,EOF):
            if self.cur().t==ID and self.peek().t==ASSIGN:
                k=self.eat(ID).v; self.eat(ASSIGN); kw[k]=self.expr()
            else:
                args.append(self.expr())
            if self.at(COMMA): self.eat(COMMA)
        return args,kw

    def primary(self):
        t=self.cur()

        if t.t==NUM: self.eat(); return Num(t.v)
        if t.t==STR: self.eat(); return Str(t.v)
        if t.v=='true': self.eat(); return Bool(True)
        if t.v=='false': self.eat(); return Bool(False)
        if t.v=='null': self.eat(); return Null()
        if t.v=='if': return self.if_expr()
        if t.v=='match': return self.match_expr()
        if t.t==LP: return self.paren_or_lambda()
        if t.t==LB: return self.list_expr()
        if t.t==LC: return self.dict_expr()

        # Identifier
        if t.t in (ID,KW):
            self.eat(); n=Var(t.v)
            # Lambda: x -> body (must be here before postfix swallows it)
            if self.at(ARROW):
                self.eat(ARROW); return Lambda([t.v],self.expr())
            return n

        # Numeric range starting with number: 1..10
        raise BlazeError(f"Unexpected token {t.t!r} ({t.v!r})", t.ln)

    def if_expr(self):
        self.eat()  # if
        c=self.or_expr()
        if self.at('then'):
            # inline: if x then y elif z then w else v
            self.eat(); th=self.expr(); ei=[]
            while self.at('elif'):
                self.eat(); ec=self.or_expr(); self.eat('then'); eb=self.expr()
                ei.append((ec,eb))
            el=None
            if self.at('else'): self.eat(); el=self.expr()
            return If(c,th,ei,el)
        else:
            self.eat(COLON)
            th=self.indented_block(); ei=[]
            while self.at(NL): self.eat()
            while self.at('elif'):
                self.eat(); ec=self.or_expr(); self.eat(COLON)
                eb=self.indented_block(); ei.append((ec,eb))
                while self.at(NL): self.eat()
            el=None
            if self.at('else'):
                self.eat(); self.eat(COLON); el=self.indented_block()
            return If(c,th,ei,el)

    def match_expr(self):
        self.eat()  # match
        v=self.expr()
        while self.at(NL): self.eat()
        # Accept optional INDENT (arms may be indented or at same level)
        indented = self.at(INDENT)
        if indented: self.eat(INDENT)
        arms=[]
        while True:
            while self.at(NL): self.eat()
            if self.at(DEDENT,EOF): break
            if not self.at(PIPE): break  # no more arms
            self.eat(PIPE)
            t=self.cur()
            if t.v=='_': self.eat(); pat=('_',None)
            elif t.t in (EQ,NEQ,LT,GT,LEQ,GEQ):
                op=self.eat().v; pv=self.expr(); pat=(op,pv)
            else:
                pv=self.expr(); pat=('==',pv)
            self.eat(ARROW); body=self.expr()
            arms.append((pat,body))
        if indented and self.at(DEDENT): self.eat(DEDENT)
        return Match(v,arms)

    def paren_or_lambda(self):
        self.eat(LP)
        # Look ahead: (params) -> = lambda
        j=self.i; depth=1
        while j<len(self.toks) and depth>0:
            if self.toks[j].t==LP: depth+=1
            elif self.toks[j].t==RP: depth-=1
            j+=1
        if j<len(self.toks) and self.toks[j].t==ARROW:
            params=[]
            while not self.at(RP,EOF):
                params.append(self.eat(ID).v)
                if self.at(COMMA): self.eat(COMMA)
            self.eat(RP); self.eat(ARROW)
            return Lambda(params,self.expr())
        e=self.expr(); self.eat(RP); return e

    def list_expr(self):
        self.eat(LB)
        while self.at(NL): self.eat()
        if self.at(RB): self.eat(RB); return List_([])
        first=self.expr()
        # [1..10] — Range already parsed by postfix, unwrap from list
        if isinstance(first, Range) and self.at(RB):
            self.eat(RB); return first
        # List comprehension: [expr for x in iter if cond]
        if self.at('for'):
            self.eat(); var=self.eat(ID).v; self.eat('in'); it=self.expr()
            c=None
            if self.at('if'): self.eat(); c=self.expr()
            self.eat(RB); return ListComp(first,var,it,c)
        items=[first]
        while self.at(COMMA):
            self.eat(COMMA)
            while self.at(NL): self.eat()
            if self.at(RB): break
            items.append(self.expr())
        while self.at(NL): self.eat()
        self.eat(RB); return List_(items)

    def dict_expr(self):
        self.eat(LC)
        while self.at(NL): self.eat()
        if self.at(RC): self.eat(RC); return Dict_([])
        k=self.dict_key(); self.eat(COLON); v=self.expr()
        if self.at('for'):
            self.eat(); var=self.eat(ID).v; self.eat('in'); it=self.expr()
            c=None
            if self.at('if'): self.eat(); c=self.expr()
            self.eat(RC); return DictComp(k,v,var,it,c)
        pairs=[(k,v)]
        while self.at(COMMA):
            self.eat(COMMA)
            while self.at(NL): self.eat()
            if self.at(RC): break
            k2=self.dict_key(); self.eat(COLON); v2=self.expr()
            pairs.append((k2,v2))
        while self.at(NL): self.eat()
        self.eat(RC); return Dict_(pairs)

    def dict_key(self):
        t=self.cur()
        if t.t==ID: self.eat(); return Str([('s',t.v)])
        return self.expr()

# ════════════════════════════════════════════════════════════════
#  RUNTIME
# ════════════════════════════════════════════════════════════════

class BlazeFunc:
    def __init__(self,name,params,defs,body,env):
        self.name=name; self.params=params; self.defs=defs
        self.body=body; self.env=env
    def __repr__(self): return f"<fn {self.name}>"

class BlazeBuiltin:
    def __init__(self,name,fn): self.name=name; self.fn=fn
    def __call__(self,*a,**kw): return self.fn(*a,**kw)
    def __repr__(self): return f"<builtin {self.name}>"

class BlazeTable:
    def __init__(self,data): self.data=data  # {col:[values]}
    @property
    def cols(self): return list(self.data.keys())
    @property
    def nrows(self):
        if not self.data: return 0
        return len(next(iter(self.data.values())))
    def to_records(self):
        cols=self.cols
        return [dict(zip(cols,[self.data[c][i] for c in cols])) for i in range(self.nrows)]
    def __repr__(self):
        if not self.data: return "Table (empty)"
        cols=self.cols
        w={c:max(len(str(c)),max((len(str(v)) for v in self.data[c]),default=0)) for c in cols}
        hdr='  '.join(str(c).ljust(w[c]) for c in cols)
        sep='  '.join('─'*w[c] for c in cols)
        rows=[hdr,sep]
        for i in range(min(self.nrows,20)):
            rows.append('  '.join(str(self.data[c][i]).ljust(w[c]) for c in cols))
        if self.nrows>20: rows.append(f"  ... ({self.nrows} rows total)")
        return '\n'.join(rows)

class Ret(Exception):
    def __init__(self,v): self.v=v
class Brk(Exception): pass
class Cont(Exception): pass

class Env:
    def __init__(self,p=None): self.v={}; self.parent=p
    def get(self,n):
        if n in self.v: return self.v[n]
        if self.parent: return self.parent.get(n)
        raise BlazeError(f"Undefined: '{n}'")
    def set(self,n,v): self.v[n]=v
    def has(self,n): return n in self.v or (bool(self.parent) and self.parent.has(n))

# ════════════════════════════════════════════════════════════════
#  BUILT-IN LIBRARY (60+ functions)
# ════════════════════════════════════════════════════════════════

_interp = None  # set by Interpreter

def _call(fn, args):
    if isinstance(fn, BlazeBuiltin): return fn(*args)
    if isinstance(fn, BlazeFunc): return _interp.call_fn(fn, args)
    if callable(fn): return fn(*args)
    raise BlazeError(f"Not callable: {type(fn).__name__}")

def _lst(v, name=''):
    if isinstance(v,list): return v
    if isinstance(v,range): return list(v)
    if isinstance(v,str): return list(v)
    raise BlazeError(f"{name}: expected list, got {type(v).__name__}")

def _nums(v,n=''): return [x for x in _lst(v,n) if isinstance(x,(int,float))]
def _nonempty(v,n): lst=_nums(v,n); assert lst,f"{n}: empty list"; return lst

def br(v):
    """Pretty-print a Blaze value"""
    if v is None: return 'null'
    if isinstance(v,bool): return 'true' if v else 'false'
    if isinstance(v,float):
        return str(int(v))+'.0' if v==int(v) else f"{v:.6g}"
    if isinstance(v,list):
        return '['+', '.join(br(x) for x in v)+']'
    if isinstance(v,dict):
        return '{'+', '.join(f"{k}: {br(val)}" for k,val in v.items())+'}'
    if isinstance(v,(BlazeTable,BlazeFunc,BlazeBuiltin)):
        return repr(v)
    return str(v)

def make_stdlib():
    bb = lambda n,f: BlazeBuiltin(n,f)

    def hist(v, bins=10):
        lst=_nums(v,'hist')
        if not lst: return
        mn,mx=min(lst),max(lst)
        if mn==mx: mn-=0.5;mx+=0.5
        bw=(mx-mn)/bins; counts=[0]*bins
        for x in lst:
            bi=min(int((x-mn)/bw),bins-1); counts[bi]+=1
        mxc=max(counts); W=35
        print(f"\n  Histogram  n={len(lst)}  bins={bins}")
        print(f"  {'─'*55}")
        for i,c in enumerate(counts):
            lo=mn+i*bw; bar='█'*int(c/mxc*W) if mxc else ''
            print(f"  {lo:8.2f} ┤ {bar:<{W}} {c}")
        print(f"  {'─'*55}")
        return v

    def scatter(xs,ys,W=60,H=18):
        xv=_nums(xs,'scatter'); yv=_nums(ys,'scatter')
        if not xv: return
        grid=[[' ']*W for _ in range(H)]
        xmn,xmx=min(xv),max(xv); ymn,ymx=min(yv),max(yv)
        if xmn==xmx: xmx=xmn+1
        if ymn==ymx: ymx=ymn+1
        for x,y in zip(xv,yv):
            xi=int((x-xmn)/(xmx-xmn)*(W-1))
            yi=H-1-int((y-ymn)/(ymx-ymn)*(H-1))
            grid[yi][xi]='●'
        print(f"\n  Scatter  n={len(xv)}")
        print(f"  {ymx:8.2f} ┐")
        for row in grid: print(f"  {'':8} │{''.join(row)}│")
        print(f"  {ymn:8.2f} ┘")
        print(f"  {'':9}{'└'+('─'*(W-1))+'┘'}")
        print(f"  {'':9}{xmn:<{W//2}.2f}{xmx:>{W//2}.2f}")
        return [xs,ys]

    def linreg(xs,ys):
        xv=_nums(xs,'linreg'); yv=_nums(ys,'linreg')
        n=len(xv)
        if n<2: raise BlazeError("linreg needs ≥ 2 points")
        sx=sum(xv);sy=sum(yv);sxy=sum(a*b for a,b in zip(xv,yv));sx2=sum(x*x for x in xv)
        m=(n*sxy-sx*sy)/(n*sx2-sx*sx); b=(sy-m*sx)/n
        return {'slope':round(m,6),'intercept':round(b,6)}

    def corr(a,b):
        av=_nums(a,'corr'); bv=_nums(b,'corr')
        n=len(av); ma=sum(av)/n; mb=sum(bv)/n
        num=sum((x-ma)*(y-mb) for x,y in zip(av,bv))
        da=math.sqrt(sum((x-ma)**2 for x in av))
        db=math.sqrt(sum((y-mb)**2 for y in bv))
        return round(num/(da*db),6) if da and db else 0.0

    def describe(v):
        if isinstance(v,BlazeTable):
            out={}
            for col in v.cols:
                vals=[x for x in v.data[col] if isinstance(x,(int,float))]
                if vals:
                    out[col]={'count':len(vals),'mean':round(sum(vals)/len(vals),4),
                              'std':round(statistics.stdev(vals) if len(vals)>1 else 0,4),
                              'min':min(vals),'max':max(vals)}
            return out
        lst=_nums(v,'describe')
        if not lst: return {}
        return {'count':len(lst),'mean':round(sum(lst)/len(lst),4),
                'std':round(statistics.stdev(lst) if len(lst)>1 else 0,4),
                'min':min(lst),'max':max(lst),'median':statistics.median(lst)}

    return {
        # ── IO ──
        'print':   bb('print', lambda *a: print(' '.join(
                        a[0] if len(a)==1 and isinstance(a[0],str) else
                        br(x) if not isinstance(x,str) else x for x in a)) or None),
        'input':   bb('input', lambda p='': input(str(p))),
        'show':    bb('show',  lambda v: print(repr(v)) or v if isinstance(v,BlazeTable)
                              else print(br(v)) or v),

        # ── List ──
        'map':      bb('map',    lambda lst,fn: [_call(fn,[x]) for x in _lst(lst,'map')]),
        'filter':   bb('filter', lambda lst,fn: [x for x in _lst(lst,'filter') if _call(fn,[x])]),
        'reduce':   bb('reduce', lambda lst,fn,init=None: (
                        lambda l: l[0] if not init and not l[1:] else
                        __import__('functools').reduce(lambda a,b:_call(fn,[a,b]),l,init) if init is not None else
                        __import__('functools').reduce(lambda a,b:_call(fn,[a,b]),l))(_lst(lst,'reduce'))),
        'each':     bb('each',   lambda lst,fn: [_call(fn,[x]) for x in _lst(lst,'each')] and lst),
        'find':     bb('find',   lambda lst,fn: next((x for x in _lst(lst,'find') if _call(fn,[x])),None)),
        'any':      bb('any',    lambda lst,fn=None: any(_call(fn,[x]) for x in _lst(lst)) if fn else any(_lst(lst))),
        'all':      bb('all',    lambda lst,fn=None: all(_call(fn,[x]) for x in _lst(lst)) if fn else all(_lst(lst))),
        'sort':     bb('sort',   lambda v,key=None,order='asc':
                        sorted(_lst(v,'sort'),key=lambda x:_call(key,[x]) if key else x,
                               reverse=(order=='desc'))),
        'reverse':  bb('reverse',lambda v: list(reversed(_lst(v,'reverse')))),
        'unique':   bb('unique', lambda v: list(dict.fromkeys(_lst(v,'unique')))),
        'flat':     bb('flat',   lambda v,d=1: [i for s in _lst(v,'flat')
                                  for i in (s if isinstance(s,list) else [s])]),
        'take':     bb('take',   lambda v,n: _lst(v,'take')[:int(n)]),
        'skip':     bb('skip',   lambda v,n: _lst(v,'skip')[int(n):]),
        'first':    bb('first',  lambda v: _lst(v,'first')[0] if _lst(v,'first') else None),
        'last':     bb('last',   lambda v: _lst(v,'last')[-1] if _lst(v,'last') else None),
        'chunk':    bb('chunk',  lambda v,n: [_lst(v,'chunk')[i:i+int(n)] for i in range(0,len(_lst(v)),int(n))]),
        'zip':      bb('zip',    lambda *ls: [list(t) for t in zip(*[_lst(l) for l in ls])]),
        'enumerate':bb('enumerate',lambda v: [[i,x] for i,x in enumerate(_lst(v,'enumerate'))]),
        'range':    bb('range',  lambda s,e=None,st=1: list(range(int(s),int(e)+1,int(st))) if e else list(range(int(s)))),
        'group_by': bb('group_by',lambda lst,fn: (lambda d: [d.setdefault(str(_call(fn,[x])),[]).append(x) or d for x in _lst(lst)] and d)({})),
        'frequency':bb('frequency',lambda v: (lambda d: [d.__setitem__(str(x),d.get(str(x),0)+1) for x in _lst(v)] and d)({})),
        'partition':bb('partition',lambda lst,fn: [[x for x in _lst(lst) if _call(fn,[x])],[x for x in _lst(lst) if not _call(fn,[x])]]),
        'sample':   bb('sample', lambda v,n=1: __import__('random').sample(_lst(v,'sample'),min(int(n),len(_lst(v,'sample'))))),
        'shuffle':  bb('shuffle',lambda v: (lambda l: __import__('random').shuffle(l) or l)(list(_lst(v,'shuffle')))),
        'count_where':bb('count_where',lambda lst,fn: sum(1 for x in _lst(lst) if _call(fn,[x]))),
        'sort_by':  bb('sort_by',lambda lst,fn,order='asc': sorted(_lst(lst,'sort_by'),key=lambda x:_call(fn,[x]),reverse=(order=='desc'))),
        'cumsum':   bb('cumsum', lambda v: (lambda l:[sum(l[:i+1]) for i in range(len(l))])(_nums(v,'cumsum'))),
        'diff':     bb('diff',   lambda v: (lambda l:[l[i+1]-l[i] for i in range(len(l)-1)])(_nums(v,'diff'))),

        # ── Math ──
        'sum':    bb('sum',    lambda v: sum(_nums(v,'sum'))),
        'min':    bb('min',    lambda *a: min(_nums(a[0],'min')) if len(a)==1 else min(a)),
        'max':    bb('max',    lambda *a: max(_nums(a[0],'max')) if len(a)==1 else max(a)),
        'argmax': bb('argmax', lambda v: (lambda l: l.index(max(l)))(_nums(v,'argmax'))),
        'argmin': bb('argmin', lambda v: (lambda l: l.index(min(l)))(_nums(v,'argmin'))),
        'abs':   bb('abs',   lambda v: abs(v)),
        'floor': bb('floor', lambda v: math.floor(v)),
        'ceil':  bb('ceil',  lambda v: math.ceil(v)),
        'round': bb('round', lambda v,n=0: round(float(v),int(n))),
        'sqrt':  bb('sqrt',  lambda v: math.sqrt(v)),
        'log':   bb('log',   lambda v,b=math.e: math.log(v,b)),
        'sin':   bb('sin',   lambda v: math.sin(v)),
        'cos':   bb('cos',   lambda v: math.cos(v)),
        'tan':   bb('tan',   lambda v: math.tan(v)),
        'exp':   bb('exp',   lambda v: math.exp(v)),
        'pow':   bb('pow',   lambda b,e: b**e),
        'pi':    math.pi,
        'e':     math.e,
        'inf':   math.inf,
        'tau':   math.tau,
        'clamp': bb('clamp', lambda v,lo,hi: max(lo,min(hi,v))),
        'lerp':  bb('lerp',  lambda a,b,t: a+(b-a)*t),

        # ── Stats ──
        'len':        bb('len',      lambda v: len(_lst(v,'len')) if isinstance(v,(list,str)) else
                                              v.nrows if isinstance(v,BlazeTable) else len(v)),
        'count':      bb('count',    lambda v: len(_lst(v,'count')) if isinstance(v,list) else
                                               v.nrows if isinstance(v,BlazeTable) else 1),
        'mean':       bb('mean',     lambda v: sum(_nonempty(v,'mean'))/len(_nonempty(v,'mean'))),
        'median':     bb('median',   lambda v: statistics.median(_nonempty(v,'median'))),
        'std':        bb('std',      lambda v: statistics.stdev(_nonempty(v,'std')) if len(_nonempty(v,'std'))>1 else 0.0),
        'var':        bb('var',      lambda v: statistics.variance(_nonempty(v,'var')) if len(_nonempty(v,'var'))>1 else 0.0),
        'percentile': bb('percentile',lambda v,p: (lambda l,p:l[int(p/100*(len(l)-1))])(sorted(_nums(v,'percentile')),p)),
        'normalize':  bb('normalize',lambda v: (lambda l,mn,mx:[(x-mn)/(mx-mn) if mx!=mn else 0.0 for x in l])(_nums(v,'normalize'),min(_nums(v)),max(_nums(v)))),
        'zscore':     bb('zscore',   lambda v: (lambda l,m,s:[(x-m)/s if s else 0.0 for x in l])(_nums(v,'zscore'),sum(_nums(v))/len(_nums(v)),statistics.stdev(_nums(v)) if len(_nums(v))>1 else 1)),
        'corr':       bb('corr',     corr),
        'linreg':     bb('linreg',   linreg),
        'describe':   bb('describe', describe),
        'hist':       bb('hist',     hist),
        'scatter':    bb('scatter',  scatter),

        # ── String ──
        'upper':      bb('upper',      lambda v: str(v).upper()),
        'lower':      bb('lower',      lambda v: str(v).lower()),
        'trim':       bb('trim',       lambda v: str(v).strip()),
        'ltrim':      bb('ltrim',      lambda v: str(v).lstrip()),
        'rtrim':      bb('rtrim',      lambda v: str(v).rstrip()),
        'split':      bb('split',      lambda v,sep=None: str(v).split(sep)),
        'join':       bb('join',       lambda v,sep='': sep.join(str(x) for x in _lst(v,'join'))),
        'replace':    bb('replace',    lambda v,old,new: str(v).replace(str(old),str(new))),
        'contains':   bb('contains',   lambda v,s: str(s) in str(v)),
        'starts_with':bb('starts_with',lambda v,s: str(v).startswith(str(s))),
        'ends_with':  bb('ends_with',  lambda v,s: str(v).endswith(str(s))),
        'lines':      bb('lines',      lambda v: str(v).split('\n')),
        'words':      bb('words',      lambda v: str(v).split()),
        'pad_left':   bb('pad_left',   lambda v,n,c=' ': str(v).rjust(int(n),str(c))),
        'pad_right':  bb('pad_right',  lambda v,n,c=' ': str(v).ljust(int(n),str(c))),
        'repeat':     bb('repeat',     lambda v,n: str(v)*int(n)),

        # ── Type ──
        'type':  bb('type',  lambda v: ('bool' if isinstance(v,bool) else 'int' if isinstance(v,int) else 'float' if isinstance(v,float) else 'string' if isinstance(v,str) else 'list' if isinstance(v,list) else 'map' if isinstance(v,dict) else 'table' if isinstance(v,BlazeTable) else 'fn' if callable(v) else 'null' if v is None else 'unknown')),
        'str':   bb('str',   lambda v: br(v) if not isinstance(v,str) else v),
        'int':   bb('int',   lambda v: int(v)),
        'float': bb('float', lambda v: float(v)),
        'bool':  bb('bool',  lambda v: bool(v)),
        'list':  bb('list',  lambda v: list(v) if not isinstance(v,list) else v),

        # ── Dict/Map ──
        'keys':   bb('keys',   lambda v: list(v.keys()) if isinstance(v,dict) else v.cols if isinstance(v,BlazeTable) else []),
        'values': bb('values', lambda v: list(v.values()) if isinstance(v,dict) else []),
        'items':  bb('items',  lambda v: [[k,val] for k,val in v.items()] if isinstance(v,dict) else []),
        'has':    bb('has',    lambda v,k: k in v if isinstance(v,(dict,list,str)) else False),
        'get':    bb('get',    lambda v,k,d=None: v.get(k,d) if isinstance(v,dict) else d),
        'merge':  bb('merge',  lambda *dicts: dict(i for d in dicts for i in (d.items() if isinstance(d,dict) else []))),
        'pick':   bb('pick',   lambda d,*ks: {k:d[k] for k in ks if k in d} if isinstance(d,dict) else {}),
        'omit':   bb('omit',   lambda d,*ks: {k:v for k,v in d.items() if k not in ks} if isinstance(d,dict) else {}),

        # ── Table ──
        'table':  bb('table',  lambda v: BlazeTable(v) if isinstance(v,dict) else
                                          BlazeTable({k:[r.get(k) for r in v] for k in v[0]}) if isinstance(v,list) and v and isinstance(v[0],dict) else v),
        'cols':   bb('cols',   lambda v: v.cols if isinstance(v,BlazeTable) else []),
        'rows':   bb('rows',   lambda v: v.to_records() if isinstance(v,BlazeTable) else v),
        'head':   bb('head',   lambda v,n=5: BlazeTable({c:v.data[c][:int(n)] for c in v.cols}) if isinstance(v,BlazeTable) else _lst(v)[:int(n)]),
        'tail':   bb('tail',   lambda v,n=5: BlazeTable({c:v.data[c][-int(n):] for c in v.cols}) if isinstance(v,BlazeTable) else _lst(v)[-int(n):]),
        'where':  bb('where',  lambda t,fn: (BlazeTable({k:[t.data[k][i] for i in range(t.nrows) if _call(fn,[t.to_records()[i]])] for k in t.cols}) if isinstance(t,BlazeTable) else [x for x in _lst(t) if _call(fn,[x])])),
        'select_cols': bb('select_cols', lambda t,*cs: BlazeTable({c:t.data[c] for c in cs if c in t.data}) if isinstance(t,BlazeTable) else t),

        # ── File I/O ──
        'load':      bb('load',      lambda p: (lambda rows,cols:
                          BlazeTable({c:[(lambda v:int(v) if v.lstrip('-').isdigit() else float(v) if re.match(r'^-?\d+\.?\d*$',v) else v)(r[c]) for r in rows] for c in cols}))(
                          list(__import__('csv').DictReader(open(str(p)))),
                          list(__import__('csv').DictReader(open(str(p))).fieldnames or []))),
        'load_json': bb('load_json', lambda p: json.load(open(str(p)))),
        'save_json': bb('save_json', lambda v,p: json.dump(
                          v.to_records() if isinstance(v,BlazeTable) else v,open(str(p),'w'),indent=2) or True),
        'read_file': bb('read_file', lambda p: open(str(p)).read()),
        'write_file':bb('write_file',lambda p,v: open(str(p),'w').write(str(v)) or True),

        # ── Misc ──
        'identity': bb('identity', lambda v: v),
        'not':      bb('not',      lambda v: not v),
        'assert_eq':bb('assert_eq',lambda a,b,msg='Assertion failed': None if a==b else (_ for _ in ()).throw(BlazeError(f"{msg}: {br(a)} != {br(b)}"))),
        '__sort__': bb('__sort__', lambda v,order='asc': sorted(_lst(v,'sort'),reverse=(order=='desc'))),
    }

# ════════════════════════════════════════════════════════════════
#  INTERPRETER
# ════════════════════════════════════════════════════════════════

class Interpreter:
    def __init__(self):
        global _interp
        self.genv = Env()
        for k,v in make_stdlib().items():
            self.genv.set(k,v)
        _interp = self

    def run(self, src, env=None):
        toks = Lexer(src).tokenize()
        ast  = Parser(toks).parse()
        return self.ev(ast, env or self.genv)

    def ev(self, node, env):
        if node is None: return None
        T = type(node)

        if T is Num:  return node.v
        if T is Bool: return node.v
        if T is Null: return None

        if T is Str:
            out=[]
            for kind,val in node.parts:
                if kind=='s': out.append(val)
                else:
                    try:
                        r=self.run(val.strip(), env)
                        out.append(br(r) if not isinstance(r,str) else r)
                    except Exception as ex:
                        out.append(f"{{ERR:{ex}}}")
            return ''.join(out)

        if T is Var:
            return env.get(node.name)

        if T is Assign:
            v=self.ev(node.val,env); env.set(node.name,v); return v

        if T is Block:
            r=None
            for s in node.stmts: r=self.ev(s,env)
            return r

        if T is BinOp:
            l=self.ev(node.l,env)
            if node.op=='and': return l and self.ev(node.r,env)
            if node.op=='or':  return l or  self.ev(node.r,env)
            r=self.ev(node.r,env)
            op=node.op
            if op=='+':
                if isinstance(l,list) and isinstance(r,list): return l+r
                if isinstance(l,str) or isinstance(r,str): return str(l)+str(r)
                return l+r
            if op=='-': return l-r
            if op=='*':
                if isinstance(l,str) and isinstance(r,int): return l*r
                return l*r
            if op=='/':  return l/r if r else (math.inf if l>0 else -math.inf)
            if op=='%':  return l%r
            if op in ('^','**'): return l**r
            if op=='//': return l//r
            if op=='==': return l==r
            if op=='!=': return l!=r
            if op=='<':  return l<r
            if op=='>':  return l>r
            if op=='<=': return l<=r
            if op=='>=': return l>=r
            raise BlazeError(f"Unknown op: {op}")

        if T is UnOp:
            v=self.ev(node.v,env)
            if node.op=='-':   return -v
            if node.op=='not': return not v

        if T is List_:
            return [self.ev(i,env) for i in node.items]

        if T is Dict_:
            return {self.ev(k,env):self.ev(v,env) for k,v in node.pairs}

        if T is Range:
            s=int(self.ev(node.s,env)); e=int(self.ev(node.e,env))
            st=int(self.ev(node.step,env)) if node.step else 1
            return list(range(s,e+1,st))

        if T is Index:
            obj=self.ev(node.obj,env); idx=self.ev(node.idx,env)
            try:
                if isinstance(obj,(list,str)): return obj[int(idx)]
                if isinstance(obj,dict): return obj[idx]
                if isinstance(obj,BlazeTable):
                    if isinstance(idx,str): return obj.data.get(idx)
                    return obj.to_records()[int(idx)]
            except (IndexError,KeyError):
                raise BlazeError(f"Index error: {idx}")

        if T is Field:
            obj=self.ev(node.obj,env)
            if isinstance(obj,dict): return obj.get(node.f)
            if isinstance(obj,BlazeTable): return obj.data.get(node.f)
            raise BlazeError(f"No field '{node.f}' on {type(obj).__name__}")

        if T is Lambda:
            return BlazeFunc('<lambda>',node.params,{},node.body,env)

        if T is FuncDef:
            defs={k:self.ev(v,env) for k,v in node.defs.items()}
            fn=BlazeFunc(node.name,node.params,defs,node.body,env)
            env.set(node.name,fn); return fn

        if T is Call:
            fn=self.ev(node.fn,env)
            args=[self.ev(a,env) for a in node.args]
            kw={k:self.ev(v,env) for k,v in node.kw.items()}
            return self.call(fn,args,kw)

        if T is Pipe:
            left=self.ev(node.l,env)
            return self.pipe(left,node.r,env)

        if T is If:
            if self.ev(node.cond,env):
                return self.ev(node.then,Env(env))
            for ec,eb in node.elifs:
                if self.ev(ec,env): return self.ev(eb,Env(env))
            return self.ev(node.else_,Env(env)) if node.else_ else None

        if T is Match:
            v=self.ev(node.v,env)
            for (op,pn),body in node.arms:
                if op=='_': return self.ev(body,Env(env))
                pv=self.ev(pn,env)
                hit={'==':v==pv,'!=':v!=pv,'<':v<pv,'>':v>pv,'<=':v<=pv,'>=':v>=pv}.get(op,False)
                if hit: return self.ev(body,Env(env))
            return None

        if T is For:
            it=self.ev(node.iter,env)
            items=it if isinstance(it,list) else list(it) if isinstance(it,range) else [it]
            last=None
            for item in items:
                sub=Env(env); sub.set(node.var,item)
                try: last=self.ev(node.body,sub)
                except Brk: break
                except Cont: continue
            return last

        if T is While:
            last=None
            while self.ev(node.cond,env):
                sub=Env(env)
                try: last=self.ev(node.body,sub)
                except Brk: break
                except Cont: continue
            return last

        if T is Return: raise Ret(self.ev(node.val,env) if node.val else None)
        if T is Break: raise Brk()
        if T is Continue: raise Cont()

        if T is Show:
            v=self.ev(node.val,env)
            print(repr(v) if isinstance(v,BlazeTable) else br(v))
            return v

        if T is Import:
            import importlib
            try:
                mod=importlib.import_module(node.mod)
                env.set(node.alias or node.mod.split('.')[-1], mod)
            except ImportError:
                raise BlazeError(f"Cannot import '{node.mod}'")
            return None

        if T is TryCatch:
            try: return self.ev(node.body,Env(env))
            except BlazeError as ex:
                sub=Env(env)
                if node.var: sub.set(node.var,str(ex))
                return self.ev(node.handler,sub)
            except Exception as ex:
                sub=Env(env)
                if node.var: sub.set(node.var,str(ex))
                return self.ev(node.handler,sub)

        if T is ListComp:
            it=self.ev(node.iter,env)
            items=it if isinstance(it,list) else list(it)
            out=[]
            for x in items:
                sub=Env(env); sub.set(node.var,x)
                if node.cond and not self.ev(node.cond,sub): continue
                out.append(self.ev(node.expr,sub))
            return out

        if T is DictComp:
            it=self.ev(node.iter,env)
            items=it if isinstance(it,list) else list(it)
            out={}
            for x in items:
                sub=Env(env); sub.set(node.var,x)
                if node.cond and not self.ev(node.cond,sub): continue
                out[self.ev(node.k,sub)]=self.ev(node.v,sub)
            return out

        raise BlazeError(f"Unknown node: {type(node).__name__}")

    def pipe(self, left, rhs, env):
        """Evaluate  left | rhs"""
        # bare name: left | sum
        if isinstance(rhs,Var):
            try:
                fn=env.get(rhs.name)
                if callable(fn) or isinstance(fn,(BlazeFunc,BlazeBuiltin)):
                    return self.call(fn,[left],{})
            except BlazeError:
                pass
            # fall-through to eval as expression (shouldn't be reached normally)

        # call with left injected: left | take(3)
        if isinstance(rhs,Call):
            fn=self.ev(rhs.fn,env)
            args=[left]+[self.ev(a,env) for a in rhs.args]
            kw={k:self.ev(v,env) for k,v in rhs.kw.items()}
            return self.call(fn,args,kw)

        # lambda: left | x -> x * 2
        if isinstance(rhs,Lambda):
            fn=BlazeFunc('<lambda>',rhs.params,{},rhs.body,env)
            return self.call_fn(fn,[left])

        # fallback: evaluate rhs as value then call
        v=self.ev(rhs,env)
        if callable(v) or isinstance(v,(BlazeFunc,BlazeBuiltin)):
            return self.call(v,[left],{})
        return v

    def call(self, fn, args, kw):
        if fn is None: raise BlazeError("Cannot call null")
        if isinstance(fn,BlazeBuiltin):
            try: return fn(*args,**kw)
            except TypeError as e: raise BlazeError(str(e))
        if isinstance(fn,BlazeFunc): return self.call_fn(fn,args,kw)
        if callable(fn): return fn(*args,**kw)
        raise BlazeError(f"Not callable: {br(fn)}")

    def call_fn(self, fn, args, kw=None):
        if kw is None: kw={}
        loc=Env(fn.env)
        for i,p in enumerate(fn.params):
            if i<len(args): loc.set(p,args[i])
            elif p in kw: loc.set(p,kw[p])
            elif p in fn.defs: loc.set(p,fn.defs[p])
            else: raise BlazeError(f"Missing arg '{p}' in call to {fn.name}")
        try: return self.ev(fn.body,loc)
        except Ret as r: return r.v

# ════════════════════════════════════════════════════════════════
#  REPL
# ════════════════════════════════════════════════════════════════

HELP = """
  🔥 BLAZE QUICK REFERENCE
  ═══════════════════════════════════════════════════════════

  VARIABLES       x = 42           name = "Uday"
  ARITHMETIC      2 + 3 * 4        10 ^ 2      7 % 3
  STRINGS         "Hello, {name}!" "hi" | upper
  BOOLEANS        true  false  not  and  or
  NULL            null

  LISTS           data = [1, 2, 3, 4, 5]
  RANGES          1..10  →  [1, 2, 3, ..., 10]
  DICTS           p = {name: "Alice", age: 30}

  FUNCTIONS       double(x) -> x * 2
  LAMBDAS         sq = x -> x * x
  MULTI-LINE      fn stats(data) ->
                    {mean: data | mean, std: data | std}

  PIPES           [1..100] | filter x -> x%2==0 | sum
                  "hello world" | upper | words | reverse | join "-"

  IF EXPR         if score >= 90 then "A" elif score >= 80 then "B" else "C"
  MATCH           match status | "ok" -> 1 | "fail" -> 0 | _ -> -1
  FOR             for x in 1..5: print "{x} squared = {x*x}"
  WHILE           while n > 0: n = n - 1

  LIST COMP       [x*x for x in 1..10 if x % 2 == 0]
  DICT COMP       {x: x*x for x in 1..5}

  STRING INTERP   "Pi is approximately {pi | round(4)}"
  TRY/CATCH       try: risky() catch (e): print e

  ─── BUILT-IN FUNCTIONS ──────────────────────────────────

  Math:     sum  min  max  abs  round  sqrt  log  sin  cos
  Lists:    map  filter  reduce  sort  unique  take  skip
            first  last  flat  zip  chunk  each  find
            cumsum  diff  partition  sort_by  frequency
  Stats:    mean  median  std  var  percentile
            normalize  zscore  corr  linreg  describe
  Display:  show  hist  scatter
  Strings:  upper  lower  trim  split  join  replace
            contains  starts_with  ends_with  words  lines
  Tables:   table  load  cols  rows  head  tail  where
            select_cols  describe
  Type:     type  str  int  float  bool  list

  ─── EXAMPLES ────────────────────────────────────────────

  # Project Euler #1
  [1..999] | filter x -> x % 3 == 0 or x % 5 == 0 | sum

  # Stats pipeline
  data = [2,4,1,8,5,9,3,6,7,10]
  data | sort | describe

  # Word frequency
  text = "the quick brown fox jumps over the lazy dog"
  text | words | frequency

  # Fibonacci
  fib(n) -> if n <= 1 then n else fib(n-1) + fib(n-2)
  [fib(x) for x in 0..12]

  Type 'exit' to quit.
"""

def repl():
    interp = Interpreter()
    print(f"""
  ╔══════════════════════════════════════════════════════╗
  ║  🔥  Blaze v{VERSION}  —  Pipeline-First Language          ║
  ║  Zero-setup · Zero-boilerplate · Maximum productivity ║
  ╚══════════════════════════════════════════════════════╝
  Type 'help' for a quick guide, 'exit' to quit.
""")
    buf=[]; cont=False
    while True:
        try:
            line=input('... ' if cont else 'blaze> ')
        except (EOFError,KeyboardInterrupt):
            print("\n  Goodbye! 🔥"); break

        if line.strip()=='exit': print("  Goodbye! 🔥"); break
        if line.strip()=='help': print(HELP); continue
        if line.strip()=='':
            if cont:
                src='\n'.join(buf); buf=[]; cont=False
                try:
                    r=interp.run(src)
                    if r is not None and not isinstance(r,(BlazeFunc,BlazeBuiltin)):
                        print(f"  → {br(r)}")
                except Exception as ex: print(ex)
            continue

        buf.append(line)
        if line.rstrip().endswith(':') or line.rstrip().endswith('->'):
            cont=True; continue
        if not cont:
            src=line; buf=[]
            try:
                r=interp.run(src)
                if r is not None and not isinstance(r,(BlazeFunc,BlazeBuiltin)):
                    print(f"  → {br(r)}")
            except Ret as ret:
                if ret.v is not None: print(f"  → {br(ret.v)}")
            except Exception as ex:
                print(ex)

# ════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ════════════════════════════════════════════════════════════════

def main():
    args=sys.argv[1:]
    if not args: repl(); return
    if args[0]=='--version': print(f"Blaze {VERSION}"); return
    if args[0]=='--help': print(HELP); return
    if args[0]=='-e':
        src=' '.join(args[1:])
        interp=Interpreter()
        try:
            r=interp.run(src)
            if r is not None: print(br(r))
        except Exception as ex: print(ex); sys.exit(1)
        return
    # run file — execute statement-by-statement, auto-print expression results
    path=args[0]
    try:
        src=open(path).read()
    except FileNotFoundError:
        print(f"  ❌ File not found: {path}"); sys.exit(1)
    interp=Interpreter()
    try:
        toks=Lexer(src).tokenize()
        ast=Parser(toks).parse()
        # ast is a Block; run each stmt and print expr results
        for stmt in ast.stmts:
            try:
                r=interp.ev(stmt,interp.genv)
                # Print non-null, non-function expression results (assignments/defs stay quiet)
                if r is not None and not isinstance(r,(BlazeFunc,BlazeBuiltin)):
                    if not isinstance(stmt,(Assign,FuncDef)):
                        print(br(r))
            except Ret: pass
    except Exception as ex: print(ex); sys.exit(1)

if __name__=='__main__':
    main()
