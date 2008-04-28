from __future__ import with_statement
import sys, re, os

from optparse import OptionParser
from glob import glob

from munge.util.err_utils import warn, info, err

from munge.quote.span import SpanQuoter
from munge.quote.shift import ShiftComma

from munge.penn.io import PTBReader
from munge.ccg.io import CCGbankReader
from munge.ccg.deps_io import CCGbankDepsReader

from munge.trees.traverse import text, text_without_quotes_or_traces, text_without_traces

DefaultLogFile = "quote_error"

def register_builtin_switches(parser):
    parser.set_defaults(punct_method="shift",
                        quote_method="span",
                        quotes="both",
                        higher="left",
                        quiet=False,
                        log=True,
                        logfile=DefaultLogFile)
                        
    parser.add_option("-i", "--penn-in", help="Path to wsj/ directory", action="store",
                      dest="penn_in", metavar="DIR")
    parser.add_option("-I", "--ccgbank-in", help="Path to CCGbank AUTO/ and PARG/ directory", action="store",
                      dest="ccg_in", metavar="DIR")
    parser.add_option("-o", "--output", help="Output directory for quoted data", dest="outdir", metavar="DIR"),
    parser.add_option("-p", "--punct-method", choices=('none', 'swap', 'shift'),
                      help="Algorithm for handling absorbed punctuation (none|swap|shift)",
                      dest="punct_method", metavar='ALGO')
    parser.add_option("-Q", "--quote-method", choices=('span', 'lca'),
                      help="Algorithm for inserting quotes (span|lca)",
                      dest="quote_method", metavar='ALGO')
    parser.add_option("-d", "--insert", choices=('both', 'left', 'right'),
                      help="Which quotes to reinsert (both|left|right)",
                      dest="quotes", metavar='DIR')
    parser.add_option("-H", "--higher", choices=('left', 'right'),
                      help="Which of the opening (left) or closing (right) quote is the higher in the resulting tree",
                      dest="higher", metavar='DIR')
    parser.add_option("--log", help="Log derivations which cause problems to a file", dest="logfile", metavar="FILE")
    parser.add_option("-q", "--quiet", help="Produce less output", action="store_true", dest="quiet")
    
# required_args maps the name of the 'dest' variable of each required option to a summary of its switches (this text is
# shown to the user)
required_args = {
    "penn_in": "-i (--penn-in)",
    "ccg_in" : "-I (--ccgbank-in)",
    "outdir" : "-o (--output)"
}
def check_for_required_args(opts):
    '''Ensures that the required arguments are all present, and notifies the user as to which of them are not.'''
    arg_missing = False
    for (required_arg, arg_switches) in required_args.iteritems():
        if getattr(opts, required_arg, None) is None:
            err("Argument %s is mandatory.", arg_switches)
            arg_missing = True

    if arg_missing:
        sys.exit(1)
            
def fix_secdoc_string(secdoc):
    '''Given a section/document specifier of the form S:D, where S or D may be absent, returns a specifier string
with S and D padded by a zero to 2 digits if necessary, or with an absent S or D component replaced by an asterisk.'''
    if secdoc is None:
        return '*'
    if len(secdoc) == 1:
        return '0' + secdoc
    return secdoc
    
deriv_re = re.compile(r'([*\d]+)?:([*\d]+)?')
def parse_requested_derivs(args):
    '''Makes each section/document specifier canonical using fix_secdoc_string.'''
    result = []
    
    for arg in args:
        match = deriv_re.match(arg)
        if match and len(match.groups()) == 2:
            sec, doc = map(fix_secdoc_string, match.groups())
            
            result.append( (sec, doc) )
            
    return result

def match_trees(penn_trees, ccg_trees):
    '''Given two lists, of PTB and CCGbank trees which we believe to belong to the same document file, this removes
those PTB trees which do not correspond to any CCGbank tree.'''
    cur_ptb_index = 0
    result = []
    
    for ccg_bundle in ccg_trees:
        ccg_tree_matched = False
        
        while not ccg_tree_matched:
            if cur_ptb_index >= len(penn_trees): break
        
            ccg_text = text(ccg_bundle.derivation)
            ptb_text = text_without_quotes_or_traces(penn_trees[cur_ptb_index].derivation)
        
            if ptb_text != ccg_text:
                warn("In document %s:", ccg_bundle.label())
                warn("\tCCG tokens: %s", ' '.join(ccg_text))
                warn("\tPTB tokens: %s", ' '.join(ptb_text))
                pass
            else:
                result.append( penn_trees[cur_ptb_index] )
                ccg_tree_matched = True
            
            cur_ptb_index += 1
            
    return result
            
from munge.util.list_utils import first_index_such_that, last_index_such_that
def spans(ptb_tree):
    '''Returns a sequence of tuples (B, E), where the Bth token from the start, and the Eth token from the end
of the given PTB derivation span a quoted portion of the text.'''
    # This is implemented as returning a sequence for generality: our naive implementation only ever locates a
    # single (outermost) span of quoted text, so this implementation only ever returns a sequence of at most one
    # tuple. A smarter implementation would handle and identify nested quotes, as well as multiple spans.
    ptb_tokens = text_without_traces(ptb_tree)

    # TODO: this definition of a quote tag is broken!!
    yield (first_index_such_that(lambda e: e in ("``", "`"), ptb_tokens),
           first_index_such_that(lambda e: e in ("''", "'"), reversed(ptb_tokens)))
           
