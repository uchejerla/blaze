import { useState, useCallback, useEffect, useRef } from "react";

// ════════════════════════════════════════════════════
//  BLAZE INTERPRETER  —  JS runtime for the showcase
// ════════════════════════════════════════════════════

const KEYS = new Set([
  'if','then','elif','else','match','for','in','while',
  'and','or','not','true','false','null','return','break',
  'continue','desc','asc'
]);

function tokenize(src) {
  const toks = []; let i = 0; const n = src.length;
  const ch = (o=0) => (i+o < n ? src[i+o] : '');
  const isD = c => c >= '0' && c <= '9';
  const isA = c => /[a-zA-Z_]/.test(c);

  while (i < n) {
    const c = ch();
    if (c === ' ' || c === '\t' || c === '\r') { i++; continue; }
    if (c === '#') { while (i < n && ch() !== '\n') i++; continue; }
    if (c === '\n') { toks.push({t:'NL'}); i++; continue; }
    const prev = toks[toks.length-1];
    const prevIsVal = prev && ['NUM','RP','RB','ID'].includes(prev.t);
    if (isD(c) || (c==='-' && !prevIsVal && isD(ch(1)))) {
      let s = c==='-' ? (i++,'-') : '';
      while (i<n && (isD(ch()) || (ch()==='.' && ch(1)!=='.'))) s += src[i++];
      toks.push({t:'NUM', v:parseFloat(s)}); continue;
    }
    if (c==='"' || c==="'") {
      const q=src[i++]; let s='';
      while (i<n && src[i]!==q) {
        if (src[i]==='\\') { i++; s+=({n:'\n',t:'\t',r:'\r'}[src[i]]??src[i]); i++; }
        else s+=src[i++];
      }
      i++; toks.push({t:'STR',v:s}); continue;
    }
    if (isA(c)) {
      let s=''; while (i<n && /[a-zA-Z0-9_]/.test(ch())) s+=src[i++];
      toks.push({t:KEYS.has(s)?'KW':'ID',v:s}); continue;
    }
    const two=src.slice(i,i+2);
    const T2={'..':'DD','->':'ARR','==':'EQ','!=':'NEQ','<=':'LEQ','>=':'GEQ','**':'POW'};
    if (T2[two]) { toks.push({t:T2[two]}); i+=2; continue; }
    const T1={'|':'PIPE','+':'ADD','-':'SUB','*':'MUL','/':'DIV','%':'MOD',
               '^':'POW','<':'LT','>':'GT','=':'ASS',
               '(':'LP',')':'RP','[':'LB',']':'RB','{':'LC','}':'RC',
               ',':'COM',':':'COL','.':'DOT'};
    if (T1[c]) { toks.push({t:T1[c]}); i++; continue; }
    i++;
  }
  toks.push({t:'EOF'}); return toks;
}

function parseStrParts(s) {
  const parts=[]; let i=0; let lit='';
  while (i<s.length) {
    if (s[i]==='{') {
      if (lit) parts.push({k:'s',v:lit}); lit='';
      let depth=1, expr=''; i++;
      while (i<s.length && depth>0) {
        if (s[i]==='{') depth++;
        if (s[i]==='}') { if(--depth===0){i++;break;} }
        expr+=s[i++];
      }
      parts.push({k:'e',v:expr});
    } else lit+=s[i++];
  }
  if (lit) parts.push({k:'s',v:lit});
  return parts;
}

class BlazeEnv {
  constructor(parent=null) { this.s={}; this.p=parent; }
  get(n) {
    if (n in this.s) return this.s[n];
    if (this.p) return this.p.get(n);
    throw new Error(`Undefined: '${n}'`);
  }
  set(n,v) { if (!this._upd(n,v)) this.s[n]=v; }
  _upd(n,v) { if (n in this.s){this.s[n]=v;return true;} return this.p?this.p._upd(n,v):false; }
  def(n,v) { this.s[n]=v; }
  child() { return new BlazeEnv(this); }
}

class Parser {
  constructor(toks) { this.t=toks; this.i=0; }
  cur() { return this.t[this.i]||{t:'EOF'}; }
  peek(n=1) { return this.t[this.i+n]||{t:'EOF'}; }
  at(...vs) { const c=this.cur(); return vs.some(v=>c.t===v||c.v===v); }
  eat(v) {
    const c=this.cur();
    if (v && c.t!==v && c.v!==v) throw new Error(`Expected ${v}, got ${c.t}(${c.v})`);
    this.i++; return c;
  }
  nl() { while(this.at('NL')) this.eat(); }

  parse() {
    const ss=[]; this.nl();
    while(!this.at('EOF')) { if(this.at('NL')){this.eat();continue;} ss.push(this.stmt()); }
    return {T:'Prog',ss};
  }

  stmt() {
    const c=this.cur();
    if (c.t==='ID' && c.v==='print') { this.eat(); return {T:'Print',e:this.expr()}; }
    if (c.t==='ID' && this.peek().t==='LP') {
      const saved=this.i;
      try {
        const nm=this.eat('ID').v; this.eat('LP');
        const ps=[];
        while(!this.at('RP')) { if(this.at('COM')){this.eat();continue;} ps.push(this.eat('ID').v); }
        this.eat('RP');
        if (this.at('ARR')) { this.eat('ARR'); this.nl(); return {T:'FnDef',nm,ps,body:this.expr()}; }
        this.i=saved;
      } catch(e) { this.i=saved; }
    }
    if (c.t==='ID' && this.peek().t==='ASS') {
      const nm=this.eat('ID').v; this.eat('ASS');
      return {T:'Asgn',nm,e:this.expr()};
    }
    return {T:'Expr',e:this.expr()};
  }

