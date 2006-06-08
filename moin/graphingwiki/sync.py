# -*- coding: iso-8859-1 -*-
"""
    sync class
     - handles graph internals

    @copyright: 2006 by Joachim Viide and
                        Juhani Eronen <exec@iki.fi>
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

class SyncRow:
    def __init__(self, identity,
                 constants, guarantees,
                 sethandler, unsethandler):
        self.constants = None
        self.guarantees = frozenset(guarantees)
        self.defaults = guarantees
        self.__sethandler = sethandler
        self.__unsethandler = unsethandler        
        self.__id = identity
        self.__dict__.update(constants)
        
        self.constants = frozenset(self.__dict__)
        self.__dict__.update(self.defaults)
        
    def __setattr__(self, name, value):
        constants = self.__dict__.get("constants", None)        
        if constants and name in self.constants:
            raise AttributeError, "Can't change a constant attribute"
        if name in self.__dict__ and self.__dict__[name] == value:
            return
        
        oldvalue = self.__dict__.get(name, None)
        self.__dict__[name] = value        
        if constants and self.__sethandler:
            self.__sethandler(self, self.__id, name, value, oldvalue)

    def __delattr__(self, name):
        if name in self.constants:
            raise AttributeError, "Can't delete a constant attribute"

        if name in self.guarantees:
            raise AttributeError, "Can't delete a guaranteed attributes"

        if name not in self.__dict__:
            raise AttributeError, "Can't delete a undefined attribute "+repr(name)

        oldvalue = self.__dict__[name]
        del self.__dict__[name]
        if self.__unsethandler:
            self.__unsethandler(self, self.__id, name, oldvalue)

    def __iter__(self):
        variables = set(self.__dict__)
        variables.difference_update(self.constants)
        
        for key in variables:
            yield key, self.__dict__[key]

    def update(self, other):
        # FIXME: Check whether rows are compatible
        for name, value in other:
            setattr(self, name, value)

class Dispatcher:
    def __init__(self):
        self.chain = []

    def __iadd__(self, other):
        self.chain.append(other)
        return self

    def __isub__(self, other):
        self.chain.remove(other)
        return self

    def __call__(self, *args, **keys):
        for chained in self.chain:
            chained(*args, **keys)

class SyncTable:
    def __init__(self, constants, guarantees):
        self.constants = constants
        self.guarantees = frozenset([i[0] for i in guarantees])
        self.defaults = dict(guarantees)
        
        self.dicts = dict()
        self.attributes = dict()

        self.addhandler = Dispatcher()
        self.sethandler = Dispatcher()
        self.unsethandler = Dispatcher()
        self.delhandler = Dispatcher()

        self.sets = dict()

        for key in constants:
            self.dicts[key] = dict()
        for key in self.guarantees:
            self.dicts[key] = dict()            

    def __pack(self, values, keys):
        values = list(values)

	expected = len(self.constants)
	given = len(values)+len(keys)
	if given > expected:	    
	    raise TypeError, "Exactly "+repr(expected)+" arguments expected ("+repr(given)+" given)"

        head, tail = set(self.constants[:len(values)]), self.constants[len(values):]
        head.intersection_update(keys)
        if head:
            raise TypeError, "Multiple values for keyword argument "+repr(head.pop())
            
        for key in tail:
            if key not in keys:
                raise TypeError, "Keyword argument "+repr(key)+" missing"
            values = values.append(keys[key])
            del keys[key]

        if keys:
	    raise TypeError, "An unexpected keyword argument "+repr(keys.keys()[0])

        return tuple(values)

    def __check(self, keys):
        keyset = set(keys)
        keyset.difference_update(self.guarantees)
        keyset.difference_update(self.constants)
        if keyset:
	    raise TypeError, "An unexpected keyword argument "+repr(keyset.pop())            

    def __set(self, row, ident, key, value, oldvalue):
        if ident not in self.attributes:
            return
        
        if key in self.guarantees:
            self.dicts[key][oldvalue].discard(ident)
            if not self.dicts[key][oldvalue]:
                del self.dicts[key][oldvalue]
            if value not in self.dicts[key]:
                self.dicts[key][value] = set()
            self.dicts[key][value].add(ident)      
        
        if self.sethandler:
            self.sethandler(self, row, *(ident+(key, value, oldvalue)))

    def __unset(self, row, ident, key, oldvalue):
        if ident not in self.attributes:
            return
        
        if self.unsethandler:
            self.unsethandler(self, row, *(ident+(key, oldvalue)))

    def add(self, *values, **keys):
        result = self.__pack(values, keys)
        if result in self.attributes:
            return self.attributes[result]

	constants = dict(zip(self.constants, result))
        
        for key, value in constants.iteritems():
            if value not in self.dicts[key]:            
                self.dicts[key][value] = set()
            self.dicts[key][value].add(result)

        for key, value in self.defaults.iteritems():
            if value not in self.dicts[key]:            
                self.dicts[key][value] = set()
            self.dicts[key][value].add(result)

        row = SyncRow(result, constants, self.defaults,
                      self.__set, self.__unset)

        self.attributes[result] = row

        if self.addhandler:
            self.addhandler(self, row, *result)

        for key in self.guarantees:
            value = getattr(row, key)
            self.__set(row, result, key, value, value)
            
        return row

    def delete(self, *values, **keys):
        result = self.__pack(values, keys)

        if result not in self.attributes:
            return

        deleted = self.attributes[result]

        for key in self.constants:
	    value = getattr(deleted, key)
            self.dicts[key][value].discard(result)
            if not self.dicts[key][value]:
                del self.dicts[key][value]

        for key in self.guarantees:
	    value = getattr(deleted, key)
            self.dicts[key][value].discard(result)
            if not self.dicts[key][value]:
                del self.dicts[key][value]	
                
        del self.attributes[result]
        
        if self.delhandler:
            self.delhandler(self, deleted, *result)

    def deleteall(self, **keys):
 
        results = self.getall(**keys)        
        for result in results:
            self.delete(*result)

    def has(self, *values, **keys):
        result = self.__pack(values, keys)
        return result in self.attributes

    def hasany(self, **keys):
	return len(self.getall(**keys)) > 0

    def __len__(self):
        return len(self.attributes)

    def count(self, **keys):
	return len(self.getall(**keys))

    def get(self, *values, **keys):
        result = self.__pack(values, keys)
        
        if result not in self.attributes:
            return None
        return self.attributes[result]

    def getall(self, **keys):
	self.__check(keys)
        
	total = set(self.attributes)
        
        for key, value in keys.iteritems():
            if value == "*":
                newvalues = set()
                for realvalue in self.dicts[key]:
                    if realvalue != "":
                        return self.dicts[key][realvalue]
                    if realvalue == "":
                        continue

                    #Warning, bug potential, I seem to lack part of the
                    #understanding how self.dicts work
                    return self.dicts[key][realvalue]

            elif value not in self.dicts[key]:
                    return set()
            else:
                total.intersection_update(self.dicts[key][value])
        return total

    def update(self, other):
        # FIXME: Check whether the tables are compatible
        for item in other.getall():
            otherattrs = other.get(*item)
            if self.has(*item):
                attributes = self.get(*item)
            else:
                attributes = self.add(*item)
            attributes.update(otherattrs)

class SyncDummy:
    pass

class Sync:
    def __init__(self, tables):
	self.__tables = tables
	self.__sync = dict()
        self.tablenames = set()

        self.commithandler = Dispatcher()

        tables += (("listeners", ("listener",), (("group", None),)),)
        tables += (("listened",
                    ("listened",),
                    ()),)
                    
        for name, constants, guarantees in tables:
            addh, delh, seth, unseth = self.__createhandlers(name)
            table = SyncTable(constants, guarantees)
            table.addhandler += addh
            table.delhandler += delh
            table.sethandler += seth
            table.unsethandler += unseth
            setattr(self, name, table)
            self.tablenames.add(name)

	self.__totals = self.__createdummy()
	self.__dummy = self.__createdummy()
        self.listeners.addhandler += self.__addlistener
        self.listeners.sethandler += self.__setlistener
        self.listeners.unsethandler += self.__unsetlistener
        self.listeners.delhandler += self.__dellistener        

    def __createdummy(self):
        dummy = SyncDummy()
        for name in self.tablenames:
	    subdummy = SyncDummy()
	    
	    subdummy.added = set()
	    subdummy.deleted = set()
	    subdummy.set = dict()
	    subdummy.unset = dict()

	    setattr(dummy, name, subdummy)
	return dummy

    def __createhandlers(self, name):
        def _add(table, row, *ident):
            dummy = getattr(self.__dummy, name)
            total = getattr(self.__totals, name)
            
	    if ident not in total.added:
		dummy.added.add(ident)
	    if ident in total.set:
		dummy.unset[ident] = set(total.set[ident])
	    dummy.deleted.discard(ident)
            
        def _del(table, row, *ident):
            dummy = getattr(self.__dummy, name)
            total = getattr(self.__totals, name)
            
	    dummy.added.discard(ident)
	    if ident in total.added:
		dummy.deleted.add(ident)
	    if ident in dummy.set:
		del dummy.set[ident]
	    if ident in dummy.unset:
		del dummy.unset[ident]

        def _set(table, row, *rest):
            dummy = getattr(self.__dummy, name)
            total = getattr(self.__totals, name)
            
	    ident, key, value = rest[:-3], rest[-3], rest[-2]

            if ident in dummy.set and key in dummy.set[ident]:
                del dummy.set[ident][key]
                if not dummy.set[ident]:
                    del dummy.set[ident]

            if ident not in total.set or key not in total.set[ident] or \
                   total.set[ident][key] != value:
                if ident not in dummy.set:
                    dummy.set[ident] = dict()
                dummy.set[ident][key] = value

	    if ident in dummy.unset:
		dummy.unset[ident].discard(key)
                if not dummy.unset[ident]:
                    del dummy.unset[ident]

        def _unset(table, row, *rest):
            dummy = getattr(self.__dummy, name)
            total = getattr(self.__totals, name)
            
	    ident, key = rest[:-2], rest[-2]
	    
	    if ident in dummy.set and key in dummy.set[ident]:
		del dummy.set[ident][key]
		if not dummy.set[ident]:
		    del dummy.set[ident]
	    elif ident in total.set and key in total.set[ident]:
		if ident not in dummy.unset:
		    dummy.unset[ident] = set()
		dummy.unset[ident].add(key)

        return _add, _del, _set, _unset

    def __addlistener(self, table, attrs, listener):
	listener(self, self.__totals)
        attrs.group = listener

    def __setlistener(self, table, attrs, listener, key, value, oldvalue):
        if key == "group":
            if isinstance(value, Sync):
                value.listened.add(self)
            if (isinstance(oldvalue, Sync) and
                not self.listeners.hasany(group = oldvalue)):
                oldvalue.listened.delete(self)                

    def __unsetlistener(self, table, attrs, listener, key, oldvalue):
        if key == "group":
            if (isinstance(oldvalue, Sync) and
                not self.listeners.hasany(group = oldvalue)):
                oldvalue.listened.delete(self)                        

    def __dellistener(self, table, attrs, listener):
        group = attrs.group
        if (isinstance(group, Sync) and
            not self.listeners.hasany(group = group)):
            group.listened.delete(self)

    def commit(self):
        dummies = self.__dummy
        self.__dummy = self.__createdummy()

	for name in self.tablenames:
	    dummy = getattr(dummies, name)
	    total = getattr(self.__totals, name)
	    
	    total.added.update(dummy.added)

            for ident in dummy.deleted:
                if ident in total.set:
                    del total.set[ident]
                total.added.remove(ident)

	    for ident, names in dummy.set.iteritems():
		if ident not in total.set:
		    total.set[ident] = dict()
		total.set[ident].update(names)

	    for ident, names in dummy.unset.iteritems():
		if ident not in total.set:
		    continue
		for name in names:
		    if name in total.set[ident]:
			del total.set[ident][name]
        
	for listener, in self.listeners.getall():
	    listener(self, dummies)

        self.commithandler(self)

    def clear(self):
        for name in self.tablenames:
            if name == "listeners":
                continue
            if name == "listened":
                continue            
            table = getattr(self, name)
            table.deleteall()

    def destroy(self):
        listeners = [self.listeners.get(listener).group
                     for listener, in self.listeners.getall()]

        for name in self.tablenames:
            table = getattr(self, name)
            table.deleteall()

if __name__ == '__main__':
    def addhand(table, row, parent, child):
	print "! Added edge", parent, "->", child, "label:", row.label

    def delhand(table, row, parent, child):
	print "! Deleted edge", parent, "->", child, "label:", row.label

    def sethand(table, row, parent, child, name, value):
	print "! Set edge's", parent, "->", child, "attribute", name, "to", value

    def unsethand(table, row, parent, child, name):
	print "! Unset edge's", parent, "->", child, "attribute", name

    edges = SyncTable(("parent", "child"),                  # First, the identifying attributes.
		      (("label", ""), ("somenumber", 0)),   # Then the guaranteed attributes and their defaults.
		      addhand, delhand, sethand, unsethand) # AND then the handlers


    print


    # This adds two edges. One with parent "node1" and child "node3",
    # one with parent "node1" and child "node2"
    edges.add("node1", "node3")
    row1 = edges.add("node1", "node2")
    print row1.parent, row1.child, row1.label, row1.somenumber


    print

    
    row1.label = "The king of edges" # Sets the guaranteed attribute "label"
    row1.mylist = [1, 2, 3] # Creates and sets a new attribute "mylist"
    # This gives out an exception:
    # row1.parent = "node3"
    print row1.label, row1.mylist


    print


    del row1.mylist # Unsets the attribute "mylist"
    # These give out excptions:
    # del row1.label
    # del row1.parent


    print


    row2 = edges.get("node1", "node3")
    row2.label = "The other edge"
    print row2.parent, row2.child, row2.label, row2.somenumber

    
    print


    # Gets all the edges whose parent is "node1"
    print edges.getall(parent = "node1")
    # Gets all the edges whose child is "node2"
    print edges.getall(child = "node2")
    # You get the drill
    print edges.getall(parent = "node1", label = "The other edge")

    # Gets all the edges
    results = edges.getall()
    for parent, child in results:
	row = edges.get(parent, child)
	print row.parent, row.child, row.label    

    
    print


    edges.delete("node1", "node3")
    # The row "node1", "node3" has magically disappeared from the table! OMG!
    print edges.getall()


    print
    

    # Deletes every edge whose parent is "node1"
    edges.deleteall(parent = "node1")
    # And this will delete, like, everything:
    edges.deleteall()


    print


    
    # Defines a Sync with two Sync Tables: edges and nodes.
    # Edges are defined by the identifying attributes "parent" and "child",
    # and they also have a guaranteed attribute "label" (with default "").
    # Nodes are defined by the identifying attribute "node"
    # and they also have a guaranteed attribute "label" (with default "").
    graph = Sync(( ("edges",
		     (addhand, delhand, sethand, unsethand),
		   ("parent", "child"),
		   (("label", ""),)),
		  ("nodes",
		   (None, None, None, None),
		   ("node",),
		   (("label", ""),("blah","")))))


    graph.nodes.add("node1")
    graph.nodes.add("node2")
    row = graph.edges.add("node1", "node2")
    row.label = "An edge from node1 to node2"
    # ...aaand so on...


    print


    graph.commit()


    print



    def graphlistener(sync, diff):
      for node, in diff.nodes.added:
	print "- Node", node, "added"

      for parent, child in diff.edges.added:
	print "- Edge", parent, "->", child, "added"

      for node, in diff.nodes.deleted:
	print "- Node", node, "deleted"

      for parent, child in diff.edges.deleted:
	print "- Edge", parent, "->", child, "deleted"

      for node, in diff.nodes.set:
	names = diff.nodes.set[(node,)]
	for name in names:
	  print "- Node attribute", name, "set to", names[name]

      for parent, child in diff.edges.set:
	names = diff.edges.set[(parent, child)]
	for name in names:
	  print "- Edge attribute", name, "set to", names[name]

      for node, in diff.nodes.unset:
	names = diff.nodes.unset[(node,)]
	for name in names:
	  print "- Node attribute", name, "unset"

      for parent, child in diff.nodes.unset:
	names = diff.edges.unset[(parent, child)]
	for name in names:
	  print "- Edge attribute", name, "unset"

    graph.listeners.add(graphlistener)


    print


    graph.nodes.add("node3")
    row = graph.edges.add("node1", "node3")
    row.label = "The greatest edge of them all"
    row.mystuff = "Schwaa?"
    graph.commit()

    print

    del row.mystuff
    graph.commit()


    print


    
    graph.nodes.add("node4")
    graph.nodes.delete("node4")
    graph.commit()


    print


    graph.nodes.add(1)
    graph.nodes.add(2).label = "jee"
    
    graph.nodes.delete(2)
    print graph.nodes.getall(label = "jee")

    graph.nodes.add(2).blah = "justinterestedabouttheattribute"
    graph.nodes.add(3).blah = "justinterestedabouttheattribute"

    
    print "searching all"
    print "RES",graph.nodes.getall(blah="justinterestedabouttheattribute")
    print 
    print "searching just the attribute"
    all_with_attribute_blah = graph.nodes.getall(blah = "*")
    print "RES:", all_with_attribute_blah


    graph.commit()

    
    print "-----------------------------"
    graph.nodes.add("attributenode")
    print "commit1:"
    graph.commit()

    print "setting srca:"
    attribs = graph.nodes.get("attributenode")
    attribs.srca = "huoh"

    print "commit2"
    graph.commit()

    print "changng srca"
    attribs.srca = "blaah"

    print "commit3:"
    graph.commit()
    print "changed"
    print "total:", graph.nodes.get("attributenode").srca
    print "-----------------------------"
