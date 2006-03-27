import readline
from copy import copy, deepcopy

db = []

class Term(object):
    _nm = 0

    def __init__(self):
        self._numstr = '?' + str(Term._nm) 
        Term._nm += 1

    def __repr__(self):
        return self._numstr

def is_bound(var, env):
    return isinstance(var, Term) and env.has_key(var)

def unify_var(var, val, env = None):
    if env is None:
        env = dict()
    
    # if variable bound, value must match
    # print "unify var " + str(var) + " with val " + \
    #       str(val) + " in env " + str(env)

    if is_bound(var, env):
        return unify(env[var], val, env)
    # If match to something that is bound, the value must match
    elif is_bound(val, env):
        return unify(var, env[val], env)
    # new binding
    else:
        env[var] = val
        return env

def unify(term1, term2, env = None):
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
        return unify_var(term1, term2, env)
    # value is unified, the other way around
    elif isinstance(term2, Term):
        return unify_var(term2, term1, env)
    # handle rule lists
    elif (isinstance(term1, list) and isinstance(term2, list) and
          term1 != [] and term2 != []):
        return unify(term1[1:], term2[1:], unify(term1[0], term2[0], env))
    # non-matching terms
    else:
        return False

# Replace all variables with their values
def substitute(exp, env):
    if env is False:
        return False
    elif is_bound(exp, env):
        return substitute(env[exp], env)
    elif isinstance(exp, list):
        return map(lambda x: substitute(x, env), exp)
    else:
        return exp

def prove_term_with_rule(goal, rule, env, sc, fa):
    print "prove_term_with_rule", goal, rule
    # re-instantiate rule
    rule = deepcopy(rule)
    head = rule[0]
    subgoals = rule[1:]
    # try to bind variable into new environment
    env = copy(env)
    newenv = unify(head, goal, env)
    # Backtrack if needed
    if newenv is False:
        print "fail from prove_term_with_rule"
        return fa()
    else:
        # try to prove rest in a new environment
        k = copy(env)
        k.update(newenv)
        return prove_terms(subgoals, k, sc, fa)

def prove_terms(goals, env, sc, fa):
    print "prove_terms", goals
    # If successful i.e. terms to be solved empty, call success
    if goals == []:
        print "success from prove_terms"
        return sc(env, fa)
    else:
        # prove one, if successful, carry on with rest
        def new_success(env, fa):
            print "new_success back in prove_terms!"
            return prove_terms(goals[1:], env, sc, fa)
        return prove_term(goals[0], env, new_success, fa)

def prove_term(goal, env, sc, fa):
    print "prove_term", goal
    goal = substitute(goal, env)
    print "->prove_term", goal
    def prove_part(db):
        if db == []:
            print "fail from prove_part"
            return fa()
        else:
            # new failure - try to prove rest
            def new_failure():
                print "new_failure back in prove_part! More stuff in from db!", db[1:]
                return prove_part(db[1:])
            print "in prove_part, trying to prove", db[0]
            return prove_term_with_rule(goal, db[0], env, sc, new_failure)
    return prove_part(db)
        
def solve_term(goal):
    def success(env, fa):
        print "Success ", substitute(goal, env), env
        # We've had results, no more
        if fa is failure:
            print "No more results"
        # try to get more results with the failure function
        else:
            print "Fail from solve_term, get more data!", goal
            print
            return fa()
    # Default failure - no results
    def failure():
        return "Out of results"
    return prove_term(goal, {}, success, failure)

# Map query strings to variables
def instantiate_terms(inp):
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
    inp = instantiate_terms(inp)
    if inp[0] == 'fact':
        db.append(inp[1:])
        print "Saved " + str(inp[1]) + "..."
    else:
        print solve_term(inp)
        
    repl()

if __name__ == '__main__':
    repl()
