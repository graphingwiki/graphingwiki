#!/usr/bin/env python

from random import seed, choice
import os, sys, pydot, cPickle, time, getopt, sets
from colorsys import *

#basedir = '/home/secpelle/method-thesis/soft-devel/'
#baseurl = 'print.cgi?proto='

# Used standard type abbreviations, names and alt texts

statuslabels = {'S': 'Standard', 'PS': 'Proposed Standard',
                'I': 'Informational', 'E': 'Experimental',
                'H': 'Historic', 'DS': 'Draft Standard',
                'N': 'None'}

statustext = {'S': "Specification with significant implementation \
and successful operational experience.",
              'DS': "Specification with operational experience and \
at least two interoperable implementations.",
              'PS': "Stable specification that has received \
significant community review.",
              'E': "Part of a research or development effort, \
submitted for information or archival.",
              'I': "General information, does not represent an \
consensus or recommendation.",
              'H': "Obsolete or superseded by a more recent \
specification.",
              'N': "No specification status listed."}

# dependency type abbreviations and names

typelabels = {'R': ['Reference', 'ReferenceFrom', 'seealso'],
              'O': ['Obsolete', 'ObsoleteFrom'],
              'U': ['Update', 'UpdateFrom']}

typetext = {'seealso': 'References',
            'Reference': 'References', 'ReferenceFrom': 'References',
            'Obsolete': 'Obsoletes', 'ObsoleteFrom': 'Obsoletes',
            'Update': 'Updates', 'UpdateFrom': 'Updates'}

## reftypes and inreftypes are the variables that contain the
## dependency types that will be used by the graph-generating methods:
## reftypes reference, inreftypes are referenced

# order of types significant as some rfc:s both ref and obs|upd, only
# one line between two nodes is allowed and only the latest changes
# remain in effect

reftypes = ['Reference', 'seealso', 'Update', 'Obsolete']
inreftypes = ['ReferenceFrom', 'seealso', 'UpdateFrom', 'ObsoleteFrom']

# a selection of dot colors

dotcolors = ["aquamarine1", "bisque", "blue", "brown4", "burlywood",
"chocolate3", "cornflowerblue", "crimson", "cyan", "darkkhaki",
"darkolivegreen3", "darksalmon", "darkseagreen", "darkslateblue",
"darkslategray", "darkviolet", "deeppink", "deepskyblue", "gray33",
"forestgreen", "gold2", "goldenrod", "gray", "green", "greenyellow",
"hotpink", "indigo", "lavender", "lightpink", "lightsalmon",
"lightseagreen", "lightskyblue", "lightsteelblue", "limegreen",
"magenta", "maroon", "mediumaquamarine", "mediumorchid1",
"mediumpurple", "mediumseagreen", "olivedrab", "orange", "orangered",
"palegoldenrod", "palegreen", "palevioletred", "peru", "plum",
"powderblue", "red2", "rosybrown", "royalblue4", "salmon",
"slategray", "springgreen", "steelblue", "tomato3", "turquoise",
"violetred", "yellow", "yellowgreen"]

colors = dotcolors
used_colors = []
used_colorlabels = []

# another color generation method, not used right now

hue = [17, 30, 45, 55, 70, 85, 120, 150, 170, 210, 250, 270, 310, 340, 5]

def gencolors():
    global colors
    for i in hue:
        h = i/360.
        l = 0.7
        s = 1.0
        r, g, b = hls_to_rgb(h, l, s)
        colors.append("#%02X%02X%02X" % (int(r*255), int(g*255), int(b*255)))
        l = 0.5
        r, g, b = hls_to_rgb(h, l, s)
        colors.append("#%02X%02X%02X" % (int(r*255), int(g*255), int(b*255)))
        l = 0.4
        r, g, b = hls_to_rgb(h, l, s)
        colors.append("#%02X%02X%02X" % (int(r*255), int(g*255), int(b*255)))
    for r in range(120, 230, 35):
        colors.append("#%02X%02X%02X" % (r, r, r))

#gencolors()

highlightcolors = []

# Names for different cryptic standards markings
#           S, PS, I, E, H, DS

# global list of rfc:s whose refs are yet to be handled
unhandled = []

# global dict of rfc:s per year
per_year = {}

