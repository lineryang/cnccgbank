class Filter(object):
    '''Every filter extends this class, which defines `don't care' implementations of the four hook
    functions. For each Derivation object (a bundle of the derivation object itself and some metadata),
    the framework calls each of the below methods.'''

    def __init__(self):
        # This will be set to the bundle object this filter is operating on.
        self.context = None
    
    accept_comb_and_slash_index = None
    # IMPORTANT: accept_comb_and_slash_index will not be called unless accept_leaf is defined as well.
    accept_leaf = None
    def accept_derivation(self, deriv): 
        '''This is invoked by the framework after each derivation is processed.'''
        pass
    def output(self): 
        '''This is invoked by the framework after all derivations have been processed.'''
        pass

    # Concrete filters should define a long name ('--long-name') for command-line invocation.
    long_opt = "??"
    # Concrete filters should define a short name ('-l') for command-line invocation.
    opt = "?"
    
    # This is displayed after the long name as an intuitive name for any arguments the filter may expect.
    arg_names = ''
    
    @staticmethod
    def is_abstract(): return False
    