  expr() { return this.pipe(); }
  pipe() {
    let left=this.or();
    while(this.at('PIPE')) { this.eat('PIPE'); left={T:'Pipe',l:left,r:this.pipeRhs()}; }
    return left;
  }
  pipeRhs() {
    const c=this.cur();
    if (c.t==='ID'&&c.v==='sort'&&(this.peek().v==='desc'||this.peek().v==='asc')) {
      this.eat(); const ord=this.eat().v;
      return {T:'Call',fn:{T:'Var',n:'sort'},as:[],kw:{order:ord}};
    }
    if (c.t==='ID'&&this.peek().t==='ID'&&this.peek(2).t==='ARR') {
      const fn=this.eat().v; const p=this.eat().v; this.eat('ARR');
      return {T:'Call',fn:{T:'Var',n:fn},as:[{T:'Lam',ps:[p],body:this.expr()}],kw:{}};
    }
    if ((c.t==='ID'||c.t==='KW')&&['EOF','NL','PIPE','RP','RB','RC','COM'].includes(this.peek().t)) {
      this.eat(); return {T:'Var',n:c.v};
    }
    return this.or();
  }
  or()  { let l=this.and(); while(this.at('or')){this.eat();l={T:'Bin',op:'or',l,r:this.and()};} return l; }
  and() { let l=this.nt(); while(this.at('and')){this.eat();l={T:'Bin',op:'and',l,r:this.nt()};} return l; }
  nt()  { if(this.at('not')){this.eat();return{T:'Un',op:'not',e:this.cmp()};} return this.cmp(); }
  cmp() {
    let l=this.add();
    const M={'EQ':'==','NEQ':'!=','LT':'<','GT':'>','LEQ':'<=','GEQ':'>='};
    while(M[this.cur().t]){const op=M[this.eat().t];l={T:'Bin',op,l,r:this.add()};}
    return l;
  }
  add() { let l=this.mul(); while(this.at('ADD')||this.at('SUB')){const op=this.eat().t;l={T:'Bin',op,l,r:this.mul()};} return l; }
  mul() { let l=this.un(); while(this.at('MUL')||this.at('DIV')||this.at('MOD')||this.at('POW')){const op=this.eat().t;l={T:'Bin',op,l,r:this.un()};} return l; }
  un()  { if(this.at('SUB')){this.eat();return{T:'Un',op:'-',e:this.post()};} return this.post(); }
  post() {
    let n=this.prim();
    while(true) {
      if(this.at('LP')){this.eat('LP');const{as,kw}=this.args();this.eat('RP');n={T:'Call',fn:n,as,kw};}
      else if(this.at('LB')){this.eat('LB');const idx=this.expr();this.eat('RB');n={T:'Idx',o:n,idx};}
      else if(this.at('DOT')){this.eat('DOT');const f=this.eat('ID').v;n={T:'Field',o:n,f};}
      else if(this.at('DD')){this.eat('DD');const e=this.prim();n={T:'Range',s:n,e};}
      else break;
    }
    return n;
  }
  args() {
    const as=[],kw={};
    while(!this.at('RP')) {
      if(this.at('COM')){this.eat();continue;}
      if(this.cur().t==='ID'&&this.peek().t==='ASS'){const k=this.eat('ID').v;this.eat('ASS');kw[k]=this.expr();}
      else as.push(this.expr());
    }
    return {as,kw};
  }
  prim() {
    const c=this.cur();
    if(c.t==='NUM'){this.eat();return{T:'Num',v:c.v};}
    if(c.v==='true'){this.eat();return{T:'Bool',v:true};}
    if(c.v==='false'){this.eat();return{T:'Bool',v:false};}
    if(c.v==='null'){this.eat();return{T:'Null'};}
    if(c.t==='STR'){this.eat();return{T:'Str',parts:parseStrParts(c.v)};}
    if(c.v==='if'){
      this.eat(); const cond=this.or(); this.eat('then'); const then_=this.expr();
      let else_=null; if(this.at('else')){this.eat();else_=this.expr();}
      return{T:'If',cond,then_,else_};
    }
    if(c.v==='match'){
      this.eat(); const v=this.or(); this.nl(); const arms=[];
      while(this.at('PIPE')) {
        this.eat('PIPE'); let pat;
        const d=this.cur();
        if(d.v==='_'){this.eat();pat={op:'_'};}
        else if(['GEQ','LEQ','GT','LT','EQ','NEQ'].includes(d.t)){const op=this.eat().t;const pv=this.or();pat={op,pv};}
        else{const pv=this.or();pat={op:'EQ',pv};}
        this.eat('ARR');const body=this.expr();arms.push({pat,body});this.nl();
      }
      return{T:'Match',v,arms};
    }
    if(c.t==='LB'){
      this.eat('LB');this.nl();
      if(this.at('RB')){this.eat('RB');return{T:'List',items:[]};}
      const first=this.expr();
      if(first.T==='Range'&&this.at('RB')){this.eat('RB');return first;}
      if(this.at('for')){
        this.eat();const v=this.eat('ID').v;this.eat('in');const it=this.expr();
        let cond=null;if(this.at('if')){this.eat();cond=this.expr();}
        this.eat('RB');return{T:'LC',e:first,v,it,cond};
      }
      const items=[first];
      while(this.at('COM')){this.eat();this.nl();if(this.at('RB'))break;items.push(this.expr());}
      this.nl();this.eat('RB');return{T:'List',items};
    }
    if(c.t==='LC'){
      this.eat('LC');this.nl();
      if(this.at('RC')){this.eat('RC');return{T:'Dict',pairs:[]};}
      const pairs=[];
      while(!this.at('RC')){
        this.nl();const k=this.expr();this.eat('COL');const v=this.expr();pairs.push([k,v]);
        if(this.at('COM'))this.eat();this.nl();
      }
      this.eat('RC');return{T:'Dict',pairs};
    }
    if(c.t==='LP'){this.eat('LP');const e=this.expr();this.eat('RP');return e;}
    if(c.t==='ID'||c.t==='KW'){
      this.eat();
      if(this.at('ARR')){this.eat('ARR');return{T:'Lam',ps:[c.v],body:this.expr()};}
      return{T:'Var',n:c.v};
    }
    throw new Error(`Unexpected: ${c.t}(${c.v})`);
  }
}

let _out=[];
let _genv=null;

function blazeR(v) {
  if(v===null||v===undefined)return'null';
  if(typeof v==='boolean')return v?'true':'false';
  if(typeof v==='number'){
    if(!isFinite(v))return v>0?'Infinity':'-Infinity';
    if(Number.isInteger(v))return String(v);
    return String(Math.round(v*1e8)/1e8);
  }
  if(typeof v==='string')return v;
  if(Array.isArray(v))return'['+v.map(blazeR).join(', ')+']';
  if(v&&v._fn)return`<fn ${v.name}>`;
  if(typeof v==='object')return'{'+Object.entries(v).map(([k,val])=>`${k}: ${blazeR(val)}`).join(', ')+'}';
  return String(v);
}

function callBz(fn,args,kw={}) {
  if(typeof fn==='function')return fn(args,kw);
  if(fn&&fn._fn){
    const sub=fn.env.child();
    fn.ps.forEach((p,i)=>sub.def(p,args[i]??null));
    return evBz(fn.body,sub);
  }
  throw new Error(`Not callable`);
}

function _arr(v){if(Array.isArray(v))return v;if(typeof v==='string')return[...v];return[v];}
function _mean(a){return a.reduce((s,x)=>s+x,0)/a.length;}
function _std(a){const m=_mean(a);return Math.sqrt(a.reduce((s,x)=>s+(x-m)**2,0)/a.length);}