# global limit of standard types
limit = []

# Da graph. Years laid separately, left to right. Nodes are boxes.
# "If clusterrank is "local", a subgraph whose name begins with
#  "cluster" is given special treatment. The subgraph is laid out
#  separately, and then integrated as a unit into its parent graph,"
# -Dot reference
graph = pydot.Dot(clusterrank='local', rankdir='LR', compound='true')

# another for ledgend about pruned nodes
legend_pruned = pydot.Cluster('legend_pruned',
                              label="Legend: pruned edges")
graph.add_subgraph(legend_pruned)

# A special cluster for legend section about
# rfc-statuses and edge types
legend = pydot.Cluster('legend', label="Legend: specification and link types")
graph.add_subgraph(legend)

def hashcolor(string):
    if string in used_colorlabels:
        return used_colors[used_colorlabels.index(string)]

    seed(string)
    cl = choice(colors)
    while cl in used_colors:
        cl = choice(colors)
    used_colors.append(cl)
    used_colorlabels.append(string)
    return cl

# Add notes on the rfc publication years.
def add_to_years(rfc):
    key = 'Year' + rfc['Year']
    if per_year.has_key(key):
        per_year[key].add(rfc['number'])
    else:
        per_year[key] = set([rfc['number']])

# Generate graph ordering based on the collected publication year data
# pf the rfcs present in the graph. This is done adding rfcs per year
# to subgraphs that have the attribute 'rank=same'.
def add_years_to_graph():
    global graph, per_year

    prev_year = None
    for year in sorted(per_year.keys()):
        sg = pydot.Subgraph(graph_name=year, rank='same')
        sg.add_node(pydot.Node(year))

        for rfc in per_year[year]:
            sg.add_node(pydot.Node(rfc))
        graph.add_subgraph(sg)

        graph.add_node(pydot.Node(year, group='Year',
                                  shape='plaintext'))
        if prev_year is not None:
            graph.add_edge(pydot.Edge(prev_year, year, dir='none',
                                      minlen=1,
                                      style='invis', weight=10))
        prev_year = year

# Check a certain node has references, updates etc., create edges to/from
# (depending on the inout arg) these new nodes and mark them unhandled.
def gimme_edges(data, whom, reason, inout, **args):
    global graph, unhandled, limit

    if whom.has_key(reason):
        for i in whom[reason]:
            # limit-arg: Don't allow edges from rfcs with certain status
            if data[i].has_key('Status'):
                if data[i]['Status'] in limit:
                    continue
            # Don't allow statusless if limited
            elif 'N' in limit:
                continue
            unhandled.append(i)
            if inout == 'out':
                # If edge already exists, just update parameters
                if graph.get_edge(whom['number'], i) is None:
                    graph.add_edge(pydot.Edge(whom['number'], i, **args))
                else:
                    graph.get_edge(whom['number'], i).__setstate__(args)
            elif inout == 'in':
                if graph.get_edge(i, whom['number']) is None:
                    graph.add_edge(pydot.Edge(i, whom['number'], **args))
                else:
                    graph.get_edge(i, whom['number']).__setstate__(args)

# See if certain rfc status does not yet have a legend node, if not,
# make one
def add_statusnode(status, statuscolor):
    global legend

    if legend.get_node(status) is None:
        legend.add_node(pydot.Node(status, style='filled',
                                   fillcolor=statuscolor,
                                   label=statuslabels[status],
                                   tooltip=statustext[status],
                                   URL='http://www.ietf.org/rfc/rfc2026.txt'))

# Nicer layout when all the standard type nodes in legend are bound
# with invisible edges. Edge types includes also.
def tie_statusnodes():
    global graph, legend

    prev = None
    for i in legend.get_node_list():
        if prev is not None:
            legend.add_edge(pydot.Edge(prev.name, i.name, dir='none',
                                       style='invis'))
        prev = i

    # The edge types (3) are, as of yet, hardcoded in the legend, below 
    legend.add_edge(pydot.Edge("viivatyyppi1", "viivatyyppi1",
                               color=hashcolor('Obsoletes'),
                               label='Obsoletes'))
    legend.add_edge(pydot.Edge("viivatyyppi2", "viivatyyppi2",
                               color=hashcolor('References'),
                               label='References'))
    legend.add_edge(pydot.Edge("viivatyyppi3", "viivatyyppi3",
                               color=hashcolor('Updates'),
                               label='Updates'))
    legend.get_node("viivatyyppi1").set_style("invis")
    legend.get_node("viivatyyppi2").set_style("invis")
    legend.get_node("viivatyyppi3").set_style("invis")
    legend.add_edge(pydot.Edge("viivatyyppi1", "viivatyyppi2",
                               style='invis'))
    legend.add_edge(pydot.Edge("viivatyyppi2", "viivatyyppi3",
                               style='invis'))

