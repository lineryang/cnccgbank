
def preserving_split(str, split_chars, skip_chars=" \t\r\n", suppressors=''):
    '''Returns an iterator yielding successive tokens from _str_ as split on three
    kinds of separators. 
      - _split_chars_ will split the string, and appear in the resulting stream.
      - _skip_chars_ will split the string, but will not appear in the stream.
      - Any text between the pair of _suppressors_ (if given) will be split only
        on skip_chars and not on split_chars.
    The returned iterator supports an additional _peek_ method which returns the same
    value as _next_ without consuming a value from the stream.'''

    class PressplitIterator:
        def __init__(self, str, split_chars, skip_chars, suppressors):
            def _preserving_split():
                use_suppressors = len(suppressors) == 2

                in_node = False
                cur = []
                for char in str:
                    if (not in_node and char in split_chars) or \
                            char in skip_chars or \
                            char in suppressors:
                        if cur: 
                            yield ''.join(cur)
                            del cur[:]

                        if use_suppressors:
                            if char == suppressors[0]: in_node = True
                            elif char == suppressors[1]: in_node = False

                        if char in split_chars or char in suppressors: yield char
                    else:
                        cur.append(char)

                if cur: yield ''.join(cur)

            self.generator = _preserving_split()

            # generator may be empty and raise StopIteration
            try:
                self.top = self.generator.next()
            except StopIteration:
                self.top = None

        def __iter__(self): return self

        def peek(self): return self.top
        def next(self):
            if self.top is None: raise StopIteration

            previous_top = self.top
            try:
                self.top = self.generator.next()
            except StopIteration: 
                self.top = None
            return previous_top

    return PressplitIterator(str, split_chars, skip_chars, suppressors)

