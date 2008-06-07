from munge.trees.traverse import text_without_traces
import re

class Node(object):
    '''Representation of a PTB internal node.'''
    def __init__(self, tag, kids):
        self.tag = tag
        self.kids = kids
        
    @property
    def cat(self):
        return self.tag

    def __repr__(self, first=True):
        return "%s(%s %s)%s" % ("(" if first else "", 
                                self.tag, 
                                ' '.join(kid.__repr__(False) for kid in self.kids), 
                                ")" if first else "")

    def __iter__(self):
        for kid in self.kids: yield kid

    def count(self):
        return len(self.kids)

    def is_leaf(self): return False
    def label_text(self): return re.escape(self.tag)
    
    def text(self, with_quotes=True):
        return (text_without_traces if with_quotes else text_without_traces_or_quotes)(self)

    def __getitem__(self, index):
        return self.kids[index]

class Leaf(object):
    '''Representation of a PTB leaf.'''
    def __init__(self, tag, lex):
        self.tag = tag
        self.lex = lex
        
    @property
    def cat(self):
        return self.tag

    def __repr__(self, first=True):
        return "(%s %s)" % (self.tag, self.lex)

    def __iter__(self): raise StopIteration

    def count(self): return 0

    def is_leaf(self): return True
    def label_text(self): return "%s '%s'" % (self.tag, self.lex)
    
    def text(self, with_quotes=True):
        return (text_without_traces if with_quotes else text_without_traces_or_quotes)(self)

    def __getitem__(self, index):
        raise NotImplementedError('Leaf has no children.')