# Add a node to graph by its rfc data struct. Called by spread_from_node
def add_rfcnode(rfc):
    global graph
#    global baseurl
    numb = rfc['number']
    add_to_years(rfc)

    if rfc.has_key('proto'):
        labelstr = "rfc" + numb + " " + rfc['proto']
    else:
        labelstr = "rfc" + numb

    if rfc.has_key('Status'):
        status = rfc['Status']
        statuscolor = hashcolor(status)
    else:
        status = 'N'
        statuscolor = "white"

    add_statusnode(status, statuscolor)

    graph.add_node(pydot.Node(numb, style='filled',
                              fillcolor=statuscolor,
                              label=labelstr,
                              URL="http://www.ietf.org/rfc/rfc" +
                              numb + ".txt",
                              # URL=baseurl + numb,
                              tooltip=rfc['Name']))

# For noded that have already been added ot graph by being assigned as
# edge endpoints, but that have no attributes
def change_rfcnode(rfc):
    global graph
#    global baseurl
    add_to_years(rfc)

    olmi = graph.get_node(rfc['number'])
    
    if rfc.has_key('Status'):
        status = rfc['Status']
        statuscolor = hashcolor(status)
    else:
        status = 'N'
        statuscolor = "white"
    
    add_statusnode(status, statuscolor)

    olmi.set_style('filled')
    olmi.set_fillcolor(statuscolor)

    if rfc.has_key('proto'):
        olmi.set_label("rfc" + rfc['number'] + " " + rfc['proto'])
    else:
        olmi.set_label("rfc" + rfc['number'])

    olmi.set_URL("http://www.ietf.org/rfc/rfc" + rfc['number'] + ".txt")
#    olmi.set_URL(baseurl + rfc['number'])
    olmi.set_tooltip(rfc['Name'])

# Start from a node, add node and all reference edges (adds nodes
# also), add attributes to added nodes.
def spread_from_node(rfc, data):
    global graph, typetext, reftypes, inreftypes
    
    if graph.get_node(rfc['number']) is None:
        add_rfcnode(rfc)
    else:
        change_rfcnode(rfc)

    # possible keys: number, status, name, stdtype, refs, refed,
    #                obs, obsby, upd, updby, seealso, proto

    for linktype in reftypes:
        gimme_edges(data, rfc, linktype, 'out',
                    color=hashcolor(typetext[linktype]),
                    comment=typetext[linktype])

    for linktype in inreftypes:
        gimme_edges(data, rfc, linktype, 'in',
                    color=hashcolor(typetext[linktype]),
                    comment=typetext[linktype])

    for i in unhandled:
        change_rfcnode(data[i])

    return unhandled

# Get counts on the in/out-fanning of nodes
def getedgecounts():
    global graph
    
    src = []
    for dir in ['src', 'dst']:
        for i in graph.edge_list:
            if not i.__get_attribute__(dir).startswith('Year'):
                src.append(dir + "," +
                           i.__get_attribute__(dir) +
                           "," + i.comment)
    srccnt = []
    for i in set(src):
        srccnt.append(src.count(i))
    return list(set(src)), srccnt

def del_graph_edge(graph_edge):
    # pydot does not have this method, that's why all this jazz is
    # needed. Node/edge data lies in many places in graph
    global graph
    for i, j in enumerate(graph.sorted_graph_elements):
        if type(j) == pydot.Edge:
            if graph_edge.__eq__(j):
                del graph.sorted_graph_elements[i]
    graph.edge_list.remove(graph_edge)
    src = 0
    dst = 0
    for i in graph.edge_list:
        if i.src == graph_edge.src:
            src += 1
        if i.dst == graph_edge.dst:
            src += 1
    if src == 1:
        graph.edge_src_list.remove(graph_edge.src)
    if dst == 1:
        graph.edge_dst_list.remove(graph_edge.dst)

