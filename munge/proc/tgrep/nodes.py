# Chinese CCGbank conversion
# ==========================
# (c) 2008-2012 Daniel Tse <cncandc@gmail.com>
# University of Sydney

# Use of this software is governed by the attached "Chinese CCGbank converter Licence Agreement"
# supplied in the Chinese CCGbank conversion distribution. If the LICENCE file is missing, please
# notify the maintainer Daniel Tse <cncandc@gmail.com>.

from munge.proc.tgrep.ops import *
from munge.util.err_utils import warn, err
from munge.util.exceptions import TgrepException
import re
import operator

class AttributeAccessibleDict(dict):
    '''A dict subclass allowing attribute access to its keys.'''
    def __getattr__(self, attr):
        '''Converts attribute access to key access, but returns None if the key is not present.'''
        return self.get(attr.upper(), None)
    def __setattr__(self, attr, v):
        self[attr.upper()] = v

Context = AttributeAccessibleDict

class Node(object):
    '''Represents a head node matcher (the anchor) and its sequence of constraints.'''
    def __init__(self, anchor, constraints=None):
        self.anchor = anchor
        
        if not constraints: constraints = []
        self.constraints = constraints
        
    def __repr__(self):
        return "%s%s%s" % (self.anchor, 
                           ' ' if self.constraints else '', 
                           ' '.join(str(c) for c in self.constraints))
        
    def is_satisfied_by(self, node, context=Context()):
        if self.anchor.is_satisfied_by(node, context):
            # XXX: side effects for unevaluated constraints will not be executed (due to short-circuiting)
            return all(constraint.is_satisfied_by(node, context) for constraint in self.constraints)
        return False
    
class Reluctant(object):
    '''A constraint which always succeeds, but allows side-effects a chance to run.'''
    def __init__(self, constraint):
        self.constraint = constraint
        
    def __repr__(self):
        return "? %s" % repr(self.constraint)
        
    def is_satisfied_by(self, node, context):
        self.constraint.is_satisfied_by(node, context)
        return True
        
class Constraint(object):
    '''Represents a single constraint, characterised by an operator symbol and an argument node.'''
    def __init__(self, operator, rhs=None):
        self.operator = operator
        self.rhs = rhs
        
        self.op_func = self.get_op_func_for(self.operator)

    def get_op_func_for(self, operator):
        if operator in Operators:
            return Operators[operator]
        else:
            for regex, op_func_maker in IntArgOperators.iteritems():
                matches = re.match(regex, operator)
                
                if matches:
                    return op_func_maker(*matches.groups())
            else:
                err('Invalid operator %s encountered.', self.operator)
        
    def __repr__(self):
        return "%s %s" % (self.operator, self.rhs)
    def is_satisfied_by(self, node, context):
        try:
            # Determine whether rhs matches the candidate node
            return self.op_func(self.rhs, node, context)
        except KeyError:
            warn("Invalid operator %s encountered.", self.operator)

        return False
        
class Negation(object):
    '''Represents the negation of a constraint.'''
    def __init__(self, inner):
        self.inner = inner
    def __repr__(self):
        return "!%s" % self.inner
    def is_satisfied_by(self, node, context):
        return not self.inner.is_satisfied_by(node, context)
        
class Alternation(object):
    '''Represents a disjunction between two constraints.'''
    def __init__(self, lhs, rhs):
        self.lhs, self.rhs = lhs, rhs
    def __repr__(self):
        return "%s | %s" % (self.lhs, self.rhs)
    def is_satisfied_by(self, node, context):
        return self.lhs.is_satisfied_by(node, context) or self.rhs.is_satisfied_by(node, context)
        
class Group(object):
    def __init__(self, node):
        self.node = node
    def __repr__(self):
        return "{%s}" % self.node
    def is_satisfied_by(self, node, context):
        return self.node.is_satisfied_by(node, context)
        
class ConstraintGroup(object):
    '''Matches when all sub-constraints are matched.'''
    def __init__(self, constraints):
        self.constraints = constraints
    def __repr__(self):
        return "[%s]" % ' '.join(str(c) for c in self.constraints)
    def is_satisfied_by(self, node, context):
        return all(constraint.is_satisfied_by(node, context) for constraint in self.constraints)
 
class Atom(object):
    '''Matches only on an exact string match of the node's _cat_.'''
    def __init__(self, value):
        self.value = value
    def __repr__(self):
        return self.value
    def is_satisfied_by(self, node, context):
        return self.value == str(node.cat)
        
