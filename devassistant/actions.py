from devassistant import settings

actions = {}


def register_action(action):
    """Decorator that adds an action class to active actions.
    Only toplevel actions should be registered, subactions will be
    read from Action.get_subactions()."""
    actions[action] = _register_actions_recursive(action, {})
    return action


def _register_actions_recursive(action, subact_dict):
    for a in action.get_subactions():
        subact_dict[a] = {}
        _register_actions_recursive(a, subact_dict[a])
    return subact_dict


def is_action_run(**kwargs):
    first_act = kwargs.get(settings.SUBASSISTANT_N_STRING.format(0), None)
    if first_act in map(lambda a: a.name, actions.keys()):
        return True
    return False


def get_action_to_run(level=0, **kwargs):
    return _get_action_to_run_recursive(level, actions, **kwargs)


def _get_action_to_run_recursive(level, subact_dict, **kwargs):
    alevel = settings.SUBASSISTANT_N_STRING.format(level)
    aname = kwargs.get(alevel, None)
    if not aname:
        return None
    for a, suba in subact_dict.items():
        if a.name == aname:
            if settings.SUBASSISTANT_N_STRING.format(level + 1) in kwargs:
                return _get_action_to_run_recursive(level + 1, suba, **kwargs)
            else:
                return a


class Action(object):
    """Superclass of custom actions of devassistant"""

    name = 'action'
    description = 'Action description'
    args = []

    @classmethod
    def get_subactions(cls):
        return []

    @classmethod
    def run(cls, **kwargs):
        """Runs this actions, accepts arguments parsed from cli/retrieved from gui.

        Raises:
            devassistant.exceptions.ExecutionExceptions if something goes wrong
        """
        raise NotImplementedError()


@register_action
class HelpAction(Action):
    """Can gather info about all actions and assistant types and print it nicely."""
    name = 'help'
    description = 'Print detailed help'

    @classmethod
    def run(cls, **kwargs):
        """Prints nice help."""
        print(cls.get_help(format_type=kwargs.get('format_type')))

    @classmethod
    def get_help(cls, format_type='ascii'):
        """Constructs and formats help for printing.

        Args:
            format_type: type of formatting for nice output, see format_text for possible values
        """
        # we will justify the action names (and assistant types) to the same width
        just = max(
            max(*map(lambda x: len(x), settings.ASSISTANT_ROLES)),
            max(*map(lambda x: len(x.name), actions.keys()))
        ) + 2
        text = ['You can either run assistants with:']
        text.append(cls.format_text('da [--debug] {crt,mod,prep,task} [ASSISTANT [ARGUMENTS]] ...',
                                    'bold',
                                    format_type))
        text.append('')
        text.append('Where:')
        text.append(cls.format_action_line('crt',
                                           'used for creating new projects',
                                           just,
                                           format_type))
        text.append(cls.format_action_line('mod',
                                           'used for working with existing projects',
                                           just,
                                           format_type))
        text.append(cls.format_action_line('prep',
                                           'used for preparing environment for upstream projects',
                                            just,
                                            format_type))
        text.append(cls.format_action_line('task',
                                           'used for performing custom tasks not related to a '
                                           'specific project',
                                            just,
                                            format_type))
        text.append('')
        text.append('Or you can run a custom action:')
        text.append(cls.format_text('da [--debug] [ACTION] [ARGUMENTS]',
                                    'bold',
                                    format_type))
        text.append('')
        text.append('Available actions:')
        for action in sorted(actions.keys(), key=lambda x: x.name):
            text.append(cls.format_action_line(action.name,
                                               action.description,
                                               just,
                                               format_type))
        return '\n'.join(text)

    @classmethod
    def format_text(cls, text, format, format_type):
        """Formats text to have given format in given format_type.

        Args:
            text: text to format
            format: format, e.g. 'bold'
            format_type: None (will do nothing) or 'ascii'
        Returns:
            formatted text
        """
        if format_type == 'ascii':
            if format == 'bold':
                text = '\033[1m' + text + '\033[0m'
        return text

    @classmethod
    def format_action_line(cls, action_name, action_desc, just, format_type):
        """Creates and formats action line from given action_name and action_desc.

        Args:
            action_name: name of action
            action_desc: description of action
            just: columns to justify action_name to
            format_type: formats action_name in bold using this format, see
                         format_text help for available format types
        Returns:
            formatted action line
        """
        text = []
        justed_name = action_name.ljust(just)
        text.append(cls.format_text(justed_name, 'bold', format_type))
        text.append(action_desc)
        return ''.join(text)


@register_action
class VersionAction(Action):
    """Prints DevAssistant version, what else?"""
    name = 'version'
    description = 'Print version'

    @classmethod
    def run(cls, **kwargs):
        from devassistant import __version__
        print('DevAssistant {version}'.format(version=__version__))
