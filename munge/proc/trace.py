# Chinese CCGbank conversion
# ==========================
# (c) 2008-2012 Daniel Tse <cncandc@gmail.com>
# University of Sydney

# Use of this software is governed by the attached "Chinese CCGbank converter Licence Agreement"
# supplied in the Chinese CCGbank conversion distribution. If the LICENCE file is missing, please
# notify the maintainer Daniel Tse <cncandc@gmail.com>.

from optparse import OptionParser, OptionGroup
import sys, re, os

from munge.util.err_utils import warn, info, err
from munge.proc.trace_core import TraceCore
from munge.proc.dynload import get_argcount_for_method

from munge.util.config import config
    
BuiltInPackages = ['munge.proc.builtins', 
                   'munge.proc.tgrep.tgrep', 
                   'apps.cn.tag', 'apps.cn.binarise', 'apps.cn.catlab']

def run_builtin_filter(option, opt_string, value, parser, *args, **kwargs):
    filter_class_name = args[0]
    
    # optparse will return either a single value, or a tuple of values.
    # We wrap a single argument in a tuple for consistency
    if (value is not None) and not isinstance(value, (list, tuple)):
        value = (value, )
        
    parser.values.filters_to_run.append( (filter_class_name, value) )
    
def add_filter_to_optparser(parser, filter):
    '''Given a filter, this registers it with the option parser, allowing it to be selected on the
command line.'''
    argcount = get_argcount_for_method(filter.__init__)
    
    opt_dict = {
        'help': filter.__doc__,     # Help string is the filter docstring
        'dest': filter.long_opt,    # Destination variable is the same as the long option name
        'metavar': filter.arg_names,# Metavar names are supplied by the filter
        'action': 'callback',
        'callback': run_builtin_filter,
        'callback_args': (filter.__name__, ) # Pass in the filter's class name
    }
    
    # If the filter expects arguments, set the correct number of arguments and assume that it takes
    # string arguments (for consistency).
    if argcount > 0:
        opt_dict['nargs'] = argcount
        opt_dict['type'] = 'string'
    
    parser.add_option("-" + filter.opt, "--" + filter.long_opt, **opt_dict)
        
# Adapted from Python Library Reference
def register_filter(option, opt_string, value, parser, *args, **kwargs):
    '''The user is able to specify filters by name using the '-r' switch in this way:
    -r FilterName1 arg1 arg2 -r FilterName2 arg1
This requires us to handle consumption of arguments because we cannot tell at the time
we encounter the filter name how many arguments it expects. This is why the dummy flag
-0 (--end) is required after the use of -r; this tells register_filter when to stop
reading filter arguments.
This callback is invoked by optparse upon encountering a '-r' switch; it consumes all
arguments until another switch is encountered, registering them as arguments to be passed
to the filter when it is invoked.'''
    filter_name = value
    filter_args = []
    
    rargs = parser.rargs # remaining optparse arguments
    while rargs:
        arg = rargs[0]
        
        if ((arg[:2] == '--' and len(arg) > 2) or
            (arg[:1] == '-' and len(arg) > 1 and arg[1] != '-')):
            break
        else:
            filter_args.append( arg )
            del rargs[0]
            
    parser.values.filters_to_run.append( (filter_name, filter_args) )

def set_config_file(option, opt_string, value, parser, *args, **kwargs):
    try:
        config.config_file = value
    except IOError, e:
        err("Couldn't load config file `%s': %s", value, e)
    