function makeBuiltins(env) {
  const defs={
    sum:([a])=>_arr(a).reduce((s,x)=>s+x,0),
    mean:([a])=>_mean(_arr(a)),
    std:([a])=>_std(_arr(a)),
    median:([a])=>{const s=[..._arr(a)].sort((x,y)=>x-y),m=Math.floor(s.length/2);return s.length%2?s[m]:(s[m-1]+s[m])/2;},
    min:([a])=>Math.min(..._arr(a)),
    max:([a])=>Math.max(..._arr(a)),
    sort:([a],kw={})=>[..._arr(a)].sort((x,y)=>kw.order==='desc'?y-x:x-y),
    filter:([a,fn])=>_arr(a).filter(x=>callBz(fn,[x])),
    map:([a,fn])=>_arr(a).map(x=>callBz(fn,[x])),
    reduce:([a,fn,init])=>_arr(a).reduce((acc,x)=>callBz(fn,[acc,x]),init??_arr(a)[0]),
    join:([a,sep=''])=>_arr(a).join(sep??''),
    upper:([s])=>String(s).toUpperCase(),
    lower:([s])=>String(s).toLowerCase(),
    words:([s])=>String(s).trim().split(/\s+/).filter(Boolean),
    chars:([s])=>[...String(s)],
    take:([a,n])=>_arr(a).slice(0,n),
    drop:([a,n])=>_arr(a).slice(n),
    first:([a])=>_arr(a)[0],
    last:([a])=>{const x=_arr(a);return x[x.length-1];},
    len:([v])=>Array.isArray(v)?v.length:String(v).length,
    count:([a])=>_arr(a).length,
    unique:([a])=>[...new Set(_arr(a))],
    reverse:([a])=>[..._arr(a)].reverse(),
    flatten:([a])=>_arr(a).flat(),
    append:([a,item])=>[..._arr(a),item],
    prepend:([a,item])=>[item,..._arr(a)],
    zip:([a,b])=>_arr(a).map((x,i)=>[x,_arr(b)[i]]),
    keys:([o])=>Object.keys(o||{}),
    values:([o])=>Object.values(o||{}),
    frequency:([a])=>{const f={};for(const x of _arr(a))f[x]=(f[x]||0)+1;return f;},
    group_by:([a,fn])=>{const g={};for(const x of _arr(a)){const k=String(callBz(fn,[x]));if(!g[k])g[k]=[];g[k].push(x);}return g;},
    corr:([xs,ys])=>{const xa=_arr(xs),ya=_arr(ys),n=xa.length,mx=_mean(xa),my=_mean(ya);const cov=xa.reduce((s,x,i)=>s+(x-mx)*(ya[i]-my),0)/n;const sx=_std(xa),sy=_std(ya);return cov/(sx*sy);},
    zscore:([a])=>{const x=_arr(a),m=_mean(x),s=_std(x);return x.map(v=>(v-m)/s);},
    normalize:([a])=>{const x=_arr(a),lo=Math.min(...x),hi=Math.max(...x);return x.map(v=>(v-lo)/(hi-lo));},
    linreg:([xs,ys])=>{const xa=_arr(xs),ya=_arr(ys),n=xa.length,mx=_mean(xa),my=_mean(ya);const b=xa.reduce((s,x,i)=>s+(x-mx)*(ya[i]-my),0)/xa.reduce((s,x)=>s+(x-mx)**2,0);return{slope:Math.round(b*1e6)/1e6,intercept:Math.round((my-b*mx)*1e6)/1e6};},
    percentile:([a,p])=>{const s=[..._arr(a)].sort((x,y)=>x-y);const i=(p/100)*(s.length-1);const lo=Math.floor(i),hi=Math.ceil(i);return s[lo]+(s[hi]-s[lo])*(i-lo);},
    describe:([a])=>{const x=_arr(a),m=_mean(x),s=_std(x);return{count:x.length,min:Math.min(...x),max:Math.max(...x),mean:Math.round(m*100)/100,std:Math.round(s*100)/100};},
    round:([n,d=0])=>Math.round(n*(10**d))/(10**d),
    floor:([n])=>Math.floor(n),
    ceil:([n])=>Math.ceil(n),
    abs:([n])=>Math.abs(n),
    sqrt:([n])=>Math.sqrt(n),
    pow:([b,e])=>b**e,
    log:([n])=>Math.log(n),
    exp:([n])=>Math.exp(n),
    str:([v])=>blazeR(v),
    num:([s])=>parseFloat(s),
    bool:([v])=>Boolean(v),
    type:([v])=>Array.isArray(v)?'list':v===null?'null':typeof v,
    range:([s,e,st=1])=>Array.from({length:Math.max(0,Math.ceil((e-s+1)/st))},(_,i)=>s+i*st),
    trim:([s])=>String(s).trim(),
    split:([s,sep])=>String(s).split(sep??/\s+/),
    replace:([s,f,t])=>String(s).replace(new RegExp(String(f),'g'),t??''),
    contains:([s,sub])=>String(s).includes(sub),
    chunk:([a,n])=>{const x=_arr(a);return Array.from({length:Math.ceil(x.length/n)},(_,i)=>x.slice(i*n,i*n+n));},
    print:(args)=>{_out.push(args.map(blazeR).join(' '));return null;},
    pi:Math.PI, e:Math.E,
  };
  Object.entries(defs).forEach(([k,v])=>env.def(k,v));
}

