import sys, cPickle, pydot, sets, getopt

k = file('../rfc-data/rfc-data.pickle')
data = cPickle.load(k)
types = ['refs', 'obs', 'upd', 'seealso']
intypes = ['refed', 'updby', 'obsby', 'seealso']

def appendreftypes(rfc, types):
    allrefs = []
    for i in types:
        if rfc.has_key(i):
            allrefs = allrefs + rfc[i]
    return allrefs

def routes_from_node(data, start):
    states = [start]
    done = {}
    lvl = 0
    while states != []:
        newstates = []
        for i in states:
            for child in appendreftypes(data[i], types):
                if child not in done.keys():
                    newstates.append(child)
                    done[child] = i
        states = newstates
    return done

def find_path(data, start, end, path=[]):
    global types
    path = path + [start]
    if start == end:
        return path
    # The only way a former rfc can ref later is that they
    # were published together with a 'seealso' note on each other
    # This greatly simplifies some comparisons
    if int(start) < int(end):
        if data[start].has_key('seealso'):
            if end in data[start]['seealso']:
                return path + [end]
        return None
    if not data.has_key(start):
        return None
    for node in appendreftypes(data[start], types):
        if node not in path:
            newpath = find_path(data, node, end, path)
            if newpath:
                return newpath
    return None
            
def numberatize(data, start, types):
    """Number the nodes by nimimum distance to the start node. 
    Return dictionary of nodes and distances"""
    nodes = sets.Set()
    nodes.add(start)

    numbered = dict()
    num = 0
    while nodes:
        newnodes = sets.Set()
        for node in nodes:
            if node not in numbered:
                numbered[node] = num
                newnodes.update(appendreftypes(data[node], types))
        num += 1
        nodes = newnodes
    return numbered

def backtrackatize(data, numbered, start, types):
    """Backtrack from a node to the starting point, numbered
    zero. Return a list of all the paths between these points."""
    path = [start]
    num = numbered[start]
    current = start
    
    while num > 0:
        num -= 1
        for parent in appendreftypes(data[current], types):
            if parent in numbered and numbered[parent] == num:
                current = parent
                path.insert(0, current)
                break
    return path

# 2407,822,680

# default values
output = 'gv'
cycles = 1
shortest = 0

# here goes.. argument handling
try:
    opts, rest = getopt.getopt(sys.argv[1:], 'nsp',
                               ['nocycles', 'shortest', 'pajek'])
except getopt.error, what:
    sys.exit(str(what))

for o, a in opts:
    if o in ('-p', '--pajek'):
        output = 'pajek'
    if o in ('-s', '--shortest'):
        # shortest path will contain no cycles...
        shortest = 1
        cycles = 0
        continue
    if o in ('-n', '--nocycles'):
        cycles = 0

if len(rest) < 1:
    sys.exit(2)

path = rest[0].split(',')
if len(path) < 2:
    sys.exit(2)

# [1,2,3] -> [(1,2),(2,3)]
chain = zip(path, path[1:])

# add all paths here
paths = []

for pair in chain:
    if data.has_key(pair[1]):
        # if end node is unreachable -> next path
        if appendreftypes(data[pair[1]], intypes) == []:
            continue
        else:
            startnum = numberatize(data, pair[0], types)
            endnum = numberatize(data, pair[1], intypes)            

            for middle in startnum:
                if middle not in endnum:
                    continue
                startpath = backtrackatize(data, startnum, middle, intypes)
                endpath = backtrackatize(data, endnum, middle, types)

                # this prevents the short cycles:
                # if cycles are possible and if one exists -> next path
                if cycles == 0:
                    if len(startpath) > 1 and len(endpath) > 1:
                        if startpath[-2] == endpath[-2]:
                            continue
                
                endpath.reverse()
                paths.append(startpath+endpath[1:])

if len(paths) == 0:
    sys.exit(0)

if shortest:
    shortest_paths = {}
    for idx, path in enumerate(paths):
        # go through paths between endpoints,
        # save len and idx of shortest paths
        endpoints = path[0] + path[-1]
        if shortest_paths.has_key(endpoints):
            if shortest_paths[endpoints][1] > len(path):
                shortest_paths[endpoints] = (idx, len(path))
        else:
            shortest_paths[endpoints] = (idx, len(path))

    # include only shortest paths
    newpaths = []
    for i in shortest_paths.keys():
        newpaths.append(paths[shortest_paths[i][0]])
    paths = newpaths

if output == 'pajek':
    nodes = sets.Set()
else:
    g = pydot.Graph(rankdir='LR')
                
pairs = sets.Set()
for i in paths:
    # [1,2,3] -> [(1,2),(2,3)]
    pairs.update(zip(i, i[1:]))

    if output == 'pajek':
        for j in i:
            nodes.add(j)

if output == 'pajek':
    # make new indices for nodes, starting from 0
    # add their names after them
    print "*Vertices " + str(len(nodes)) + '\x0d'
    pajek_idx = {}
    for i, j in enumerate(list(nodes)):
        i = str(i+1)
        print i + ' "rfc' + j + '"' + '\x0d'
        pajek_idx[j] = i
                
    print "*Arcs" + '\x0d'
                
for j in pairs:
    if output == 'pajek':
        # arcs use pajek indices
        print pajek_idx[j[0]]  + " " + pajek_idx[j[1]] + '\x0d'
    else:
        g.add_edge(pydot.Edge(*j))

if output != 'pajek':
    print g.to_string()
