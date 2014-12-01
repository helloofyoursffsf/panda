#!/usr/bin/env python

import os
import sys
import re
import pdb
proto_re = re.compile("(.+)\s+(\S+)\s*\((.*)\)")

KNOWN_TYPES = ['int', 'double', 'float', 'char', 'short', 'long',
               'uint8_t', 'uint16_t', 'uint32_t', 'uint64_t']

def generate_code(functions, module, includes):
    code =  "#ifndef __%s_EXT_H__\n" % (module.upper())
    code += "#define __%s_EXT_H__\n" % (module.upper())
    code +="""
/*
 * DO NOT MODIFY. This file is automatically generated by scripts/apigen.py,
 * based on the <plugin>_int.h file in your plugin directory.
 */

#include <dlfcn.h>
#include "panda_plugin.h"

"""
    for include in includes:
        code+= include + "\n"

    for function in functions:
        argtypelist = ",".join([x[0] for x in  function[2]])
        code+= "typedef " + function[0] + "(*" + function[1]+ "_t)(" + argtypelist + ");\n"
        code+= "static " + function[1] + "_t __" + function[1] + " = NULL;\n"
        
        arglist = ",".join([x[0] + ' ' + x[1] for x in function[2]])
        # if an arg is an r-value reference, we need to pass it with std::move
        argnamelist = ",".join(map(lambda x: 'std::move({0})'.format(x[1]) if x[0].endswith('&&') else x[1], function[2]))
        code += "inline " + function[0] + " " +function[1]+"("+arglist+"""){
    assert(__"""+function[1]+""");
    return __"""+function[1]+"("+argnamelist+""");
}
"""
    code += "#define API_PLUGIN_NAME \"" + module
    code += """\"\n#define IMPORT_PPP(module, func_name) { \\
 __##func_name = (func_name##_t) dlsym(module, #func_name); \\
 char *err = dlerror(); \\
 if (err) { \\
    printf("Couldn't find %s function in library %s.\\n", #func_name, API_PLUGIN_NAME); \\
    printf("Error: %s\\n", err); \\
    return false; \\
 } \\
}
"""
    code += "inline bool init_%s_api(void){" % module


    code += """
    void *module = panda_get_plugin_by_name("panda_" API_PLUGIN_NAME ".so");
    if (!module) {
        printf("In trying to add plugin, couldn't load %s plugin\\n", API_PLUGIN_NAME);
        return false;
    }
    dlerror();
""" 

    for function in functions:
        code += "IMPORT_PPP(module, " + function[1] + ")\n"

    code += """return true;
}

#undef API_PLUGIN_NAME
#undef IMPORT_PPP

#endif
"""

    return code

bad_keywords = ['static', 'inline']
keep_keywords = ['const', 'unsigned']
def resolve_type(modifiers, name):
    modifiers = modifiers.strip()
    tokens = modifiers.split()
    if len(tokens) > 1:
        # we have to go through all the keywords we care about
        relevant = []
        for token in tokens[:-1]:
            if token in keep_keywords:
                relevant.append(token)
            if token in bad_keywords:
                raise Exception("Invalid token in API function definition")
        relevant.append(tokens[-1])
        rtype = " ".join(relevant)
    else:
        rtype = tokens[0]
    if name.startswith('*'):
        return rtype+'*', name[1:]
    else:
        return rtype, name

def generate_api(plugin_name, plugin_dir):
    print plugin_name
    if ("%s_int.h" % plugin_name) not in os.listdir(plugin_dir):
        return


    print "Building API for plugin", plugin_name,
    functions = []
    includes = []
    with open(os.path.join(plugin_dir, '{0}_int.h'.format(plugin_name))) as API:
        for line in API:
            line = line.strip();
            if line and not line.startswith('#') and not (re.match("^/", line)):
                print line
                match = proto_re.match(line)
                rtype, name, arglist = match.groups()
                rtype, name = resolve_type(rtype, name)

                args = []
                for arg in [x.strip() for x in arglist.split(',')]:
                    if arg == "void":
                        argtype, argname = ("void", "")
                    else:
                        argtype, argname = arg.rsplit(None, 1)
                    args.append(resolve_type(argtype, argname))
                functions.append((rtype, name, args))
            elif line and line.startswith('#include'):
                includes.append(line)
    code = generate_code(functions, plugin_name, includes)
    with open(os.path.join(plugin_dir, '{0}_ext.h'.format(plugin_name)), 'w') as extAPI:
        extAPI.write(code)
    print "... Done!"

# figure out where we are
if len(sys.argv) > 1:
    plugins_dir = sys.argv[1]
else:
    if os.getcwd().endswith('panda_plugins'):
        plugins_dir = os.getcwd()
    elif os.getcwd().endswith('qemu'):
        plugins_dir = os.getcwd() + "/panda_plugins"
    else:
        print "Usage: %s plugins_dir" % sys.argv[0]
        sys.exit(1)

for plugin in os.listdir(plugins_dir):
    plugindir = os.path.join(plugins_dir, plugin)
    if os.path.isdir(plugindir):
        generate_api(plugin, plugindir)