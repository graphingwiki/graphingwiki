import UserDict

def iterate(func, values):
    for value in values:
        try:
            value = func(value)
        except:
            continue
        yield value

class Coder(object):
    def encode(self, value):
        return value

    def decode(self, value):
        return value

class Func(Coder):
    def __init__(self, encoder=unicode, decoder=unicode):
        Coder.__init__(self)
        
        self.encoder = encoder
        self.decoder = decoder

    def encode(self, value):
        return self.encoder(value)

    def decode(self, value):
        return self.decoder(value)

Integer = Func(int)
Float = Func(float)

class MetaKey(object):
    def __init__(self, coder=None):
        object.__init__(self)

        self.set = set()
        self._setCoder(coder)

    def _setCoder(self, coder):
        if coder is None:
            coder = Coder()
        self.coder = coder

    def add(self, item):
        # A trick for validating that the inserted item can both be
        # decoded and encoded back.
        item = self.coder.decode(item)        
        item = self.coder.encode(item)

        self.set.add(item)

    def update(self, items):
        for item in items:
            self.add(item)

    def clear(self):
        self.set.clear()

    def single(self, *args):
        for item in self:
            return item

        if not args:
            raise ValueError, "no values for the meta key"
        return args[0]

    def __iter__(self):
        return iterate(self.coder.encode, self.set)

    def __len__(self):
        return len(list(iter(self)))

    def __nonzero__(self):
        return len(self) > 0

    def __repr__(self):
        return repr(list(self))

class Meta(UserDict.DictMixin):
    def __init__(self):
        self.dict = dict()
        self.schema = dict()

    def __getitem__(self, key):
        if key not in self.dict:
            self.dict[key] = MetaKey(self.schema.get(key, None))
        return self.dict[key]

    def __delitem__(self, key):
        self.dict.pop(key, None)
        
    def keys(self):
        return [key for key, value in self.dict.iteritems() if value]

    def setSchema(self, *args, **keys):
        coders = dict(args)
        for key, meta in self.dict.iteritems():
            meta._setCoder(coders.get(key, None))

        self.schema = coders

    def __contains__(self, key):
        value = self.dict.get(key, None)
        if value:
            return True
        return False
