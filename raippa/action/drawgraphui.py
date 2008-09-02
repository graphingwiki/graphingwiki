from tempfile import mkstemp
from raippa import FlowPage
from raippa import RaippaUser
import os 
import gv

def draw(request, page, raippauser):
    G = gv.digraph(page.pagename)
    gv.setv(G, 'rankdir', 'LR')
    gv.setv(G, 'bgcolor', 'transparent')
    nodes = dict()
    flow = page.getflow()
    for node, nextlist in flow.iteritems():
        if node not in nodes.keys():
            nodes[node] = gv.node(G, node)
        for nextnode in nextlist:
            if nextnode not in nodes.keys():
                nodes[nextnode] = gv.node(G, nextnode)
            gv.edge(nodes[node], nodes[nextnode])
    for node, nodeobject in nodes.iteritems():
        if node != "end" and node != "start":
            status = raippauser.statusdict.get(node, [])
            may = raippauser.canDo(node, raippauser.currentcourse)
            if may:
                gv.setv(nodeobject, 'fillcolor', "blue")
                url = "../%s?action=flowRider&userselection=%s&start" % (page.pagename, node)
                gv.setv(nodeobject, 'URL', url)
                gv.setv(nodeobject, 'label', "do now")
            elif "[[end]]" in status or "end" in status:
                gv.setv(nodeobject, 'label', "done")
                gv.setv(nodeobject, 'fillcolor', "green")
                #url = "../%s?action=flowRider&userselection=%s&start" % (page.pagename, node)
                #gv.setv(nodeobject, 'URL', url)
            else:
                gv.setv(nodeobject, 'label', "")
                #url = "../%s?action=flowRider&userselection=%s&start" % (page.pagename, node)
                #gv.setv(nodeobject, 'URL', url)
            gv.setv(nodeobject, 'style', "filled")
        else:
            gv.setv(nodeobject, 'shape', "doublecircle")
            gv.setv(nodeobject, 'label', "")
    gv.layout(G, 'dot')

    tmp_fileno, tmp_name = mkstemp()
    gv.render(G, 'png', tmp_name)
    f = file(tmp_name)
    data = f.read()
    os.close(tmp_fileno)
    os.remove(tmp_name)

    request.write(data)

def execute(pagename, request):
    request.raippauser = RaippaUser(request)
    coursepage = FlowPage(request, pagename)
    draw(request, coursepage, request.raippauser)
