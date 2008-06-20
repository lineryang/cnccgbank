import re
import copy
from munge.trees.traverse import text

class Node(object):
    '''Representation of a CCGbank internal node.'''
    
    # We allow lch to be None to make easier the incremental construction of Node structures in
    # the parser. Conventionally, lch can never be None.
    def __init__(self, cat, ind1, ind2, parent, lch=None, rch=None):
        '''Creates a new internal node.'''
        self.cat = cat
        self.ind1, self.ind2 = ind1, ind2
        self.parent = parent

        self._lch, self._rch = lch, rch
        
        if self._lch:
            self._lch.parent = self
        if self._rch:
            self._rch.parent = self

    def __repr__(self):
        '''Returns a (non-evaluable) string representation, a CCGbank bracketing.'''
        return ("(<T %s %s %s> %s %s)" %
                (self.cat, self.ind1, self.ind2,
                 self.lch, str(self.rch)+' ' if self.rch else ''))

    def __iter__(self):
        '''Iterates over each child of this node.'''
        yield self.lch
        if self.rch: yield self.rch

    def get_lch(self): return self._lch
    def set_lch(self, new_lch):
        if not new_lch: return
        self._lch = new_lch
        self._lch.parent = self
    lch = property(get_lch, set_lch)

    def get_rch(self): return self._rch
    def set_rch(self, new_rch):
        if not new_rch: return
        self._rch = new_rch
        self._rch.parent = self
    rch = property(get_rch, set_rch)

    def __eq__(self, other):
        #if not isinstance(other, Node): return False
        if other is None or other.is_leaf(): return False
        
        return (self.cat == other.cat and
                self.lch == other.lch and
                self.rch == other.rch and
                self.ind1 == other.ind1 and
                self.ind2 == other.ind2)
                
    def __ne__(self, other): return not (self == other)

    def is_leaf(self): return False
    def label_text(self): return re.escape(str(self.cat))
    
    def leaf_count(self):
        count = 1 + self._lch.leaf_count()
        if self._rch: count += self._rch.leaf_count()
        
        return count
        
    def clone(self): return copy.copy(self)
    
    def text(self):
        '''Returns a list of text tokens corresponding to the leaves under this node.'''
        return text(self)

    def __getitem__(self, index):
        if index != 0 or index != 1:
            raise RuntimeError('Invalid index %d into Node.' % index)

        return self.lch if index == 0 else self.rch

    def count(self):
        if self.rch is None: return 1
        else: return 2

class Leaf(object):
    '''Representation of a CCGbank leaf.'''
    
    def __init__(self, cat, pos1, pos2, lex, catfix, parent=None):
        '''Creates a new leaf node.'''
        self.cat = cat
        self.pos1, self.pos2 = pos1, pos2
        self.lex = lex
        self.catfix = catfix
        self.parent = parent

    def __repr__(self):
        '''Returns a (non-evaluable) string representation, a CCGbank bracketing.'''
        return "(<L %s %s %s %s %s>)" % \
                (self.cat, self.pos1, self.pos2, \
                 self.lex, self.catfix)
                 
    def __iter__(self): raise StopIteration

    def __eq__(self, other):
        if other is None or not other.is_leaf(): return False
        
        return (self.cat == other.cat and
                self.pos1 == other.pos1 and
                self.pos2 == other.pos2 and
                self.lex == other.lex and
                self.catfix == other.catfix)
                
    def __ne__(self, other): return not (self == other)
               
    def is_leaf(self): return True
    
    def label_text(self): return """%s '%s'""" % (re.escape(str(self.cat)), self.lex)
    
    def leaf_count(self): return 1
    
    def clone(self): return copy.copy(self)
    
    def text(self):
        '''Returns a list of text tokens corresponding to the leaves under this node.'''
        return text(self)

    def __getitem__(self, index):
        raise NotImplementedError('Leaf has no children.')

    def count(self):
        return 0
