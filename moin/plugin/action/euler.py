#!/usr/bin/env python
# $Id$

import copy, math, string, sys, time, urllib

rules = {}      # kb as dictionary of lists
step = 0        # step counter
why = False     # proof explanation
once = False    # only one solution
forever = False # subgoal reordering
debug = False   # debug info

class Triple:
    def __init__(self, s, nodes=[]):
        self.arc = s
        self.nodes = nodes
        if s == '': self.arc = '{}'
        elif s[-1] != '}':
            pcs = tokenize(s, ' ')
            if len(pcs) == 3:
                self.arc = pcs[1]
                del pcs[1]
                self.nodes = map(Triple, pcs)
            elif s[-1] == ')':
                pcs = tokenize(s[1:-1], '/')
                if len(pcs) == 2:
                    self.arc = '.'
                    self.nodes = map(Triple, map(string.strip, pcs))
                else:
                    pcs = tokenize(s[1:-1], ' ')
                    pcs.reverse()
                    l = Triple('.')
                    for p in pcs: l = Triple('.', [Triple(p), l])
                    self.arc = l.arc
                    self.nodes = l.nodes
        self.var = self.arc[0] == '?'

    def __repr__(self):
        if self.arc == '.':
            if len(self.nodes) == 0: return '()'
            n = self.nodes[1]
            if n.arc == '.' and n.nodes == []:
                return '(%s)' % str(self.nodes[0])
            elif n.arc == '.':
                return '(%s %s)' % (str(self.nodes[0]), str(self.nodes[1])[1:-1])
            else:
                return '(%s/%s)' % (str(self.nodes[0]), str(self.nodes[1]))
        elif self.nodes:
            return '%s %s %s' % (self.nodes[0], self.arc, self.nodes[1])
        else: return self.arc

class Rule:
    def __init__(self, s):
        flds = s.split('=>')
        self.body = []
        if len(flds) == 2:
            self.head = Triple(flds[1].strip(' {}'))
            flds = tokenize(flds[0].strip(' {}'), '.')
            for fld in flds: self.body.append(Triple(fld.strip()))
        else: self.head = Triple(flds[0].strip())

    def __repr__(self):
        if self.body != []:
            s = ''
            for t in self.body:
                if s != '': s = s+'. '
                s = s+str(t)
            if self.head.arc == '[]': return '{%s} => []' % (s)
            else: return '{%s} => {%s}' % (s, self.head)
        else: return '%s' % (self.head)
        
class Step:
    def __init__(self, rule, src=0, parent=None, env={}, ind=0):
        self.rule = rule
        self.src = src
        self.parent = parent
        self.env = copy.copy(env)
        self.ind = ind

def prove(query, lstep=-1):
    global step
    queue = [Step(query)]
    ev = ''
    istep = step
    while queue:
        c = queue.pop()
        step = step+1
        if lstep != -1 and step-istep >= lstep: return ''
        if debug: print 'step %s %s %s' % (step, c.rule, c.env)
        if c.ind >= len(c.rule.body):
            if not c.parent:
                for t in c.rule.body:
                    e = str(eval(t, c.env))
                    if t.arc == '.': e = e[1:-1]
                    if ev.find(e+'.\n') == -1: ev = ev+e+'.\n'
                if once: return ev
                continue
            r = Step(copy.copy(c.parent.rule), c.parent.src,
                  copy.copy(c.parent.parent), c.parent.env, c.parent.ind)
            unify(c.rule.head, c.env, r.rule.body[r.ind], r.env, 1)
            rh = eval(c.rule.head, c.env)
            if rh and why:
                cr = copy.deepcopy(c.rule)
                cr.head = rh
                r.rule.body = copy.deepcopy(c.parent.rule.body)
                r.rule.body[r.ind] = Triple(str(cr))
            r.ind = r.ind+1
            queue.append(r)
            continue
        t = c.rule.body[c.ind]
        b = builtin(t, c)
        if b == 1:
            r = Step(copy.copy(c.rule), c.src,
                  copy.copy(c.parent), c.env, c.ind)
            if why:
                r.rule.body = copy.deepcopy(r.rule.body)
                r.rule.body[r.ind] = eval(r.rule.body[r.ind], r.env)
            r.ind = r.ind+1
            queue.append(r)
            continue
        elif b == 0: continue
        if not rules.get(t.arc): continue
        i = len(queue)
        src = 0
        for rl in rules[t.arc]:
            src = src+1
            r = Step(rl, src, c)
            if unify(t, c.env, rl.head, r.env, 1):
                cp = c.parent
                while cp:
                    if cp.src == c.src and unify(cp.rule.head, cp.env,
                          c.rule.head, c.env, 0): break  ### euler path ###
                    cp = cp.parent
                if not cp: queue.insert(i, r)
    return ev

