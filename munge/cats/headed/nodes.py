import munge.cats.nodes as B
from apps.util.config import config
from copy import copy, deepcopy

class Head(object):
    '''A Head represents an assigned lexical item.'''
    def __init__(self, lex=None, filler=None):
        self._lex = lex
        self.filler = None

    @property
    def lex(self): 
#        print "%s < %s: lex %s" % (caller(), caller(1), self._lex)
        return self._lex
    @lex.setter
    def lex(self, lex):
        #print "%s < %s: lex <- %s" % (caller(), caller(1), lex)
        self._lex = lex
        
    def __hash__(self):
        if isinstance(self._lex, list): return hash(frozenset(self._lex))
        else: return hash(self._lex)
    def __eq__(self, other):
        return self._lex == other._lex and self.filler
    
    __repr__ = lambda self: "<|%s|>" % (str(self.lex) or "?")

class Slot(object):
    '''A Slot is a mapping from a variable name to a Head.'''
    def __init__(self, var, head_lex=None):
        self.var = var        
        self._head = Head(head_lex)
        
    @property
    def head(self): return self._head
    @head.setter
    def head(self, v): self._head = v
        
    def is_filled(self):
        return self.head.lex is not None
        
    # problem: sometimes two slots have the same var name and same head, but are distinct slots
    # the problem goes away when var names are uniquified
    def __hash__(self):
        return hash(id(self))
#        return hash(self.var) ^ hash(self._head)
    def __eq__(self, other):
        return self is other
#        return self.var == other.var and self._head == other._head
        
    if config.curly_vars:
        def __repr__(self):
            head = ('=' + self.head.lex) if self.head.lex else ''
            return "{" + self.var + head + "}"
    else:
        def __repr__(self):
            if not self.head.lex: head = None
            elif isinstance(self.head.lex, list): 
                head = '<' + ', '.join(self.head.lex) + '>'
            else: head = self.head.lex
            
            return self.var.lower() + (("=" + head) if head else '')
        
class AtomicCategory(B.AtomicCategory):
    '''An AtomicCategory augmented with a Slot field.'''
    def __init__(self, *args, **kwargs):
        var, value = kwargs.pop('var', '?'), kwargs.pop('value', None)
        
        B.AtomicCategory.__init__(self, *args, **kwargs)
        self.slot = Slot(var, value)
        
    if config.show_vars:
        def __repr__(self, *args, **kwargs):
            r = B.AtomicCategory.__repr__(self, *args, **kwargs)
            if kwargs.get('suppress_vars', False): return r
                
            if self.slot:
                r += repr(self.slot)
            return r
            
    def __hash__(self):
        return B.AtomicCategory.__hash__(self) ^ hash(self.slot)

    def clone_with(self, features=None, slot=None):
        ret = AtomicCategory(self.cat, 
                             features if features else copy(self.features))
        ret.slot = slot or self.slot
        return ret
        
if config.curly_vars:
    def bracket_category(s):
        return "(" + s + ")"
else:
    def bracket_category(s):
        return "[" + s + "]"
    
class ComplexCategory(B.ComplexCategory):
    '''A ComplexCategory augmented with a Slot field.'''
    def __init__(self, *args, **kwargs):
        var, value = kwargs.pop('var', '?'), kwargs.pop('value', None)
        
        B.ComplexCategory.__init__(self, *args, **kwargs)
        self.slot = Slot(var, value)
    
    if config.show_vars:
        def __repr__(self, *args, **kwargs):
            r = B.ComplexCategory.__repr__(self, *args, **kwargs)
            if kwargs.get('suppress_vars', False): return r
                    
            if self.slot.var:
                if kwargs.get('first', True):
                    r = bracket_category(r)
        
            r += repr(self.slot)
        
            return r

    def clone_with(self, left=None, direction=None, right=None, features=None, slot=None):
        ret = ComplexCategory(left if left else self._left.clone(),
                              direction if direction else self.direction,
                              right if right else self._right.clone(),
                              self.mode, 
                              features if features else copy(self.features))
        ret.slot = slot or self.slot
        return ret

    def clone(self):
        ret = ComplexCategory(self._left.clone(),
                               self.direction, 
                               self._right and self._right.clone(),
                               self.mode, copy(self.features))
        ret.slot = self.slot
        return ret

    def __hash__(self):
        return B.ComplexCategory.__hash__(self) ^ hash(self.slot)