class StoreAtom(object):
    '''Matches exactly what its body matches, with the side effect of capturing the matched node to a variable.'''
    def __init__(self, atom, var):
        self.atom = atom
        self.var = var
    def __repr__(self):
        return "%s=%s" % (self.atom, self.var)
    def is_satisfied_by(self, node, context):
        satisfied = self.atom.is_satisfied_by(node, context)
        if satisfied:
            context[self.var] = node
        return satisfied
        # # store into context as side effect
        # context[self.var] = self.atom
        # # TODO: Should we prevent the just-assigned variable from being used when evaluating this node?
        # return self.atom.is_satisfied_by(node, context)
        
class AtomValue(object):
    '''Matches tree nodes which are identical to the captured tree node.'''
    def __init__(self, var, evaluate):
        self.var = var
        self.evaluate = evaluate
        
    def is_satisfied_by(self, node, context):
        if self.var not in context:
            raise TgrepException('No variable %s exists in the context.' % self.var)
        stored_node = context[self.var]
        #return atom.is_satisfied_by(node, context)
        # TODO: a node only matches against itself? or against something with the same label as itself?
        # XXX: This defines two nodes as equal if they are the same modulo features (which is what we often want)
        return self.evaluate(stored_node, node)
        
class GetLex(AtomValue):
    '''Matches tree nodes which have a lexical item identical to that of the captured tree node.'''
    def __init__(self, var):
        AtomValue.__init__(self, var, lambda a, b: a.lex == b.lex)
    def __repr__(self):
        return "^=%s" % self.var
        
from apps.cn.fix_utils import base_tag
class GetBaseTag(AtomValue):
    '''Matches tree nodes which are identical in category (with function and munge tags stripped) to
the captured tree node.'''
    def __init__(self, var):
        AtomValue.__init__(self, var, lambda a, b: base_tag(a.cat) == base_tag(b.cat))
    def __repr__(self, var):
        return "%%=%s" % self.var
        
class GetAtom(AtomValue):
    '''Matches tree nodes which are identical in category to the captured tree node.'''
    def __init__(self, var):
        AtomValue.__init__(self, var, lambda a, b: a.cat.equal_respecting_features(b.cat))
    def __repr__(self):
        return "=%s" % self.var
                
class NotAtom(AtomValue):
    def __init__(self, var):
        AtomValue.__init__(self, var, lambda a, b: not a.cat.equal_respecting_features(b.cat))
    def __repr__(self):
        return "~%s" % self.var

class MatchLex(object):
    def __init__(self, lex_to_match, quoted=False):
        self.lex_to_match = lex_to_match
        self.quoted = quoted
    def __repr__(self):
        lex = "\"%s\"" % self.lex_to_match if self.quoted else self.lex_to_match
        return "^%s" % lex
    def is_satisfied_by(self, node, context):
        if not node.is_leaf(): return False
        return node.lex == self.lex_to_match
        
class MatchCat(object):
    def __init__(self, cat_to_match, quoted=False):
        self.cat_to_match = cat_to_match
        self.quoted = quoted
    def __repr__(self):
        cat = "\"%s\"" % self.cat_to_match if self.quoted else self.cat_to_match
        return "@%s" % cat
    def is_satisfied_by(self, node, context):
        return str(node.category) == self.cat_to_match        
        
class REValue(object):
    def __init__(self, source, anchor_at_start=True, unicode=False):
        self.source = source
        self.unicode = unicode
        self.regex = re.compile(source, re.UNICODE if unicode else 0)
        self.match_method = self.regex.match if anchor_at_start else self.regex.search
        
class RELex(REValue):
    def __init__(self, source, anchor_at_start=True, unicode=False):
        REValue.__init__(self, source, anchor_at_start, unicode)
    def __repr__(self):
        return "^/%s/" % self.source
    def is_satisfied_by(self, node, context):
        if not node.is_leaf(): return False
        if self.unicode:
            return self.match_method(node.lex.decode('u8')) is not None
        else:
            return self.match_method(node.lex) is not None
        
class RECat(REValue):
    def __init__(self, source, anchor_at_start=True, unicode=False):
        REValue.__init__(self, source, anchor_at_start, unicode)
    def __repr__(self):
        return "@/%s/" % self.source
    def is_satisfied_by(self, node, context):
        return self.match_method(str(node.category)) is not None
        
class RE(REValue):
    '''Matches tree nodes whose category labels satisfy a regex.'''
    def __init__(self, source, anchor_at_start=True, unicode=False):
        REValue.__init__(self, source, anchor_at_start, unicode)
    def __repr__(self):
        return "/%s/" % self.source
    def is_satisfied_by(self, node, context):
        return self.match_method(str(node.cat)) is not None

class All(object):
    '''Matches unconditionally against any tree node.'''
    def __repr__(self):
        return "*"
    def is_satisfied_by(self, node, context):
        return True

