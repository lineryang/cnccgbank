from munge.trees.traverse import text_without_traces, text_without_quotes_or_traces
import re

class Node(object):
    '''Representation of a PTB internal node.'''
    def __init__(self, tag, kids, parent=None):
        self.tag = tag
        self.kids = kids
        
        self.parent = parent
        
    @property
    def cat(self):
        return self.tag

    def __repr__(self, first=True, suppress_lex=False):
        return "%s(%s %s)%s" % ("(" if first else "", 
                                self.tag, 
                                ' '.join(kid.__repr__(False, suppress_lex) for kid in self.kids), 
                                ")" if first else "")

    def __iter__(self):
        for kid in self.kids: yield kid

    def count(self):
        return len(self.kids)

    def is_leaf(self): return False
    def label_text(self): return re.escape(self.tag)
    
    def text(self, with_quotes=True):
        return (text_without_traces if with_quotes else text_without_quotes_or_traces)(self)

    def __getitem__(self, index):
        # TODO: This is slightly broken. Since we can't define len() for nodes, we can't use negative (or omitted) slice indices properly.
        try:
            if not (-len(self.kids) <= index < len(self.kids)): 
                raise RuntimeError("Invalid index %d into Node %s." % (index, self))
            return self.kids[index]
        except TypeError:
            return self.kids[index.start:index.stop]
            
    def __setitem__(self, index, value):
        try:
            if not (-len(self.kids) <= index < len(self.kids)): 
                raise RuntimeError("Invalid index %d into Node %s." % (index, self))
            self.kids[index] = value
            value.parent = self
        except TypeError:
            self.kids[index.start:index.stop] = value
            for node in value:
                value.parent = self

    def __eq__(self, other):
        return (not other.is_leaf()) and self.tag == other.tag and self.kids == other.kids
    def __ne__(self, other): return not (self == other)
    
class Leaf(object):
    '''Representation of a PTB leaf.'''
    def __init__(self, tag, lex, parent):
        self.tag = tag
        self.lex = lex
        
        self.parent = parent
        
    @property
    def cat(self):
        return self.tag

    def __repr__(self, first=True, suppress_lex=False):
        return ("%s(%s%s)%s" %
            ("(" if first else '',
            self.tag, '' if suppress_lex else (' ' + self.lex),
            ")" if first else ''))
            
    def __iter__(self): raise StopIteration

    def count(self): return 0

    def is_leaf(self): return True
    def label_text(self): return "%s '%s'" % (re.escape(self.tag), self.lex)
    
    def text(self, with_quotes=True):
        return (text_without_traces if with_quotes else text_without_traces_or_quotes)(self)

    def not_implemented(self, *args):
        raise NotImplementedError('Leaf has no children.')
    __getitem__ = __setitem__ = not_implemented
        
    def __eq__(self, other):
        return other.is_leaf() and self.tag == other.tag and self.lex == other.lex
    def __ne__(self, other): return not (self == other)