
def replace_kid(node, old, new):
    # make sure you go through Node#__setitem__, not by modifying Node.kids directly,
    # otherwise parent pointers won't get updated 
    node[node.kids.index(old)] = new
    
#      P                   P
#     / \       ->        / \
#     L  R                L  r
#       / \
#       l  r
def shrink_left(node, parent):
    if parent:
        kid = node[1]
        replace_kid(parent, node, kid)
        return kid
    else: # is root
        return node[1]
    
def inherit_tag(node, other):
    '''Gives _node_ the tag that _other_ has, unless _node_ already has one, or _other_ doesn't.'''
    if node.tag.find(":") == -1 and other.tag.find(":") != -1:
        node.tag += other.tag[other.tag.find(":"):]