def unify(s, senv, d, denv, f):
    if s.var:
        sval = eval(s, senv)
        if sval: return unify(sval, senv, d, denv, f)
        else: return 1
    elif d.var:
        dval = eval(d, denv)
        if dval: return unify(s, senv, dval, denv, f)
        else:
            if f: denv[d.arc] = eval(s, senv)
            return 1
    elif s.arc == d.arc and len(s.nodes) == len(d.nodes):
        for i in range(len(s.nodes)):
            if not unify(s.nodes[i], senv, d.nodes[i], denv, f): return 0
        return 1
    else: return 0

def eval(t, env):
    if t.var:
        a = env.get(t.arc)
        if a: return eval(a, env)
        else: return None
    elif t.nodes == []: return t
    else:
        n = []
        for arg in t.nodes: 
            a = eval(arg, env)
            if a: n.append(a)
            else: return None
        return Triple(t.arc, n)

def reorder(goals, ev):
    global step
    lstep = step
    sys.stderr.write('%s steps at start\n' % (lstep))
    for h in rules:
        for r in rules[h]:
            if len(r.body) < 2: continue
            i = 0
            while i < len(r.body):
                c = r.body[i:i+1]
                d = r.body[:i]+r.body[i+1:]
                j = i+1
                while j < len(r.body):
                    b = d[j-1].arc[:4] == 'log:' or d[j-1].arc[:5] == 'math:'
                    if b: break
                    r.body = d[:j]+c+d[j:]
                    e = ''
                    istep = step
                    for g in goals: e = e+'\n'+prove(g, lstep)
                    if step-istep < lstep and len(e) == len(ev):
                        lstep = step-istep
                        sys.stderr.write('%s.\n%s steps\n' % (r, lstep))
                        i = 0
                        break
                    j = j+1
                if j == len(r.body) or b:
                    r.body = d[:i]+c+d[i:]
                    i = i+1