def fix_dependency(dep, quote_index):
    '''Updates the dependency data to accommodate the insertion of a new leaf at a given index. This means that
every index to the right of the newly inserted node must be incremented.'''
    for dep_row in dep:
        if quote_index >= dep_row.fields[0]:
            dep_row.fields[0] += 1
        if quote_index >= dep_row.fields[1]:
            dep_row.fields[1] += 1
    
    return dep
           
def fix_dependencies(dep, quote_indices):
    '''Updates the dependency data to accommodate the insertion of an open and/or close quote node, given the indices
at which each occurs.'''
    open_quote_index, close_quote_index = quote_indices
    
    if open_quote_index:
        dep = fix_dependency(dep, open_quote_index)
        quote_indices = map(lambda e: e and e+1, quote_indices)
    if close_quote_index:
        dep = fix_dependency(dep, close_quote_index + 1)
        quote_indices = map(lambda e: e and e+1, quote_indices)
        
    return dep 

def process(ptb_file, ccg_file, deps_file, ccg_auto_out, ccg_parg_out, higher, quotes, quoter):
    '''Reinstates quotes given a PTB file and its corresponding CCGbank file and deps file.'''
    with file(ccg_auto_out, 'w') as ccg_out:
        with file(ccg_parg_out, 'w') as parg_out:
            penn_trees = list(PTBReader(ptb_file))
            ccg_trees  = list(CCGbankReader(ccg_file))
            deps       = list(CCGbankDepsReader(deps_file))
            
            matched_penn_trees = match_trees(penn_trees, ccg_trees)

            for (ptb_bundle, ccg_bundle, dep) in zip(matched_penn_trees, ccg_trees, deps):
                ptb_tree, ccg_tree = ptb_bundle.derivation, ccg_bundle.derivation

                for (span_start, span_end) in spans(ptb_tree):
                    if not (span_start or span_end): continue
                    
                    info("Reinstating quotes to %s", ccg_bundle.label())
                    
                    ccg_tree, quote_indices = quoter.attach_quotes(ccg_tree, span_start, span_end, higher, quotes)
                    dep = fix_dependencies(dep, quote_indices)
                    
                print >> parg_out, dep
                print >> ccg_out, ccg_bundle
    
ptb_file_re = re.compile(r'(\d{2})/wsj_\d{2}(\d{2})\.mrg$')
def main(argv):
    parser = OptionParser()

    register_builtin_switches(parser)                        
    opts, args = parser.parse_args(argv)
    
    check_for_required_args(opts)
    
    quoter_class = {
        'span': SpanQuoter,
#        'lca' : LCAQuoter
    }[opts.quote_method]
    punct_class = {
#        'swap' : SwapComma,
        'shift': ShiftComma
    }.get(opts.punct_method, None)
    
    quoter = quoter_class(punct_class)
    
    remaining_args = args[1:]
    if not remaining_args:
        # If no sec/doc specifiers are given, assume 'all sections all documents'
        remaining_args.append(':')
        
    ptb_files_spec = parse_requested_derivs(remaining_args)
    
    for sec_glob, doc_glob in ptb_files_spec:
        for ptb_file in glob(os.path.join(opts.penn_in, sec_glob, "wsj_%s%s.mrg" % (sec_glob, doc_glob))):
            info("Processing %s", ptb_file)
            
            matches = ptb_file_re.search(ptb_file)
            if matches and len(matches.groups()) == 2:
                sec, doc = matches.groups()
                
                ccg_file =  os.path.join(opts.ccg_in, 'AUTO', sec, "wsj_%s%s.auto" % (sec, doc))
                deps_file = os.path.join(opts.ccg_in, 'PARG', sec, "wsj_%s%s.parg" % (sec, doc))
                
                if not opts.quiet:
                    if not os.path.exists(ccg_file):
                        warn("No corresponding CCGbank file %s for Penn file %s", ccg_file, ptb_file)
                    if not os.path.exists(deps_file):
                        warn("No corresponding CCGbank dependency file %s for CCG file %s", deps_file, ccg_file)
                        
                ccg_auto_dir, ccg_parg_dir = [os.path.join(opts.outdir, part, sec) for part in ('AUTO', 'PARG')]
                if not os.path.exists(ccg_auto_dir): os.makedirs(ccg_auto_dir)
                if not os.path.exists(ccg_parg_dir): os.makedirs(ccg_parg_dir)
                
                ccg_auto_out, ccg_parg_out = (os.path.join(ccg_auto_dir, 'wsj_%s%s.auto' % (sec, doc)),
                                              os.path.join(ccg_parg_dir, 'wsj_%s%s.parg' % (sec, doc)))
                                              
                process(ptb_file, ccg_file, deps_file, ccg_auto_out, ccg_parg_out, 
                                     opts.higher, opts.quotes, quoter)
                
            else:
                warn("Could not find, so ignoring %s", ptb_file)

if __name__ == '__main__':
    main(sys.argv)