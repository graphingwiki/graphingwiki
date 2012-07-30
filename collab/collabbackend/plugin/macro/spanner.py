import bisect

class Spanner(object):
    def __init__(self, iterable=list()):
        object.__init__(self)
        self.spans = list(iterable)

    def __eq__(self, other):
        if isinstance(other, Spanner):
            return self.spans == other.spans
        raise NotImplemented

    def __ne__(self, other):
        return not (self == other)

    def addSpan(self, start, end):
        #if start == end:
        #    return

        index = bisect.bisect_left(self.spans, (start, None))
        index = max(index-1, 0)

        while index < len(self.spans):
            oldstart, oldend = self.spans[index]
            
            if start > oldend:
                index += 1
                continue
            if oldstart <= start <= oldend and oldstart <= end <= oldend:
                return
            if end < oldstart:
                break
            start = min(start, oldstart)
            end = max(end, oldend)

            del self.spans[index]

        self.spans.insert(index, (start, end))

    def delSpan(self, start, end):
        index = bisect.bisect_left(self.spans, (start, None))
        index = max(index-1, 0)        

        while index < len(self.spans):
            oldstart, oldend = self.spans[index]
            
            if start >= oldend:
                index += 1
                continue
            if end <= oldstart:
                break

            del self.spans[index]
            if oldstart < start:
                self.spans.insert(index, (oldstart, min(start, oldend)))
                index += 1
            if oldend > end:
                self.spans.insert(index, (max(oldstart, end), oldend))
                index += 1

    def inSpan(self, point):
        index = bisect.bisect_left(self.spans, (point, None))
        index = max(index-1, 0)

        while index < len(self.spans):
            start, end = self.spans[index]
            if start > point:
                break        
            if start <= point < end:
                return start, end

            index += 1
        return None

    def splice(self, start, end):
        splices = []

        index = bisect.bisect_left(self.spans, (start, None))
        index = max(index-1, 0)

        while index < len(self.spans):
            oldstart, oldend = self.spans[index]
            index += 1

            if oldstart <= start <= oldend and oldstart <= end <= oldend:
                return splices
            if end <= oldstart:
                break
            if start < oldstart:
                splices.append((start, oldstart))                
            start = max(start, oldend)

        if start < end:
            splices.append((start, end))

        return splices

    def cut(self, start, end):
        spans = []

        index = bisect.bisect_left(self.spans, (start, None))
        index = max(index-1, 0)

        while index < len(self.spans):
            oldstart, oldend = self.spans[index]
            index += 1

            if oldend <= start:
                continue
            if end <= oldstart:
                break
            spans.append((max(start, oldstart), min(end, oldend)))

        return spans

    def __iter__(self):
        for span in self.spans:
            yield span

    def clear(self):
        self.spans = []
