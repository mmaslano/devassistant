import six

from devassistant import exceptions

class YamlChecker(object):
    _yaml_typenames = {dict: 'mapping',
                       list: 'list',
                       six.text_type: 'string',
                       six.binary_type: 'string',
                       int: 'integer',
                       float: 'float',
                       bool: 'boolean'}
    for s in six.string_types:
        _yaml_typenames[s] = 'string'

    def __init__(self, sourcefile, parsed_yaml):
        self.sourcefile = sourcefile
        self.parsed_yaml = parsed_yaml

    @classmethod
    def fullcheck(cls, sourcefile, parsed_yaml):
        checker = cls(sourcefile, parsed_yaml)
        checker.check()

    def check(self):
        """Checks whether loaded yaml is well-formed according to syntax defined for
        version 0.9.0 and later.

        Raises:
            YamlError: (containing a meaningful message) when the loaded Yaml
                is not well formed
        """
        if not isinstance(self.parsed_yaml, dict):
            msg = 'In {0}:\n'.format(self.sourcefile)
            msg += 'Assistants and snippets must be Yaml mappings, not "{0}"!'.\
                    format(self.parsed_yaml)
            raise exceptions.YamlTypeError(msg)
        self._check_fullname(self.sourcefile)
        self._check_description(self.sourcefile)
        self._check_args(self.sourcefile)
        self._check_dependencies(self.sourcefile)
        self._check_run(self.sourcefile)

    def _check_fullname(self, source):
        path = [source]
        self._assert_str(self.parsed_yaml.get('fullname', ''), path)
 
    def _check_description(self, source):
        path = [source]
        self._assert_str(self.parsed_yaml.get('description', ''), path)

    def _check_args(self, source):
        path = [source]
        args = self.parsed_yaml.get('args', {})
        self._assert_dict(args, 'args', path)
        path.append('args')
        for argn, argattrs in args.items():
            self._check_one_arg(path, argn, argattrs)

    def _check_one_arg(self, path, argn, argattrs):
        self._assert_dict(argattrs, argn, path)
        path = path + [argn]
        for attrn, attrval in argattrs.items():
            if attrn in ['use', 'help', 'nargs', 'metavar', 'dest']:
                self._assert_str(attrval, attrn, path)
            elif attrn in ['const', 'default']:
                self._assert_struct_type(attrval,
                                         attrn,
                                         (int, float, bool) + six.string_types,
                                         path)
            elif attrn in ['flags', 'choices']:
                self._assert_list(attrval, attrn, path)
            elif attrn == 'action':
                self._assert_struct_type(attrval, attrn, (list, ) + six.string_types, path)
            elif attrn == 'gui_hints':
                # TODO: maybe check this more thoroughly
                self._assert_dict(attrval, attrn, path)

    def _check_dependencies(self, source):
        path = [source]
        depsects = filter(lambda a: a[0].startswith('dependencies'), self.parsed_yaml.items())
        for name, struct in depsects:
            self._check_one_dependencies_section(path, name, struct)

    def _check_one_dependencies_section(self, path, sectname, struct):
        self._assert_list(struct, sectname, path)
        path = path + [sectname]
        for comm in struct:
            self._assert_command_dict(comm, comm, path)
            command_type, command_input = list(comm.items())[0]
            self._assert_str(command_type, command_type, path)
            if command_type == 'use':
                self._assert_str(command_input, command_type, path)
            else:
                self._assert_list(command_input, command_type, path)
            if command_type.startswith('if ') or command_type.startswith('else '):
                self._check_one_dependencies_section(path, command_type, command_input)

    def _check_run(self, source):
        path = [source]
        runsects = list(filter(lambda a: a[0].startswith('run'), self.parsed_yaml.items()))
        for s in ['pre_run', 'post_run']:
            if s in self.parsed_yaml:
                runsects.append((s, self.parsed_yaml[s]))
        for name, struct in runsects:
            self._check_execution_section(path, name, struct)

    def _check_execution_section(self, path, sectname, struct):
        # TODO: lots of duplicated code with _check_one_dependencies_section - can we improve?
        extra_info = 'Each "execution section" (for example a run section or a section after ' +\
            '"command runner" with execution flag ("~")) has to be a list of commands ' +\
            'or an expression.'
        self._assert_struct_type(struct,
                                 sectname,
                                 (list,) + six.string_types,
                                 path,
                                 extra_info)
        path = path + [sectname]
        if isinstance(struct, list):
            for comm in struct:
                self._assert_command_dict(comm, comm, path)
                command_type, command_input = list(comm.items())[0]
                self._assert_str(command_type, command_type, path)
                if command_type.startswith('if ') or command_type.startswith('else ') or \
                   command_type.startswith('for ') or command_type.endswith('~'):
                    self._check_execution_section(path, command_type, command_input)
                else:
                    self._check_input_section(path, command_type, command_input)
        else:  # expression
            pass  # TODO: check expression syntax here or leave it up for the actual run?

    def _check_input_section(self, path, sectname, struct):
        # input section can be pretty much anything; we just want to check that when there's
        # a dict somewhere in the structure  and one of its members ends with execution flag,
        # we check the execution section assigned to this member
        path = path + [sectname]
        if isinstance(struct, list):
            for item in struct:
                if isinstance(item, (dict, list)):
                    self._check_input_section(path, item, item)
        elif isinstance(struct, dict):
            for k, v in struct.items():
                if k.endswith('~'):
                    self._check_execution_section(path, k, v)
                else:
                    self._check_input_section(path, k, v)

    def _assert_dict(self, struct, name, path=None, extra_info=None):
        self._assert_struct_type(struct, name, (dict,), path, extra_info)

    def _assert_str(self, struct, name, path=None, extra_info=None):
        self._assert_struct_type(struct, name, six.string_types, path, extra_info)

    def _assert_list(self, struct, name, path=None, extra_info=None):
        self._assert_struct_type(struct, name, (list,), path, extra_info)

    def _assert_command_dict(self, struct, name, path=None, extra_info=None):
        """Checks whether struct is a command dict (e.g. it's a dict and has 1 key-value pair."""
        self._assert_dict(struct, name, path, extra_info)
        if len(struct) != 1:
            err = [self._format_error_path(path + [name])]
            err.append('Commands of run and dependencies sections must be mapping with '
                       'exactly 1 key-value pair, got {0}: {1}'.format(len(struct), struct))
            if extra_info:
                err.append(extra_info)
            raise exceptions.YamlSyntaxError('\n'.join(err))

    def _assert_struct_type(self, struct, name, types, path=None, extra_info=None):
        """Asserts that given structure is of any of given types.

        Args:
            struct: structure to check
            name: displayable name of the checked structure (e.g. "run_foo" for section run_foo)
            types: list/tuple of types that are allowed for given struct
            path: list with a source file as a first element and previous names
                  (as in name argument to this method) as other elements
            extra_info: extra information to print if error is found (e.g. hint how to fix this)
        Raises:
            YamlTypeError: if given struct is not of any given type; error message contains
                           source file and a "path" (e.g. args -> somearg -> flags) specifying
                           where the problem is
        """
        wanted_yaml_typenames = set()
        for t in types:
            wanted_yaml_typenames.add(self._yaml_typenames[t])
        wanted_yaml_typenames = ' or '.join(wanted_yaml_typenames)
        actual_yaml_typename = self._yaml_typenames[type(struct)]
        if not isinstance(struct, types):
            err = []
            if path:
                err.append(self._format_error_path(path + [name]))
            err.append('  Expected {w} value for "{n}", got value of type {a}: "{v}"'.\
                    format(w=wanted_yaml_typenames,
                           n=name,
                           a=actual_yaml_typename,
                           v=struct))
            if extra_info:
                err.append('Tip: ' + extra_info)
            raise exceptions.YamlTypeError('\n'.join(err))

    def _format_error_path(self, path):
        err = []
        err.append('Source file {p}:'.format(p=path[0]))
        path2print = ['(top level)'] + [six.text_type(x) for x in path[1:]]
        err.append('  Problem in: ' + ' -> '.join(path2print))
        return '\n'.join(err)


check = YamlChecker.fullcheck