# Remove from graph the edges that create the maximum fanning
def remove_edges(maxedge):
    global graph
    no_pruned = 0
    refnode = None
    delnode = None

    dir, number, type = maxedge.split(',')

    # if there are 10 lines with x as source, all the destinations
    # must be tagged as referenced by x.
    # Conversely,
    # if there are 10 lines with x as dst, all the source nodes must
    # be tagged to reference x.
    drev = {'src': 'dst', 'dst': 'src'}
    dellist = []
    for i in graph.edge_list:
        # if the edge matches the most occurred type
        if i.__get_attribute__(dir) == number and i.comment == type:
            prune_node = graph.get_node(i.__get_attribute__(drev[dir]))
            # continue only if the node has not
            # already had any of its edges pruned
            if prune_node.color is None:
                # add color as mark of pruning
                prune_node.color = hashcolor(maxedge)

                # stylistic stuff here
                if prune_node.fillcolor is None:
                    prune_node.style = 'bold'
                else:
                    prune_node.style = 'bold,filled'

                dellist.append(i)
                no_pruned += 1

    if len(dellist) > 0:
        # get the node that the edges were referencing or ref'ed by
        refnode = graph.get_node(dellist[0].__get_attribute__(dir))
        # get the node that was, respectively, ref'ed or ref'ing
        delnode = graph.get_node(dellist[0].__get_attribute__(drev[dir]))

    # delete the edges from graph. Done after all other stuff in the
    # routine so that the graph structure lists don't go fubar
    for i in dellist:
        del_graph_edge(i)
    return no_pruned, (refnode, delnode, maxedge, dir)

def add_legend_pruned(refnode, delnode, maxedge, dir):
    # add prune color info to cluster legend_pruned
    global graph, legend_pruned

    # Make legend nodes and edges for the case
    # referenced rfc nodes are cloned except for their names
    legend_pruned.add_node(pydot.Node(maxedge, color=hashcolor(maxedge),
                                      label="All nodes with this border",
                                      style='bold,filled',
                                      fillcolor="white"))

    state = refnode.__getstate__()
    state["name"] = "rfc" + state["name"]
    legend_pruned.add_node(pydot.Node(**state))

    # Grab the edge color from maxedges (edge type always last of list)
    edgecol = hashcolor(maxedge.split(",")[-1])

    if dir == 'dst':
        legend_pruned.add_edge(pydot.Edge(maxedge, "rfc"+refnode.name,
                                          color=edgecol))
    elif dir == 'src':
        legend_pruned.add_edge(pydot.Edge("rfc"+refnode.name, maxedge,
                                          color=edgecol))

# Try to search for the source for the most (or >n) edges in the
# graph, abstract the edges and make a note of it in the legend.
def prune_edges(lowlimit):
    global graph

    # placeholder for the construction of legend_pruned
    legend_arglist = []

    # get count of edges to/from nodes
    edges, counts = getedgecounts()

    # stop if there aren't any edges (max()&remove_edges() exceptions)
    if len(counts) == 0:
        return

    # take edge with maximum count value
    maxedge, maxcount = edges[counts.index(max(counts))], max(counts)

    # remove either only max edges or upto a limit
    if lowlimit == -1:
        num, legend_arglist = remove_edges(maxedge)
    else:
        while maxcount >= lowlimit:
            num, args = remove_edges(maxedge)
            # Stop if further edges cannot be removed
            if num == 0:
                break
            legend_arglist.append(args)
            edges, counts = getedgecounts()
            if len(counts) == 0:
                break
            maxedge, maxcount = edges[counts.index(max(counts))], max(counts)

    # Make a legend entry on the pruned edges, if any
    if len(legend_arglist) > 0:
        if type(legend_arglist) == tuple:
            add_legend_pruned(*legend_arglist)
        else:
            for args in legend_arglist:
                add_legend_pruned(*args)

