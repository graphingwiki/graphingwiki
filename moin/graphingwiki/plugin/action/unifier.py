
from copy import copy, deepcopy

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
        self.loaded = set()

    def get_facts(self, goal):
        if isinstance(goal[0], Term):
            db = get_all_facts(self.request)
        else:
            db = get_page_fact(self.request, goal[0])
        for x in db:
            yield [x]

    def is_bound(self, var, env):
        return isinstance(var, Term) and env.has_key(var)

    def unify_var(self, var, val, env = None):
        if env is None:
            env = dict()

        # if variable bound, value must match
        # print "unify var " + str(var) + " with val " + \
        #       str(val) + " in env " + str(env)

        if self.is_bound(var, env):
            return unify(env[var], val, env)
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
        elif (isinstance(term1, list) and isinstance(term2, list) and
              term1 != [] and term2 != []):
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

    def prove_term_with_rule(self, goal, rule, env, sc, fa):
        # re-instantiate rule
        rule = deepcopy(rule)
        head = rule[0]
        subgoals = rule[1:]
        # try to bind variable into new environment
        env = copy(env)
        newenv = self.unify(head, goal, env)
        # Backtrack if needed
        if newenv is False:
            return fa()
        else:
            # try to prove rest in a new environment
            k = copy(env)
            k.update(newenv)
            return self.prove_terms(subgoals, k, sc, fa)

    def prove_terms(self, goals, env, sc, fa):
        # If successful i.e. terms to be solved empty, call success
        if goals == []:
            return sc(env, fa)
        else:
            # prove one, if successful, carry on with rest
            def new_success(env, fa):
                return self.prove_terms(goals[1:], env, sc, fa)
            return self.prove_term(goals[0], env, new_success, fa)

    def prove_term(self, goal, env, sc, fa):
        db = self.get_facts(goal)

        goal = self.substitute(goal, env)
        def prove_part(db):
            try:
                data = db.next()
            except StopIteration:
                return fa()

            # new failure - try to prove rest
            def new_failure():
                return prove_part(db)
            return self.prove_term_with_rule(goal, data, env, sc, new_failure)
        return prove_part(db)

    def solve_term(self, goal):
        def success(env, fa):
            print "Success ", self.substitute(goal, env), env
            # We've had results, no more
            if fa is failure:
                print "No more results"
            # try to get more results with the failure function
            else:
                return fa()
        # Default failure - no results
        def failure():
            return "Out of results"
        return self.prove_term(goal, {}, success, failure)

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
    def repl():
        inp = input('Fact/query? ')
        inp = self.instantiate_terms(inp)
        if inp[0] == 'fact':
            database.append(inp[1:])
            print "Saved " + str(inp[1]) + "..."
        else:
            print solve_term(inp)

        repl()

if __name__ == '__main__':
    Unifier().repl()