function evBz(node,env) {
  if(!node)return null;
  switch(node.T){
    case'Num':return node.v;
    case'Bool':return node.v;
    case'Null':return null;
    case'Str':return node.parts.map(p=>{
      if(p.k==='s')return p.v;
      try{return blazeR(runSrc(p.v.trim(),env));}catch(e){return'{ERR}';}
    }).join('');
    case'Var':{try{return env.get(node.n);}catch(e){throw new Error(`Undefined: '${node.n}'`);}}
    case'Asgn':{const v=evBz(node.e,env);env.set(node.nm,v);return v;}
    case'FnDef':{const fn={_fn:true,name:node.nm,ps:node.ps,body:node.body,env};env.def(node.nm,fn);return fn;}
    case'Lam':return{_fn:true,name:'λ',ps:node.ps,body:node.body,env};
    case'Call':{
      const fn=evBz(node.fn,env);
      const args=node.as.map(a=>evBz(a,env));
      const kw=Object.fromEntries(Object.entries(node.kw||{}).map(([k,v])=>[k,typeof v==='string'?v:evBz(v,env)]));
      return callBz(fn,args,kw);
    }
    case'Bin':{
      const{op}=node;
      if(op==='and')return evBz(node.l,env)&&evBz(node.r,env);
      if(op==='or')return evBz(node.l,env)||evBz(node.r,env);
      const l=evBz(node.l,env),r=evBz(node.r,env);
      if(op==='ADD'){if(Array.isArray(l)&&Array.isArray(r))return[...l,...r];return l+r;}
      if(op==='SUB')return l-r;if(op==='MUL')return l*r;
      if(op==='DIV')return r===0?Infinity:l/r;
      if(op==='MOD')return((l%r)+r)%r;if(op==='POW')return l**r;
      if(op==='==')return l===r;if(op==='!=')return l!==r;
      if(op==='<')return l<r;if(op==='>') return l>r;
      if(op==='<=')return l<=r;if(op==='>=')return l>=r;
      return null;
    }
    case'Un':{const v=evBz(node.e,env);if(node.op==='-')return-v;if(node.op==='not')return!v;return v;}
    case'Range':{
      const s=Math.round(evBz(node.s,env)),e=Math.round(evBz(node.e,env));
      if(Math.abs(e-s)>10000)throw new Error('Range too large (>10000)');
      return Array.from({length:Math.max(0,e-s+1)},(_,i)=>s+i);
    }
    case'List':return node.items.map(i=>evBz(i,env));
    case'Dict':return Object.fromEntries(node.pairs.map(([k,v])=>[evBz(k,env),evBz(v,env)]));
    case'Idx':{const o=evBz(node.o,env),idx=evBz(node.idx,env);return Array.isArray(o)?o[idx]:o?.[idx];}
    case'Field':{const o=evBz(node.o,env);return o?.[node.f];}
    case'If':{if(evBz(node.cond,env))return evBz(node.then_,env);return node.else_?evBz(node.else_,env):null;}
    case'Match':{
      const v=evBz(node.v,env);
      for(const{pat,body}of node.arms){
        if(pat.op==='_')return evBz(body,env.child());
        const pv=evBz(pat.pv,env);
        const hit={'EQ':v===pv,'NEQ':v!==pv,'LT':v<pv,'GT':v>pv,'LEQ':v<=pv,'GEQ':v>=pv}[pat.op]||false;
        if(hit)return evBz(body,env.child());
      }
      return null;
    }
    case'LC':{
      const iter=evBz(node.it,env);
      const items=Array.isArray(iter)?iter:[iter];
      return items
        .filter(item=>{if(!node.cond)return true;const s=env.child();s.def(node.v,item);return evBz(node.cond,s);})
        .map(item=>{const s=env.child();s.def(node.v,item);return evBz(node.e,s);});
    }
    case'Pipe':{const left=evBz(node.l,env);return applyPipe(left,node.r,env);}
    case'Print':{const v=evBz(node.e,env);_out.push(typeof v==='string'?v:blazeR(v));return null;}
    case'Prog':{let r=null;for(const s of node.ss)r=evBz(s,env);return r;}
    case'Expr':return evBz(node.e,env);
    default:throw new Error(`Unknown node: ${node.T}`);
  }
}

function applyPipe(left,right,env){
  if(right.T==='Var'){const fn=evBz(right,env);return callBz(fn,[left]);}
  if(right.T==='Call'){
    const fn=evBz(right.fn,env);
    const args=right.as.map(a=>evBz(a,env));
    const kw=Object.fromEntries(Object.entries(right.kw||{}).map(([k,v])=>[k,typeof v==='string'?v:evBz(v,env)]));
    return callBz(fn,[left,...args],kw);
  }
  if(right.T==='Lam'){const fn=evBz(right,env);return callBz(fn,[left]);}
  return evBz(right,env);
}

function runSrc(src,env){
  const ast=new Parser(tokenize(src)).parse();
  return evBz(ast,env||_genv);
}

function mkEnv(){const env=new BlazeEnv();makeBuiltins(env);return env;}

function runBlaze(code){
  _out=[];
  const env=mkEnv();
  try{
    const ast=new Parser(tokenize(code)).parse();
    const result=evBz(ast,env);
    const out=[..._out];
    if(result!==null&&result!==undefined&&!(result&&result._fn)){if(out.length===0)out.push(blazeR(result));}
    return{ok:true,output:out,result};
  }catch(e){return{ok:false,output:[`❌ ${e.message}`],result:null};}
}

function runStateful(code){
  _out=[];
  if(!_genv)_genv=mkEnv();
  try{
    const ast=new Parser(tokenize(code)).parse();
    const result=evBz(ast,_genv);
    const out=[..._out];
    if(result!==null&&result!==undefined&&!(result&&result._fn)){
      if(ast.ss.length===1&&ast.ss[0].T==='Expr')out.push(blazeR(result));
    }
    return{ok:true,output:out};
  }catch(e){return{ok:false,output:[`❌ ${e.message}`]};}
}

// ════════════════════════════════════════════════════
//  SYNTAX HIGHLIGHTING
// ════════════════════════════════════════════════════