def appendreftypes(data, rfc, reftypes):
    allrefs = []
    for type in reftypes:
        if rfc.has_key(type):
            # If we don't have a status limit, make things easy
            if limit == []:
                allrefs = allrefs + rfc[type]
            # else, make it pretty darn hard
            else:
                for dst in rfc[type]:
                    if data[dst].has_key('Status'):
                        if data[dst]['Status'] in limit:
                            continue
                    elif 'N' in limit:
                        continue
                    allrefs.append(dst)
    return allrefs
            
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
                newnodes.update(appendreftypes(data, data[node], types))
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
        for parent in appendreftypes(data, data[current], types):
            if parent in numbered and numbered[parent] == num:
                current = parent
                path.insert(0, current)
                break
    return path

def traverse_path(chain, shortest, cycles, data):
    global reftypes, inreftypes

    # add all paths here
    paths = []

    for pair in chain:
        if data.has_key(pair[1]):
            # if end node is unreachable -> next path
            if appendreftypes(data, data[pair[1]], inreftypes) == []:
                continue
            else:
                startnum = numberatize(data, pair[0], reftypes)
                endnum = numberatize(data, pair[1], inreftypes)            

                for middle in startnum:
                    if middle not in endnum:
                        continue
                    startpath = backtrackatize(data, startnum, middle, inreftypes)
                    endpath = backtrackatize(data, endnum, middle, reftypes)

                    # this prevents the short cycles:
                    # if cycles are possible and if one exists -> next path
                    if cycles == 0:
                        if len(startpath) > 1 and len(endpath) > 1:
                            if startpath[-2] == endpath[-2]:
                                continue

                    endpath.reverse()
                    paths.append(startpath+endpath[1:])

    if len(paths) == 0:
        return (None, None)

    if shortest:
        shortest_paths = {}
        for idx, path in zip(range(len(paths)), paths):
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
                
    nodes = sets.Set()
    pairs = sets.Set()
    for i in paths:
        # [1,2,3] -> [(1,2),(2,3)]
        pairs.update(zip(i, i[1:]))
        for j in i:
            nodes.add(j)

    return pairs, nodes

def graph_error(label):
    global graph

    graph.set_label(label)
    print graph.to_string()
    sys.exit(0)

def main():
    global graph, limit, unhandled
    global reftypes, inreftypes, typelabels, statuslabels

    # get in data in the parserfcs.py -format, grab the needed rfc data