def register_builtin_switches(parser):
    '''Registers the command-line switches which are always available as an option group.'''
    group = OptionGroup(parser, title='Built-in operations')

    # This option is 'fake' in that filter_library_switches() ensures that optparser never sees
    # switches beginning with -l: we filter them out early so that we can pass TraceCore a list
    # of all filters to load (which in turn is used by optparser to populate its list of available filters)
    group.add_option("-l", "--load-package", help="Makes available all filters from the given package.",
                      action='append', dest='packages', metavar="PKG")
    group.add_option("-I", "--load-path", help="Makes available all filters under the given path.",
                      action='append', dest='autoload_paths', metavar="PKG")
    group.add_option("-L", "--list-filters", help="Lists all loaded filters.",
                      action='store_true', dest='do_list_filters')
    group.add_option("-r", "--run", help="Runs a filter.", type='string', nargs=1,
                      action='callback', callback=register_filter)
    group.add_option("-R", "--reader-class", help="Forces the use of a given Reader class.",
                      dest='reader_class_name', metavar='CLS')

    group.add_option("-0", "--end", help="Dummy option to separate -r arguments from input arguments.", 
                      action='store_true')
    
    group.add_option("-q", "--quiet", help="Suppress diagnostic messages.", 
                      action='store_false', dest='verbose')
    group.add_option("-v", "--verbose", help="Print diagnostic messages.", 
                      action='store_true', dest='verbose')
    group.add_option("-c", "--config", help="Set config file.", type='string', nargs=1,
                      action='callback', callback=set_config_file)
    group.add_option("-d", "--debug", help="Print debug messages.",
                      action='store_true', dest='debug')
                      
    errors_group = OptionGroup(parser, title='Error handling')
                      
    errors_group.add_option("-b", "--break-on-error", help="Ignore the rest of the document if an error is encountered.",
                      action='store_true', dest='break_on_exception', default=False)

    parser.add_option_group(group)
    parser.add_option_group(errors_group)

def filter_library_switches(argv):
    '''This strips argv of all command-line switches of the form -lPACKAGE where PACKAGE is a 
Python package exposing Filter subclasses, returning a pair (list of PACKAGE names, stripped argv).'''
    new_argv = []
    library_names = []

    for arg in argv:
        matches = re.match(r'-l(.+)', arg)
        if matches:
            library_names.append(matches.group(1))
        else:
            new_argv.append(arg)

    return new_argv, library_names
    
def extract_python_files_under_path(path):
    module_names = []
    for (subpath, dirs, files) in os.walk(path):
        for file in files:
            if file.endswith('.py'):
                subpath_bits = subpath.split(os.sep)
                if subpath_bits[0] == '.': subpath_bits = subpath_bits[1:]
                
                module_names.append( '.'.join(subpath_bits + [file.replace('.py', '')]) )
    return module_names
    
def filter_autoload_paths(argv):
    new_argv = []
    library_names = []
    
    for arg in argv:
        matches = re.match(r'-I(.+)', arg)
        if matches:
            library_names += extract_python_files_under_path(matches.group(1))
        else:
            new_argv.append(arg)
    
    return new_argv, library_names
    
def main(argv):
    parser = OptionParser(conflict_handler='resolve') # Intelligently resolve switch collisions
    parser.set_defaults(verbose=False, filters_to_run=[], packages=BuiltInPackages)

    # If any library loading switches (-l) are given, collect their names and remove them from argv
    argv, user_defined_libraries = filter_library_switches(argv)
    argv, autoloaded_libraries   = filter_autoload_paths(argv)
    
    # Load built-in filters (those under BuiltInPackages)
    # Load user-requested filters (passed by -l on the command line)
    all_libraries = BuiltInPackages + user_defined_libraries + autoloaded_libraries
    tracer = TraceCore(libraries=all_libraries)
    
    # For each available filter, allow it to be invoked with switches on the command line
    for filter in tracer.available_filters_dict.values(): add_filter_to_optparser(parser, filter)
    # Load built-in optparse switches
    register_builtin_switches(parser)

    if len(argv) <= 1:
        parser.print_help()
        sys.exit(1)
    
    # Perform option parse, check for user-requested filter classes
    opts, remaining_args = parser.parse_args(argv)
    # Done with parser
    parser.destroy()
    
    if opts.debug:
        config.set(debug=True)
            
    # Set verbose switch if given on command line
    tracer.verbose = opts.verbose
    tracer.break_on_exception = opts.break_on_exception
    
    # Set override Reader if given on command line
    tracer.reader_class_name = opts.reader_class_name
    
    # Take remaining arguments as input file names
    files = remaining_args[1:] # remaining_args[0] seems to be sys.argv[0]
    
    # If switch -L was passed, dump out all available filter names and quit
    if opts.do_list_filters:
        tracer.list_filters()
        sys.exit(0)
        
    # Run requested filters
    try:
        tracer.run(opts.filters_to_run, files)
    except RuntimeError, e:
        err('RuntimeError: %s', e)
        sys.exit(1)
    except IOError, e: # file not found, for instance
        sys.exit(2)

if __name__ == '__main__':
    #try:
    #   import psyco
    #   psyco.full()
    #except ImportError: pass

    main(sys.argv)
