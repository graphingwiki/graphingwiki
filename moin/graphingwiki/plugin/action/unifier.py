# -*- coding: iso-8859-1 -*-
"""
    Prolog-style unifier class

    @copyright: 2006 by Juhani Eronen <exec@iki.fi>, 
                        Aki Helin and Joachim Viide
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>

    Permission is hereby granted, free of charge, to any person
    obtaining a copy of this software and associated documentation
    files (the "Software"), to deal in the Software without
    restriction, including without limitation the rights to use, copy,
    modify, merge, publish, distribute, sublicense, and/or sell copies
    of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be
    included in all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
    EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
    MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
    NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
    HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
    WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
    DEALINGS IN THE SOFTWARE.

"""

from copy import copy, deepcopy

from graphingwiki.patterns import GraphData

from N3Dump import get_page_fact, get_all_facts

class Term(object):
    _nm = 0

    def __init__(self):
        self._numstr = '?' + str(Term._nm) 
        Term._nm += 1

    def __repr__(self):
        return self._numstr

class Unifier(object):
    def __init__(self, request):
        self.request = request
        if request:
            self.graphdata = GraphData(request)
        self.loaded = []
        self.all_loaded = 0
        self.backlog = []

        self.rules = []

    def add_rule(self, inp):
        inp = self.instantiate_terms(inp)
        self.rules.append(inp[1:])

    def solve(self, query):
        solutions = set()
        for x in self.solve_term(self.instantiate_terms(query)):
            solutions.add(repr(x))

        for x in solutions:
            yield x

    # Skeleton routine for optimisation
    def get_facts_basic(self, goal):
        db = None
        
        if isinstance(goal[0], Term):
            db = get_all_facts(self.request, self.graphdata)
        else:
            db = get_page_fact(self.request, goal[0], self.graphdata)

        for r in self.rules:
            yield r

        for x, y in db:
            yield [x]

    # A quite crappy attempt. I say!
    def get_facts(self, goal):
        db = None
        term_fact = isinstance(goal[0], Term)

        if term_fact:
            if not self.all_loaded:
                db = get_all_facts(self.request, self.graphdata)
        else:
            if not self.all_loaded and goal[0] not in self.loaded:
                db = get_page_fact(self.request, goal[0], self.graphdata)

        for r in self.rules:
            yield r

        if db:
            for x, y in db:
                if x not in self.backlog:
                    self.backlog.append(x)
                yield [x]

            if term_fact:
                self.all_loaded = 1
            else:
                self.loaded.append(goal[0])
                
        elif term_fact:
            for val in self.backlog:
                yield [val]
        else:
            for val in self.backlog:
                if val[0] == goal[0]:
                    yield [val]

    def is_bound(self, var, env):
        return isinstance(var, Term) and env.has_key(var)

    def unify_var(self, var, val, env = None):
        if env is None:
            env = dict()

        # if variable bound, value must match
        # print "unify var " + str(var) + " with val " + \
        #       str(val) + " in env " + str(env)

        if self.is_bound(var, env):
            # occurs-check
            if self.is_bound(val, env):
                if env[var] == env[val]:
                    return env
            return self.unify(env[var], val, env)
        # If match to something that is bound, the value must match
        elif self.is_bound(val, env):
            return self.unify(var, env[val], env)
        # new binding
        else:
            env[var] = val
            return env

    def unify(self, term1, term2, env = None):
        if env is None:
            env = dict()

        # print "unify " + str(term1) + " with val " + \
        #       str(term2) + " in env " + str(env)

        # If all has failed
        if env is False:
            return False
        # trivial case
        elif term1 == term2:
            return env
        # variable is unified if it has a proper value or is unbound
        elif isinstance(term1, Term):
            return self.unify_var(term1, term2, env)
        # value is unified, the other way around
        elif isinstance(term2, Term):
            return self.unify_var(term2, term1, env)
        # handle rule lists
        elif (isinstance(term1, list) and term1 and
              isinstance(term2, list) and term2):
            return self.unify(term1[1:], term2[1:],
                              self.unify(term1[0], term2[0], env))
        # non-matching terms
        else:
            return False

    # Replace all variables with their values
    def substitute(self, exp, env):
        if env is False:
            return False
        elif self.is_bound(exp, env):
            return self.substitute(env[exp], env)
        elif isinstance(exp, list):
            return map(lambda x: self.substitute(x, env), exp)
        else:
            return exp

    def prove_term_with_rule(self, goal, rule, env):
        # re-instantiate rule
        rule = deepcopy(rule)
        head = rule[0]
        subgoals = rule[1:]

        # try to bind variable into new environment
        env = copy(env)
        newenv = self.unify(head, goal, env)

        if newenv is False:
            return

        # try to prove rest in a new environment
        env = copy(env)
        env.update(newenv)
        for env in self.prove_terms(subgoals, env):
            yield env

    def prove_terms(self, goals, env):
        # If successful i.e. terms to be solved empty, call success
        # and end the misery
        if not goals:
            yield env
            return
        
        for env in self.prove_term(goals[0], env):
            for newenv in self.prove_terms(goals[1:], env):
                yield newenv

    def prove_term(self, goal, env):
        goal = self.substitute(goal, env)

        for data in self.get_facts(goal):
            for newenv in self.prove_term_with_rule(goal, data, env):
                yield newenv

    def solve_term(self, goal):
        for env in self.prove_term(goal, {}):
            result = self.substitute(goal, env)
            yield result, env

    # Map query strings to variables
    def instantiate_terms(self, inp):
        vars = {}
        def instantiate(item):
            if isinstance(item, basestring) and item.startswith('?'):
                if not vars.has_key(item):
                    vars[item] = Term()
                return vars[item]
            elif isinstance(item, list):
                return map(instantiate, item)
            else:
                return item

        return instantiate(inp)

    # read evaluate print loop
    def repl(self):
        self.get_facts = self.get_facts_repl
        inp = input('Fact/query? ')
        inp = self.instantiate_terms(inp)
        if inp[0] == 'fact':
            self.rules.append(inp[1:])
            print "Saved " + str(inp[1]) + "..."
        else:
            for result, env in self.solve_term(inp):
                print "Success ", result, env
            print "Out of results"
        self.repl()

    def get_facts_repl(self, goal):
        for val in self.rules:
            yield val

if __name__ == '__main__':
    Unifier(None).repl()
    