def builtin(t, c):
    t0 = eval(t.nodes[0], c.env)
    t1 = eval(t.nodes[1], c.env)
    if t.arc == 'log:equalTo':
        if t0 and t1 and t0.arc == t1.arc: return 1
        else: return 0
    elif t.arc == 'log:notEqualTo':
        if t0 and t1 and t0.arc != t1.arc: return 1
        else: return 0
    elif t.arc == 'math:absoluteValue':
        if t0 and not t0.var:
            a = abs(float(t0.arc))
            if unify(Triple(str(a)), c.env, t.nodes[1], c.env, 1): return 1
        else: return 0
    elif t.arc == 'math:cos':
        if t0 and not t0.var:
            a = math.cos(float(t0.arc))
            if unify(Triple(str(a)), c.env, t.nodes[1], c.env, 1): return 1
        elif t1 and not t1.var:
            a = math.cos(float(t1.arc))
            if unify(Triple(str(a)), c.env, t.nodes[0], c.env, 1): return 1
        else: return 0
    elif t.arc == 'math:degrees':
        if t0 and not t0.var:
            a = float(t0.arc)*180/math.pi
            if unify(Triple(str(a)), c.env, t.nodes[1], c.env, 1): return 1
        elif t1 and not t1.var:
            a = float(t0.arc)*math.pi/180
            if unify(Triple(str(a)), c.env, t.nodes[0], c.env, 1): return 1
        else: return 0
    elif t.arc == 'math:equalTo':
        if t0 and t1 and float(t0.arc) == float(t1.arc): return 1
        else: return 0
    elif t.arc == 'math:greaterThan':
        if t0 and t1 and float(t0.arc) > float(t1.arc): return 1
        else: return 0
    elif t.arc == 'math:lessThan':
        if t0 and t1 and float(t0.arc) < float(t1.arc): return 1
        else: return 0
    elif t.arc == 'math:notEqualTo':
        if t0 and t1 and float(t0.arc) != float(t1.arc): return 1
        else: return 0
    elif t.arc == 'math:notLessThan':
        if t0 and t1 and float(t0.arc) >= float(t1.arc): return 1
        else: return 0
    elif t.arc == 'math:notGreaterThan':
        if t0 and t1 and float(t0.arc) <= float(t1.arc): return 1
        else: return 0
    elif t.arc == 'math:difference' and t0:
        a = float(eval(t0.nodes[0], c.env).arc)
        ti = t0.nodes[1]
        while ti.nodes:
            a = a-float(eval(ti.nodes[0], c.env).arc)
            ti = ti.nodes[1]
        if unify(Triple(str(a)), c.env, t.nodes[1], c.env, 1): return 1
        else: return 0
    elif t.arc == 'math:exponentiation' and t0:
        a = float(eval(t0.nodes[0], c.env).arc)
        ti = t0.nodes[1]
        while ti.nodes:
            a = a**float(eval(ti.nodes[0], c.env).arc)
            ti = ti.nodes[1]
        if unify(Triple(str(a)), c.env, t.nodes[1], c.env, 1): return 1
        else: return 0
    elif t.arc == 'math:integerQuotient' and t0:
        a = float(eval(t0.nodes[0], c.env).arc)
        ti = t0.nodes[1]
        while ti.nodes:
            a = a/float(eval(ti.nodes[0], c.env).arc)
            ti = ti.nodes[1]
        if unify(Triple(str(int(a))), c.env, t.nodes[1], c.env, 1): return 1
        else: return 0
    elif t.arc == 'math:negation':
        if t0 and not t0.var:
            a = -float(t0.arc)
            if unify(Triple(str(a)), c.env, t.nodes[1], c.env, 1): return 1
        elif t1 and not t1.var:
            a = -float(t1.arc)
            if unify(Triple(str(a)), c.env, t.nodes[0], c.env, 1): return 1
        else: return 0
    elif t.arc == 'math:product' and t0:
        a = float(eval(t0.nodes[0], c.env).arc)
        ti = t0.nodes[1]
        while ti.nodes:
            a = a*float(eval(ti.nodes[0], c.env).arc)
            ti = ti.nodes[1]
        if unify(Triple(str(a)), c.env, t.nodes[1], c.env, 1): return 1
        else: return 0
    elif t.arc == 'math:quotient' and t0:
        a = float(eval(t0.nodes[0], c.env).arc)
        ti = t0.nodes[1]
        while ti.nodes:
            a = a/float(eval(ti.nodes[0], c.env).arc)
            ti = ti.nodes[1]
        if unify(Triple(str(a)), c.env, t.nodes[1], c.env, 1): return 1
        else: return 0
    elif t.arc == 'math:remainder' and t0:
        a = float(eval(t0.nodes[0], c.env).arc)
        ti = t0.nodes[1]
        while ti.nodes:
            a = a%float(eval(ti.nodes[0], c.env).arc)
            ti = ti.nodes[1]
        if unify(Triple(str(a)), c.env, t.nodes[1], c.env, 1): return 1
        else: return 0
    elif t.arc == 'math:rounded':
        if t0 and not t0.var:
            a = round(float(t0.arc))
            if unify(Triple(str(a)), c.env, t.nodes[1], c.env, 1): return 1
        else: return 0
    elif t.arc == 'math:sin':
        if t0 and not t0.var:
            a = math.sin(float(t0.arc))
            if unify(Triple(str(a)), c.env, t.nodes[1], c.env, 1): return 1
        elif t1 and not t1.var:
            a = math.asin(float(t1.arc))
            if unify(Triple(str(a)), c.env, t.nodes[0], c.env, 1): return 1
        else: return 0
    elif t.arc == 'math:sum' and t0:
        a = float(eval(t0.nodes[0], c.env).arc)
        ti = t0.nodes[1]
        while ti.nodes:
            a = a+float(eval(ti.nodes[0], c.env).arc)
            ti = ti.nodes[1]
        if unify(Triple(str(a)), c.env, t.nodes[1], c.env, 1): return 1
        else: return 0
    elif t.arc == 'math:tan':
        if t0 and not t0.var:
            a = math.tan(float(t0.arc))
            if unify(Triple(str(a)), c.env, t.nodes[1], c.env, 1): return 1
        elif t1 and not t1.var:
            a = math.atan(float(t1.arc))
            if unify(Triple(str(a)), c.env, t.nodes[0], c.env, 1): return 1
        else: return 0
    elif t.arc == 'rdf:first' and t0 and t0.arc == '.' and t0.nodes != []:
        if unify(t0.nodes[0], c.env, t.nodes[1], c.env, 1): return 1
        else: return 0
    elif t.arc == 'rdf:rest' and t0 and t0.arc == '.' and t0.nodes != []:
        if unify(t0.nodes[1], c.env, t.nodes[1], c.env, 1): return 1
        else: return 0
    elif t.arc == 'a' and t1 and t1.arc == 'rdf:List' and t0 and t0.arc == '.':
        return 1
    elif t.arc == 'a' and t1 and t1.arc == 'rdfs:Resource': return 1
    else: return -1

def tokenize(s, sep, all=1):
    n = 0
    sq = False
    dq = False
    ls = len(sep)
    if s == '': return []
    for i in range(len(s)):
        c = s[i]
        if n <= 0 and not sq and not dq and s[i:i+ls] == sep:
            if s[i] == '.' and s[i+1].isdigit() and s[i-1].isdigit(): continue
            elif all and s[:i] != '': return [s[:i]]+tokenize(s[i+ls:], sep)
            elif all and s[:i] == '': return tokenize(s[i+ls:], sep)
            elif s[:i] != '': return [s[:i], s[i+ls:]]
            else: return [s[i+ls:]]
        elif c == '(': n = n+1
        elif c == ')': n = n-1
        elif c == '\'': sq = not sq
        elif c == '"': dq = not dq
    return [s]