function hl(code){
  let s=code.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  // Order matters: comments first, then strings, then the rest
  s=s.replace(/#[^\n]*/g,m=>`<cm>${m}</cm>`);
  s=s.replace(/"[^"]*"/g,m=>`<st>${m}</st>`);
  s=s.replace(/\b(if|then|else|elif|for|in|match|and|or|not|true|false|null|return|desc|asc)\b/g,m=>`<kw>${m}</kw>`);
  s=s.replace(/\|/g,`<pi> | </pi>`);
  s=s.replace(/-&gt;/g,`<ar> -&gt;</ar>`);
  s=s.replace(/\.\./g,`<dd>..</dd>`);
  s=s.replace(/\b([a-z_][a-zA-Z0-9_]*)\s*(?=\()/g,(_,g)=>`<fn>${g}</fn>`);
  s=s.replace(/\b(\d+\.?\d*)\b/g,m=>`<nm>${m}</nm>`);
  // Now replace placeholder tags with real spans
  const C={cm:'#475569',st:'#06B6D4',kw:'#C084FC',pi:'#F59E0B',ar:'#FB923C',dd:'#F59E0B',fn:'#34D399',nm:'#FCD34D'};
  const W={pi:'700',ar:'600'};
  return s.replace(/<(cm|st|kw|pi|ar|dd|fn|nm)>(.*?)<\/\1>/gs,
    (_,tag,content)=>`<span style="color:${C[tag]};${W[tag]?`font-weight:${W[tag]};`:''}">${content}</span>`);
}

// ════════════════════════════════════════════════════
//  UI PRIMITIVES
// ════════════════════════════════════════════════════

const S={
  bg:'#0A0E17',bg2:'#0F1629',bg3:'#131929',
  bd:'#1E293B',bd2:'#2D3F5A',
  amber:'#F59E0B',cyan:'#06B6D4',green:'#34D399',
  purple:'#C084FC',slate:'#94A3B8',text:'#E2E8F0',
  orange:'#FB923C',red:'#EF4444',
};

function Pre({children,style={}}){
  return(
    <pre style={{fontFamily:"'JetBrains Mono',ui-monospace,monospace",fontSize:13,lineHeight:1.7,
      margin:0,padding:0,color:S.text,background:'transparent',whiteSpace:'pre-wrap',wordBreak:'break-word',...style}}
      dangerouslySetInnerHTML={{__html:hl(String(children))}}/>
  );
}

function RunCell({title,code:init}){
  const[code,setCode]=useState(init);
  const[out,setOut]=useState(null);
  const[busy,setBusy]=useState(false);
  const taRef=useRef();

  const run=useCallback(()=>{
    setBusy(true);
    setTimeout(()=>{setOut(runBlaze(code));setBusy(false);},20);
  },[code]);

  useEffect(()=>{run();},[]);

  const rows=code.split('\n').length;
  return(
    <div style={{background:S.bg3,border:`1px solid ${S.bd}`,borderRadius:12,overflow:'hidden',marginBottom:14,
      transition:'border-color 0.15s'}}
      onMouseEnter={e=>e.currentTarget.style.borderColor=S.bd2}
      onMouseLeave={e=>e.currentTarget.style.borderColor=S.bd}>
      <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',
        padding:'9px 16px',borderBottom:`1px solid ${S.bd}`,background:S.bg2}}>
        <span style={{fontSize:12,color:S.slate,fontFamily:'Inter,system-ui',fontWeight:500}}>{title}</span>
        <button onClick={run} style={{background:busy?'none':`${S.amber}20`,
          border:`1px solid ${busy?S.bd:S.amber}66`,color:busy?S.slate:S.amber,
          borderRadius:6,padding:'3px 12px',fontSize:12,fontFamily:'Inter,system-ui',
          fontWeight:600,cursor:busy?'default':'pointer',transition:'all 0.12s'}}>
          {busy?'⏳':'▶ Run'}
        </button>
      </div>
      <div style={{position:'relative',padding:'13px 16px 10px'}}>
        <textarea ref={taRef} value={code} onChange={e=>setCode(e.target.value)}
          rows={rows}
          style={{position:'absolute',inset:'13px 16px 10px',background:'transparent',
            border:'none',outline:'none',color:'transparent',caretColor:S.text,
            fontFamily:"'JetBrains Mono',ui-monospace,monospace",fontSize:13,lineHeight:1.7,
            resize:'none',width:'calc(100% - 32px)',zIndex:2,overflow:'hidden'}}
          spellCheck={false}
          onKeyDown={e=>{
            if(e.key==='Enter'&&(e.metaKey||e.ctrlKey)){e.preventDefault();run();}
            if(e.key==='Tab'){e.preventDefault();const t=e.target,p=t.selectionStart,v=t.value;
              setCode(v.slice(0,p)+'  '+v.slice(t.selectionEnd));
              setTimeout(()=>{t.selectionStart=t.selectionEnd=p+2;},0);}
          }}/>
        <Pre>{code}</Pre>
      </div>
      {out&&(
        <div style={{borderTop:`1px solid ${S.bd}`,padding:'9px 16px',
          background:out.ok?`${S.green}0a`:`${S.red}0a`}}>
          <div style={{fontSize:11,color:S.slate,marginBottom:4,fontFamily:'Inter,system-ui',
            fontWeight:600,textTransform:'uppercase',letterSpacing:'0.07em'}}>
            {out.ok?'→ output':'→ error'}
          </div>
          {out.output.map((line,i)=>(
            <div key={i} style={{fontFamily:"'JetBrains Mono',monospace",fontSize:13,
              color:out.ok?S.green:S.red,lineHeight:1.6}}>{line}</div>
          ))}
        </div>
      )}
    </div>
  );
}

// ════════════════════════════════════════════════════
//  TABS
// ════════════════════════════════════════════════════