#    rfcfile = file(basedir + 'rfc-data.pickle')
    rfcfile = file('rfc-data.pickle')
    data = cPickle.load(rfcfile)

    # here goes.. argument handling
    try:
        opts, rest = getopt.getopt(sys.argv[1:], 'hp:P:u:l:c:t:C:',
                                   ['help', 'proto=', 'prune=',
                                    'url=', 'limit=', 'cycles=',
                                    'path=', 'concentrate='])
    except getopt.error, what:
        sys.exit(str(what))


    protos = None

    # general parameters
    prunelimit = -2
    limit = []
    edgelimit = []

    # path parameters
    path = None
    cycles = 0

    try:
        for o, a in opts:
            if o in ('-p', '--proto'):
                protos = a.split(',');
                for number in protos:
                    int(number)
            elif o in ('-C', '--concentrate'):
                if a in ('true', 'True'):
                    graph.concentrate='True';
            elif o in ('-P', '--prune'):
                prunelimit = int(a)
            elif o in ('-l', '--limit'):
                templimit = a.split(',')

                # dependency limits are handled by just limiting
                # reftypes and inreftypes with which the dependencies
                # are gathered in methods
                for char in templimit:
                    if typelabels.has_key(char):
                        edgelimit = edgelimit + typelabels[char]
                    elif statuslabels.has_key(char):
                        limit.append(char)
                
                reftypes = filter(lambda f: f not in edgelimit, reftypes)
                inreftypes = filter(lambda f: f not in edgelimit, inreftypes)
            elif o in ('-t', '--path'):
                path = a.lower()
                if path not in ('all', 'short'):
                    raise Exception(a)
            elif o in ('-c', '--cycles'):
                if a in ('true', 'True'):
                    cycles = 1
    except ValueError, what:
        print "Expected numeric value to argument " + o
        sys.exit(2)
    except Exception, what:
        print 'Expected "all" or "short" to path, got "' + what[0] + '"'
        sys.exit(2)

    if protos is None:
        graph_error("Please supply RFC number")
    for proto in protos:
        if not data.has_key(proto):
            graph_error("RFC " + proto + " not issued")

    # TODO
    # - years to an option, default true

    # Algorithm wishes
    # - Search with some distance (to, from)
    # - Clusterise (Clique graph)
    # - Two graphs with the same point, diff the environment

    # methods:
    # - depth/breadth-first-search to find chains between two protocols
    # - search by name/protocol -fields, port number, etc?
    # - option to decide the data on which to order ranks

    # Pending
    # - clusters for pruning? Wait for dot revision.
    # - gets url/parts of url as an argument, to retain args (needed?)

    if path is None:
        # spread from protos
        for proto in protos:
            rfc = data[proto]
            unhandled = unhandled + spread_from_node(rfc, data)
        else:
            unhandled = set(unhandled)
    else:
        if len(protos) < 2:
            graph_error("Cannot form path: need at least two protocols")

        # if the a node in path in limit, give up
        for proto in protos:
            if data[proto].has_key('Status'):
                if data[proto]['Status'] in limit:
                    graph_error("No path found")
            elif 'N' in limit:
                graph_error("No path found")

        # [1,2,3] -> [(1,2),(2,3)]
        chain = zip(protos, protos[1:])

        # all or shortest paths
        if path == "all":
            pairs, nodes = traverse_path(chain, 0, cycles, data)
        else:
            pairs, nodes = traverse_path(chain, 1, cycles, data)

        if pairs is None:
            graph_error("No path found")

        for node in nodes:
            add_rfcnode(data[node])

        keywords = ['Obsolete', 'Update', 'seealso', 'Reference']
        strings = ['Obsoletes', 'Updates', 'References', 'References']

        for edge in pairs:
            src, dst = edge
            # Check all the reasons for link
            for kw, str in zip(keywords, strings):
                # If the source has the link category and dst in it
                if data[src].has_key(kw):
                    if dst in data[src][kw]:
                        # -> everything all right, add edge
                        graph.add_edge(pydot.Edge(src, dst,
                                                  color=hashcolor(str),
                                                  comment=str))
                        # next pair, please
                        break

    # To make the graph explode
    # might make a "spread in all dirs" -function later
    # for i in unhandled:
    #     spread_from_node(data[i], data)

    # used to add the year nodes and graph ranking
    add_years_to_graph()

    # Testing edge pruning
    # prune all similar edges with > 10 occurrences, if possible
    # i.e. if more than 10 edges originate from a node
    #   or if more than 10 edges are destined for a node
    # prune_edges(10)
    # Use the following to prune the case with the most edges to/from node
    # prune_edges(-1)

    if prunelimit > -2:
        prune_edges(prunelimit)

    # For pretty printing the rfc status nodes in legend, make
    # invisible edges between them
    tie_statusnodes()

    # Now, layout graph again to a new graph to achieve better ranking
    global per_year

    # first, sort the years the rfc:s (nodes) are from
    years = per_year.keys()
    years.sort()

    # go through edges, except the year-edges
    for e in graph.edge_list:
        if e.src[0] == 'Y':
            continue
        # find out how many ranks the endpoints of the edges are apart
        minlen = years.index("Year"+data[e.src]['Year']) - \
                 years.index("Year"+data[e.dst]['Year'])
        # insert that as edge minimum length
        e.minlen = minlen

    # make the new graph, add legends
    ordered = pydot.Dot(clusterrank='local', rankdir='LR', compound='true')
    ordered.add_subgraph(legend)
    ordered.add_subgraph(legend_pruned)
    
    # import pdb
    # pdb.set_trace()

    # insert nodes in year ordering, oldest first
    for year in years:
        for rfc in per_year[year]:
            ordered.add_node(graph.get_node(rfc))

    # insert subgraphs, with the exception of clusters
    for sg in graph.subgraph_list:
        if sg.graph_name[:14] != "cluster_legend":
            ordered.add_subgraph(sg)

    # add edges
    for e in graph.edge_list:
        ordered.add_edge(e)

    # print out dot
    print ordered.to_string()

    return 0

if __name__ == "__main__":
    main()