def run(args):
    global rules, step, why, once, forever, debug
    rules = {}
    np = {}
    np['log:'] = '<http://www.w3.org/2000/10/swap/log#>'
    np['math:'] = '<http://www.w3.org/2000/10/swap/math#>'
    np['owl:'] = '<http://www.w3.org/2002/07/owl#>'
    np['rdf:'] = '<http://www.w3.org/1999/02/22-rdf-syntax-ns#>'
    np['rdfs:'] = '<http://www.w3.org/2000/01/rdf-schema#>'
    np['xsd:'] = '<http://www.w3.org/2001/XMLSchema#>'
    triple = 0
    goals = []
    why = False
    once = False
    forever = False
    debug = False
    ts = time.time()
    for arg in args:
        if arg[:2] == '--': arg = arg[1:]
        if arg == '-why': why = True
        elif arg == '-once': once = True
        elif arg == '-forever': forever = True
        elif arg == '-debug': debug = True
        elif arg == '': pass
        else:
            f = urllib.urlopen(arg)
            while True:
                s = f.readline()
                if s == '': break
                s = s.strip()
                if s == '': continue
                elif s[0] == '#': continue
                elif s.find('@prefix') != -1:
                    t = tokenize(s.strip('.'), ' ')
                    if np.get(t[1]) and np[t[1]] != t[2]:
                        sys.stderr.write('#FAIL @prefix %s %s.\n'%(t[1], t[2]))
                        break
                    else: np[t[1]] = t[2]
                elif s.find('=> []') != -1:
                    goals.append(Rule(s.strip('.')))
                else:
                    r = Rule(s.strip('.'))
                    if not rules.get(r.head.arc): rules[r.head.arc] = []
                    rules[r.head.arc].append(r)
                    triple = triple+1
    step = 0
    ev = ''
    v = ''
    for n in np: v = v+'@prefix '+n+' '+np[n]+'.\n'
    for g in goals: ev = ev+'\n'+prove(g)
    if not forever: v = v+ev
    elif forever:
        reorder(goals, ev)
        v = v+'\n'
        for h in rules:
            for r in rules[h]: v = v+str(r)+'.\n'
        for g in goals: v = v+str(g)+'.\n'
    print v
    sys.stderr.write('#ENDS %s [%s triples] [%s steps/%s sec]\n' %
          (args[-1], triple, step, time.time()-ts))
    return v

def run_called(str):
    global rules, step, why, once, forever, debug
    rules = {}
    np = {}
    np['log:'] = '<http://www.w3.org/2000/10/swap/log#>'
    np['math:'] = '<http://www.w3.org/2000/10/swap/math#>'
    np['owl:'] = '<http://www.w3.org/2002/07/owl#>'
    np['rdf:'] = '<http://www.w3.org/1999/02/22-rdf-syntax-ns#>'
    np['rdfs:'] = '<http://www.w3.org/2000/01/rdf-schema#>'
    np['xsd:'] = '<http://www.w3.org/2001/XMLSchema#>'
    triple = 0
    goals = []
    why = False
    once = False
    forever = False
    debug = False
    ts = time.time()
    s = ''
    for s in str.split('\n'):
        if s == '': continue
        elif s[0] == '#': continue
        elif s.find('@prefix') != -1:
            t = tokenize(s.strip('.'), ' ')
            if np.get(t[1]) and np[t[1]] != t[2]:
                sys.stderr.write('#FAIL @prefix %s %s.\n'%(t[1], t[2]))
                break
            else: np[t[1]] = t[2]
        elif s.find('=> []') != -1:
            goals.append(Rule(s.strip('.')))
        else:
            r = Rule(s.strip('.'))
            if not rules.get(r.head.arc): rules[r.head.arc] = []
            rules[r.head.arc].append(r)
            triple = triple+1
    step = 0
    ev = ''
    v = ''
    for n in np: v = v+'@prefix '+n+' '+np[n]+'.\n'
    for g in goals: ev = ev+'\n'+prove(g)
    if not forever: v = v+ev
    elif forever:
        reorder(goals, ev)
        v = v+'\n'
        for h in rules:
            for r in rules[h]: v = v+str(r)+'.\n'
        for g in goals: v = v+str(g)+'.\n'
    return v

if __name__ == '__main__':
    try:
        import psyco
        if str(sys.modules['__main__']).find('profile.py') == -1: psyco.full()
    except ImportError: pass
    if len(sys.argv) == 1:
        print 'Usage: python euler.py [--why] [--once] [--debug] triples'
    else: run(sys.argv[1:])