function Overview(){
  return(
    <div>
      <div style={{textAlign:'center',padding:'44px 24px 36px',borderBottom:`1px solid ${S.bd}`}}>
        <div style={{display:'inline-block',padding:'3px 12px',background:`${S.amber}18`,
          border:`1px solid ${S.amber}44`,borderRadius:99,fontSize:11,color:S.amber,
          marginBottom:18,fontFamily:'Inter,system-ui',fontWeight:600,letterSpacing:'0.05em'}}>
          v0.1 · Open Source · MIT · Zero dependencies
        </div>
        <h1 style={{fontFamily:"'Space Grotesk',system-ui",
          fontSize:'clamp(26px,4.5vw,48px)',fontWeight:700,margin:'0 0 14px',
          background:`linear-gradient(135deg,${S.amber},#FBBF24,${S.orange})`,
          WebkitBackgroundClip:'text',WebkitTextFillColor:'transparent',
          lineHeight:1.1,letterSpacing:'-0.02em'}}>
          Code at the speed<br/>of thought.
        </h1>
        <p style={{fontFamily:'Inter,system-ui',fontSize:15,color:S.slate,margin:'0 auto 28px',
          maxWidth:460,lineHeight:1.65}}>
          Blaze is a pipeline-first language for data &amp; analytics. Chain operations with{' '}
          <code style={{color:S.amber,fontFamily:'monospace',fontSize:14,fontWeight:700}}>|</code>,
          skip the boilerplate, get answers faster.
        </p>
        <div style={{maxWidth:580,margin:'0 auto',background:S.bg2,borderRadius:12,
          border:`1px solid ${S.bd}`,padding:'18px 22px',textAlign:'left'}}>
          <div style={{fontSize:10,color:S.slate,marginBottom:8,fontFamily:'Inter,system-ui',
            fontWeight:700,textTransform:'uppercase',letterSpacing:'0.1em'}}>
            1 line · Project Euler #1
          </div>
          <Pre>{`[1..100] | filter x -> x % 3 == 0 or x % 5 == 0 | sum`}</Pre>
          <div style={{marginTop:8,fontFamily:"'JetBrains Mono',monospace",fontSize:13,color:S.green}}>→ 2418</div>
        </div>
      </div>
      <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(200px,1fr))',
        gap:14,padding:'28px 24px'}}>
        {[
          {icon:'⚡',t:'Pipe everything',d:'Chain any operation with |. Data flows left to right, naturally.',c:S.amber},
          {icon:'📊',t:'Stats built in',d:'mean, std, corr, zscore, linreg — no imports needed.',c:S.cyan},
          {icon:'🔢',t:'Range literals',d:'1..100 creates a list. Filter, sum, map in one line.',c:S.green},
          {icon:'✂️',t:'Zero boilerplate',d:'No class defs, no imports, no type annotations.',c:S.purple},
          {icon:'📦',t:'Zero dependencies',d:'Single Python file, 3.8+. Ships anywhere.',c:S.orange},
          {icon:'🎯',t:'Pattern matching',d:'match / | arms for clean conditional logic.',c:'#F472B6'},
        ].map(({icon,t,d,c})=>(
          <div key={t} style={{background:S.bg3,borderRadius:10,border:`1px solid ${S.bd}`,padding:'16px 18px'}}>
            <div style={{fontSize:22,marginBottom:7}}>{icon}</div>
            <div style={{fontFamily:"'Space Grotesk',system-ui",fontWeight:600,fontSize:14,color:S.text,marginBottom:5}}>{t}</div>
            <div style={{fontFamily:'Inter,system-ui',fontSize:12,color:S.slate,lineHeight:1.6}}>{d}</div>
          </div>
        ))}
      </div>
      <div style={{padding:'0 24px 36px'}}>
        <div style={{background:S.bg2,border:`1px solid ${S.bd}`,borderRadius:12,padding:'18px 22px'}}>
          <div style={{fontFamily:"'Space Grotesk',system-ui",fontWeight:600,fontSize:14,color:S.text,marginBottom:14}}>
            Get started in 30 seconds
          </div>
          {[
            ['Download', 'curl -O https://raw.githubusercontent.com/uchejerla/blaze/main/blaze.py'],
            ['REPL',     'python3 blaze.py'],
            ['Run file', 'python3 blaze.py script.blz'],
            ['One-liner','python3 blaze.py -e "[1..100] | filter x -> x % 3 == 0 | sum"'],
          ].map(([label,cmd])=>(
            <div key={label} style={{marginBottom:7,display:'flex',alignItems:'baseline',gap:12,flexWrap:'wrap'}}>
              <span style={{fontFamily:'Inter,system-ui',fontSize:10,color:S.slate,fontWeight:700,
                textTransform:'uppercase',letterSpacing:'0.07em',minWidth:60}}>{label}</span>
              <code style={{fontFamily:"'JetBrains Mono',monospace",fontSize:11,color:S.cyan}}>{cmd}</code>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Examples(){
  const cells=[
    {title:'🧮 Project Euler #1',
     code:`[1..100] | filter x -> x % 3 == 0 or x % 5 == 0 | sum`},
    {title:'🌀 Fibonacci sequence',
     code:`fib(n) -> if n <= 1 then n else fib(n-1) + fib(n-2)\n[fib(n) for n in 0..12]`},
    {title:'📊 Data analysis',
     code:`data = [23, 45, 12, 67, 34, 89, 56, 78, 11, 90]\nprint "Mean:   {data | mean | round(2)}"\nprint "Std:    {data | std | round(2)}"\nprint "Top 3:  {data | sort desc | take(3)}"`},
    {title:'📝 String pipeline',
     code:`"the quick brown fox jumps" | words | unique | sort | join ", "`},
    {title:'🔧 Closures & higher-order functions',
     code:`make_adder(n) -> x -> x + n\nadd5 = make_adder(5)\nadd10 = make_adder(10)\nprint "add5:  {[add5(x) for x in 1..5]}"\nprint "add10: {[add10(x) for x in 1..5]}"`},
    {title:'📈 Stats & correlation',
     code:`xs = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]\nys = [1.8, 4.2, 5.9, 8.1, 10.0, 12.2, 13.9, 15.8, 18.1, 20.0]\nprint "Corr:   {corr(xs, ys) | round(4)}"\nprint "Slope:  {linreg(xs, ys).slope}"\nprint "Zscore: {xs | zscore | map x -> round(x, 2)}"`},
  ];
  return(
    <div style={{padding:'22px 24px'}}>
      <div style={{marginBottom:18}}>
        <h2 style={{fontFamily:"'Space Grotesk',system-ui",fontWeight:700,fontSize:19,color:S.text,margin:'0 0 5px'}}>Live examples</h2>
        <p style={{fontFamily:'Inter,system-ui',fontSize:12,color:S.slate,margin:0}}>
          All examples run in-browser. Edit any cell and press ▶ Run or Ctrl+Enter.
        </p>
      </div>
      {cells.map((c,i)=><RunCell key={i} {...c}/>)}
    </div>
  );
}

function Syntax(){
  const secs=[
    {t:'Variables & Strings',items:[
      ['Assign','x = 42'],['String interp','"Hello {name}, x={x*2}"'],
      ['Range','1..10  →  [1, 2, ..., 10]'],['Bool/null','true  false  null'],
    ]},
    {t:'The Pipe Operator |',items:[
      ['Chain ops','data | sort | take(5)'],
      ['Lambda in pipe','[1..20] | filter x -> x % 2 == 0'],
      ['Full pipeline','"text" | words | map w -> upper(w) | join " "'],
      ['Reverse sort','data | sort desc | take(3)'],
    ]},
    {t:'Functions & Lambdas',items:[
      ['Arrow fn','double(x) -> x * 2'],
      ['If expression','sign(x) -> if x > 0 then 1 else -1'],
      ['Lambda','x -> x * x'],
      ['Closure','make_adder(n) -> x -> x + n'],
      ['Recursion','fib(n) -> if n <= 1 then n else fib(n-1) + fib(n-2)'],
    ]},
    {t:'Collections',items:[
      ['List','[1, 2, 3, 4, 5]'],['Dict','{name: "Alice", age: 30}'],
      ['List comp','[x*x for x in 1..10 if x % 2 == 0]'],
      ['Dict comp','{x: x*x for x in 1..5}'],['Concat','[1,2] + [3,4]'],
    ]},
    {t:'Pattern Matching',items:[
      ['Match','grade(s) ->\n  match s\n  | >= 90 -> "A"\n  | >= 80 -> "B"\n  | _     -> "F"'],
    ]},
    {t:'Stats builtins',items:[
      ['Summaries','mean  median  std  min  max  sum'],
      ['Advanced','corr(xs, ys)  linreg(xs, ys)'],
      ['Transform','data | zscore  |  data | normalize'],
      ['Lists','filter  map  sort  take  unique  frequency'],
    ]},
  ];
  return(
    <div style={{padding:'22px 24px'}}>
      <h2 style={{fontFamily:"'Space Grotesk',system-ui",fontWeight:700,fontSize:19,color:S.text,margin:'0 0 18px'}}>Syntax reference</h2>
      <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(260px,1fr))',gap:14}}>
        {secs.map(({t,items})=>(
          <div key={t} style={{background:S.bg3,border:`1px solid ${S.bd}`,borderRadius:10,overflow:'hidden'}}>
            <div style={{padding:'9px 15px',borderBottom:`1px solid ${S.bd}`,background:S.bg2,
              fontFamily:"'Space Grotesk',system-ui",fontWeight:600,fontSize:12,color:S.amber}}>{t}</div>
            <div style={{padding:'11px 15px'}}>
              {items.map(([label,code])=>(
                <div key={label} style={{marginBottom:9}}>
                  <div style={{fontSize:10,color:S.slate,fontFamily:'Inter,system-ui',fontWeight:600,marginBottom:2,letterSpacing:'0.03em'}}>{label}</div>
                  <Pre style={{fontSize:11.5}}>{code}</Pre>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Compare(){
  const rows=[
    {task:'Sum multiples of 3 or 5 below 100',
     py:`total = 0\nfor i in range(1, 101):\n    if i % 3 == 0 or i % 5 == 0:\n        total += i\nprint(total)`,
     bz:`[1..100] | filter x -> x % 3 == 0 or x % 5 == 0 | sum`,
     pl:5,bl:1},
    {task:'Compute mean, std, top-3',
     py:`import statistics\ndata = [23, 45, 12, 67, 34, 89]\nprint(statistics.mean(data))\nprint(f"{statistics.stdev(data):.2f}")\nprint(sorted(data, reverse=True)[:3])`,
     bz:`data = [23, 45, 12, 67, 34, 89]\nprint "Mean: {data | mean}"\nprint "Std:  {data | std | round(2)}"\nprint "Top3: {data | sort desc | take(3)}"`,
     pl:5,bl:4},
    {task:'Uppercase every word in a string',
     py:`result = " ".join(w.upper()\n    for w in sentence.split())`,
     bz:`sentence | words | map w -> upper(w) | join " "`,
     pl:2,bl:1},
    {task:'Word frequency count',
     py:`from collections import Counter\nfreq = dict(Counter(text.split()))`,
     bz:`text | words | frequency`,
     pl:2,bl:1},
    {task:'Fibonacci (first 13)',
     py:`def fib(n):\n    if n <= 1: return n\n    return fib(n-1) + fib(n-2)\nresult = [fib(i) for i in range(13)]`,
     bz:`fib(n) -> if n <= 1 then n else fib(n-1) + fib(n-2)\n[fib(n) for n in 0..12]`,
     pl:4,bl:2},
  ];
  return(
    <div style={{padding:'22px 24px'}}>
      <h2 style={{fontFamily:"'Space Grotesk',system-ui",fontWeight:700,fontSize:19,color:S.text,margin:'0 0 5px'}}>Blaze vs Python</h2>
      <p style={{fontFamily:'Inter,system-ui',fontSize:12,color:S.slate,margin:'0 0 20px'}}>Same task. Less code. More readable.</p>
      {rows.map(({task,py,bz,pl,bl})=>(
        <div key={task} style={{background:S.bg3,border:`1px solid ${S.bd}`,borderRadius:12,
          overflow:'hidden',marginBottom:14}}>
          <div style={{padding:'9px 18px',background:S.bg2,borderBottom:`1px solid ${S.bd}`,
            display:'flex',alignItems:'center',justifyContent:'space-between',flexWrap:'wrap',gap:6}}>
            <span style={{fontFamily:"'Space Grotesk',system-ui",fontWeight:600,fontSize:13,color:S.text}}>{task}</span>
            <div style={{display:'flex',gap:6}}>
              <span style={{fontSize:10,padding:'2px 7px',borderRadius:99,background:'#1E293B',
                color:S.slate,fontFamily:'Inter,system-ui',fontWeight:600}}>Python: {pl} {pl===1?'line':'lines'}</span>
              <span style={{fontSize:10,padding:'2px 7px',borderRadius:99,background:`${S.amber}22`,
                color:S.amber,border:`1px solid ${S.amber}44`,fontFamily:'Inter,system-ui',fontWeight:700}}>
                Blaze: {bl} {bl===1?'line':'lines'}</span>
            </div>
          </div>
          <div style={{display:'grid',gridTemplateColumns:'1fr 1fr'}}>
            <div style={{padding:'12px 16px',borderRight:`1px solid ${S.bd}`}}>
              <div style={{fontSize:10,color:'#64748B',marginBottom:7,fontFamily:'Inter,system-ui',
                fontWeight:700,textTransform:'uppercase',letterSpacing:'0.07em'}}>Python</div>
              <pre style={{fontFamily:"'JetBrains Mono',monospace",fontSize:11.5,lineHeight:1.7,
                color:'#94A3B8',margin:0,whiteSpace:'pre-wrap'}}>{py}</pre>
            </div>
            <div style={{padding:'12px 16px'}}>
              <div style={{fontSize:10,color:S.amber,marginBottom:7,fontFamily:'Inter,system-ui',
                fontWeight:700,textTransform:'uppercase',letterSpacing:'0.07em'}}>Blaze 🔥</div>
              <Pre style={{fontSize:11.5}}>{bz}</Pre>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function Playground(){
  const[code,setCode]=useState('# Write Blaze code here — state persists between runs!\ndata = [3, 1, 4, 1, 5, 9, 2, 6, 5, 3]\ndata | sort desc');
  const[out,setOut]=useState(null);

  useEffect(()=>{ _genv=mkEnv(); },[]);

  const run=useCallback(()=>{
    setOut(runStateful(code));
  },[code]);

  return(
    <div style={{padding:'22px 24px'}}>
      <h2 style={{fontFamily:"'Space Grotesk',system-ui",fontWeight:700,fontSize:19,color:S.text,margin:'0 0 5px'}}>Playground</h2>
      <p style={{fontFamily:'Inter,system-ui',fontSize:12,color:S.slate,margin:'0 0 14px'}}>
        State persists between runs. Define a variable, then use it in the next run. Ctrl+Enter to execute.
      </p>
      <div style={{background:S.bg3,border:`1px solid ${S.bd}`,borderRadius:12,overflow:'hidden'}}>
        <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',
          padding:'9px 15px',background:S.bg2,borderBottom:`1px solid ${S.bd}`}}>
          <div style={{display:'flex',gap:5}}>
            {['#EF4444','#F59E0B','#34D399'].map(c=>(
              <div key={c} style={{width:9,height:9,borderRadius:'50%',background:c}}/>
            ))}
          </div>
          <button onClick={()=>{_genv=mkEnv();setOut(null);}}
            style={{fontSize:11,color:S.slate,background:'none',border:'none',cursor:'pointer',fontFamily:'Inter,system-ui'}}>
            ↺ Reset
          </button>
        </div>
        <textarea value={code} onChange={e=>setCode(e.target.value)}
          style={{width:'100%',minHeight:120,padding:'13px 16px',background:'transparent',
            border:'none',outline:'none',color:S.text,resize:'vertical',
            fontFamily:"'JetBrains Mono',ui-monospace,monospace",fontSize:13,lineHeight:1.7,
            boxSizing:'border-box'}}
          spellCheck={false}
          onKeyDown={e=>{
            if(e.key==='Enter'&&(e.metaKey||e.ctrlKey)){e.preventDefault();run();}
            if(e.key==='Tab'){e.preventDefault();const t=e.target,p=t.selectionStart,v=t.value;
              setCode(v.slice(0,p)+'  '+v.slice(t.selectionEnd));
              setTimeout(()=>{t.selectionStart=t.selectionEnd=p+2;},0);}
          }}/>
        <div style={{padding:'8px 14px',borderTop:`1px solid ${S.bd}`,display:'flex',justifyContent:'flex-end'}}>
          <button onClick={run} style={{background:S.amber,color:'#000',border:'none',
            borderRadius:6,padding:'6px 20px',fontSize:13,fontWeight:700,cursor:'pointer',
            fontFamily:'Inter,system-ui',transition:'opacity 0.1s'}}
            onMouseEnter={e=>e.target.style.opacity='0.85'}
            onMouseLeave={e=>e.target.style.opacity='1'}>▶ Run</button>
        </div>
        {out&&(
          <div style={{borderTop:`1px solid ${S.bd}`,padding:'11px 16px',
            background:out.ok?`${S.green}0a`:`${S.red}0a`}}>
            <div style={{fontSize:10,color:S.slate,marginBottom:5,fontFamily:'Inter,system-ui',
              fontWeight:700,textTransform:'uppercase',letterSpacing:'0.08em'}}>output</div>
            {out.output.length===0
              ?<div style={{color:S.slate,fontFamily:'monospace',fontSize:12}}>null</div>
              :out.output.map((l,i)=>(
                <div key={i} style={{fontFamily:"'JetBrains Mono',monospace",fontSize:13,
                  color:out.ok?S.green:S.red,lineHeight:1.6}}>{l}</div>
              ))}
          </div>
        )}
      </div>
      <div style={{marginTop:16,padding:14,background:S.bg2,border:`1px solid ${S.bd}`,borderRadius:8}}>
        <div style={{fontSize:11,color:S.amber,fontFamily:'Inter,system-ui',fontWeight:600,marginBottom:8}}>Try these:</div>
        {[
          '[1..50] | filter x -> x % 7 == 0',
          '"data governance is the foundation" | words | frequency',
          'make_adder(100) -> x -> x + 100  # try defining your own!',
          '[x*x for x in 1..10 if x % 2 != 0]',
        ].map(s=>(
          <div key={s} onClick={()=>{setCode(s);}}
            style={{fontFamily:"'JetBrains Mono',monospace",fontSize:11.5,color:S.slate,
              cursor:'pointer',padding:'3px 0',lineHeight:1.7,transition:'color 0.1s'}}
            onMouseEnter={e=>e.target.style.color=S.cyan}
            onMouseLeave={e=>e.target.style.color=S.slate}>
            &gt; {s}
          </div>
        ))}
      </div>
    </div>
  );
}

// ════════════════════════════════════════════════════
//  ROOT
// ════════════════════════════════════════════════════

const TABS=[
  {id:'overview',label:'Overview'},
  {id:'examples',label:'Examples'},
  {id:'syntax',label:'Syntax'},
  {id:'compare',label:'vs Python'},
  {id:'play',label:'Playground'},
];

export default function BlazeShowcase(){
  const[tab,setTab]=useState('examples');
  return(
    <div style={{background:S.bg,color:S.text,minHeight:'100vh',fontFamily:'Inter,system-ui,sans-serif'}}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@400;500&family=Inter:wght@400;500;600&display=swap');
        *{box-sizing:border-box;}
        textarea{caret-color:#F59E0B!important;}
        textarea::placeholder{color:#2D3F5A;}
        ::-webkit-scrollbar{width:5px;height:5px;}
        ::-webkit-scrollbar-track{background:#0F1629;}
        ::-webkit-scrollbar-thumb{background:#2D3F5A;border-radius:3px;}
        @media(prefers-reduced-motion:reduce){*{transition:none!important;}}
      `}</style>

      {/* Header */}
      <header style={{borderBottom:`1px solid ${S.bd}`,padding:'12px 22px',
        display:'flex',alignItems:'center',justifyContent:'space-between',
        background:S.bg,position:'sticky',top:0,zIndex:10}}>
        <div style={{display:'flex',alignItems:'center',gap:9}}>
          <span style={{fontFamily:"'Space Grotesk',system-ui",fontWeight:700,fontSize:21,
            background:`linear-gradient(135deg,${S.amber},${S.orange})`,
            WebkitBackgroundClip:'text',WebkitTextFillColor:'transparent'}}>🔥 Blaze</span>
          <span style={{fontSize:10,color:S.slate,padding:'2px 7px',background:S.bg3,
            border:`1px solid ${S.bd}`,borderRadius:99,fontFamily:'Inter,system-ui',fontWeight:600}}>v0.1</span>
        </div>
        <code style={{fontFamily:"'JetBrains Mono',monospace",fontSize:11,color:S.cyan,
          background:S.bg2,border:`1px solid ${S.bd}`,borderRadius:5,padding:'3px 9px'}}>
          python3 blaze.py
        </code>
      </header>

      {/* Tab nav */}
      <div style={{borderBottom:`1px solid ${S.bd}`,display:'flex',
        overflowX:'auto',padding:'0 22px',scrollbarWidth:'none'}}>
        {TABS.map(({id,label})=>(
          <button key={id} onClick={()=>setTab(id)} style={{
            padding:'11px 15px',border:'none',background:'none',cursor:'pointer',
            fontFamily:"'Space Grotesk',system-ui",fontSize:13,fontWeight:tab===id?600:400,
            color:tab===id?S.amber:S.slate,
            borderBottom:tab===id?`2px solid ${S.amber}`:'2px solid transparent',
            transition:'color 0.12s',whiteSpace:'nowrap',
          }}>
            {label}
          </button>
        ))}
      </div>

      {/* Content */}
      <main style={{maxWidth:880,margin:'0 auto'}}>
        {tab==='overview'&&<Overview/>}
        {tab==='examples'&&<Examples/>}
        {tab==='syntax'&&<Syntax/>}
        {tab==='compare'&&<Compare/>}
        {tab==='play'&&<Playground/>}
      </main>

      <footer style={{borderTop:`1px solid ${S.bd}`,padding:'18px 24px',textAlign:'center',
        fontFamily:'Inter,system-ui',fontSize:11,color:'#334155'}}>
        Blaze v0.1 · MIT License · Built for data people ·{' '}
        <a href="https://uchejerla.github.io" style={{color:S.slate,textDecoration:'none'}}>uchejerla.github.io</a>
      </footer>
    </div>
  );
}
