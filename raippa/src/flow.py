import random

from graphingwiki.editing import get_metas

class Flow:

    def __init__(self, request, pagename):
        self.request = request
        self.pagename = pagename

    def fullflow(self):
        return self.flow_from_point('first')

    def flow_from_point(self, point):
        flow = dict()

        def get_next(currentpoint):
            nextlist = self.nextlist(currentpoint)

            if len(nextlist) == 0:
                return list()

            reasons = self.parse_nextlist(nextlist)
            
            nexts = list()
            for reasons, values in reasons.iteritems():
                for next in values:
                    nexts.append(next)
                    flow[next] = get_next(next)

            return nexts

        flow[point] = get_next(point)
        
        return flow

    def next_from_point(self, point, handler=None):
        nextlist = self.nextlist(point)

        if len(nextlist) == 0:
            return list()

        reasons = self.parse_nextlist(nextlist)

        if not handler or point == 'first':
            nexts = list()
            for reasons, values in reasons.iteritems():
                nexts.extend(values)

            return nexts 

        return self.handle_types(handler(point), reasons)

    def nextlist(self, point):
        metas = get_metas(self.request, self.pagename, [point], checkAccess=False)
        return metas.get(point, list())

    def handle_types(self, success, reasons):
        if success:
            if 'success' in reasons.keys() and len(reasons['success']) > 0:
                #TODO: if len(reasons['success']) > 1:
                return [reasons['success'][0]]
            elif 'random' in reasons.keys() and len(reasons['random']) > 0:
                return random.sample(reasons['random'], 1)
            elif 'select' in reasons.keys():
                return reasons['select']
            else:
                return list()
        else:
            if 'failure' in reasons.keys() and len(reasons['failure']) > 0:
                #TODO: if len(reasons['failure']) > 1:
                return [reasons['failure'][0]]
            else:
                return list()

    def parse_nextlist(self, nextlist):
        reasons = dict()

        for nextpoint in nextlist:
            reason = None

            parts = nextpoint.split()
            if len(parts) > 1 and not parts[0].startswith("[["):
                reason = parts[0]
                nextpoint = " ".join(parts[1:])

            if nextpoint.startswith("[[") and nextpoint.endswith("]]"):
                nextpoint = nextpoint[2:-2]

            if reason not in reasons.keys():
                reasons[reason] = list()
            reasons[reason].append(nextpoint)

        return reasons

    def get_metas(self, pagename, keys):
        from MoinMoin.Page import Page
        raw = Page(self.request, pagename).get_raw_body()
        metas = dict()

        for key in keys:
            metas[key] = list()
            text = ' %s::' % key
            for line in raw.split("\n"):
                if line.startswith(text):
                    metas[key].append(line[len(text)+1:])

        return metas
