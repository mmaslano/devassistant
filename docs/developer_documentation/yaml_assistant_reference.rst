.. _assistants in our Github repo: https://github.com/bkabrda/devassistant/tree/master/devassistant/assistants/assistants

.. _yaml_assistant_reference:

Yaml Assistant Reference
========================

This is a reference manual to writing yaml assistants, hopefully
up-to-date. For real examples, have a look at `assistants in our Github repo`_.
The basic rules apply to all assistants, but there are some special
rules for modifier assistants. And since either me or GitHub wiki is
stupid, I just can't make intra-page link without using the whole url,
which sucks. So find "Modifier Assistants" somewhere below.

Assistant Name
--------------

Assistant name is a short name used on command line, e.g. ``python``. It
should also be the only top-level yaml mapping in the file (that means
just one assistant per file). Each assistant should be placed in a file
that's named the same as the assistant itself (e.g. ``python`` assistant
in ``python.yaml`` file).

Assistant Content
-----------------

The top level mapping has to be mapping from assistant name to assistant
attributes, for example:

.. code:: yaml

   python:
     fullname: Python
     subassistants: [django, flask]
     # etc.

List of allowed attributes follows (attributes marked with ``?`` are
optional):

``fullname``
  a verbose name that will be displayed to user (``Python Assistant``)
``subassistants``
  list of names of subassistants of this assistant (``[django, flask]``)
``role``
  role of this assistant. ``creator`` (default) is an assistant used for creating projects from scratch,
  ``modifier`` is used for modifying existing projects, ``preparer`` is used for setting up environment
  for already existing projects (located e.g. at remote SCM etc.)
``description``
  a (verbose) description to show to user (``Bla bla create project bla bla``)
``dependencies`` (and ``dependencies_*``)
  specification of dependencies, see below `Dependencies`_
``args``
  specification of arguments, see below `Args`_
``files``
  specification of used files, see below `Files`_
``run`` (and ``run_*``)
  specification of actual operations, see below `Run`_

Dependencies
------------

Yaml assistants can express their dependencies in multiple sections.

- Packages from section ``dependencies`` are **always** installed.
- If there is a section named ``dependencies_foo``, then dependencies from this section are installed
  **iff** ``foo`` argument is used (either via commandline or via gui). For example:

.. code:: sh

   $ devassistant python --foo

- These rules differ for ``modifier`` assistants, see `Modifier Assistants`_

Each section contains a list of mappings ``dependency type: [list, of, deps]``.
If you provide more mappings like this: 

.. code:: yaml

   dependencies:
   - rpm: [foo]
   - rpm: ["@bar"]

they will be traversed and installed one by one. Supported dependency types: 

``rpm``
  the dependency list can contain RPM packages or YUM groups
  (groups must begin with ``@`` and be quoted, e.g. ``"@Group name"``)
``call``
  installs dependencies from snippet or other dependency section of this assistant. For example:

.. code:: yaml

   dependencies:
   - call: foo # will install dependencies from snippet "foo", section "dependencies"
   - call: foo.dependencies_bar # will install dependencies from snippet "foo", section "bar"
   - call: self.dependencies_baz # will install dependencies from section "dependencies_baz" of this assistant

``if``, ``else``
  conditional dependency installation. For more info on conditions, see "Run section"
  below `Run`_. For example:

.. code:: yaml

   dependencies:
   - if $foo:
     - rpm: [bar]
   - else:
     - rpm: [spam]

Full example: 

.. code:: yaml

   dependencies: - rpm: [foo, "@bar"]

   dependencies_spam:
   - rpm: [beans, eggs]
   - if $with_spam:
     - call: spam.spamspam
   - rpm: [ham]

Args
----

Arguments are used for specifying commandline arguments or gui inputs.
Every assistant can have zero to multiple arguments.

The ``args`` section of each yaml assistant is a mapping of arguments to
their attributes:

.. code:: yaml

   args:
     name:
       flags:
       - -n
       - --name
     help: Name of the project to create.
 
Available argument attributes:

``flags``
  specifies commandline flags to use for this argument. The longer flag
  (without the ``--``, e.g. ``name`` from ``--name``) will hold the specified
  commandline/gui value during ``run`` section, e.g. will be accessible as ``$name``.
``help``
  a help string
``required``
  one of ``{true,false}`` - is this argument required?
``nargs``
  how many parameters this argument accepts, one of ``{?,*,+}``
  (e.g. {0 or 1, 0 or more, 1 or more})
``default``
  a default value (this will cause the default value to be
  set even if the parameter wasn't used by user)
``action``
  one of ``{store_true, [default_iff_used, value]}`` - the ``store_true`` value
  will create a switch from the argument, so it won't accept any
  parameters; the ``[default_iff_used, value]`` will cause the argument to
  be set to default value ``value`` **iff** it was used without parameters
  (if it wasn't used, it won't be defined at all)
``snippet``
  name of the snippet to load this argument from; any other specified attributes
  will override those from the snippet By convention, some arguments
  should be common to all or most of the assistants.
  See :ref:`common_assistant_behaviour`

Files
-----

This section serves as a list of aliases of files stored in one of the
template dirs of devassistant. E.g. if the devassistant's template dir
contains file ``foo/bar``, then you can use:

.. code:: yaml

   files:
     bar: &bar
     source: foo/bar

This will allow you to reference the ``foo/bar`` file in ``run`` section as
``*bar`` without having to know where exactly it is located in your
installation of devassistant.

Run
---

Run sections are the essence of devassistant. They are responsible for
preforming all the tasks and actions to set up the environment and
the project itself. By default, section named ``run`` is invoked
(this is a bit different for ``modifier`` assistants `Modifier Assistants`_).
If there is a section named ``run_foo`` and ``foo`` argument is used,
then **only** ``run_foo`` is invoked. This is different from
dependencies sections, as the default ``dependencies`` section is used
every time.

Every ``run`` section is a sequence of various commands, mostly
invocations of commandline. Each command is a mapping
``command_type: command``. During the execution, you may use logging
(messages will be printed to terminal or gui) with following levels:
``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, ``CRITICAL``. By default,
messages of level ``INFO`` and higher are logged. As you can see below,
there is a separate ``log_*`` command type for logging, but some other
command types can also log various messages. Log messages with levels
``ERROR`` and ``CRITICAL`` terminate execution of devassistant imediatelly.

Run sections allow you to use variables with certain rules and
limitations. See below.

List of supported commands follows:

``cl``
  runs given command on commandline, aborts execution of the invoked assistant if it fails.
  **Note:** ``cd`` is a special cased command, which doesn't do shell expansion other than
  user home dir (``~``) expansion.
``cl_i``
  the ``i`` option makes the command execution be logged at ``INFO`` level
  (default is ``DEBUG``), therefore visible to user
``log_[diwec]``
  logs given message at level specified by the last letter in ``log_X``.
  If the level is ``e`` or ``c``, the execution of the assistant is interrupted immediately.
``dda_[c]``
  ``c`` creates ``.devassistant`` file (containing some sane initial meta
  information about the project) in given directory
``if``, ``else``
  conditional execution. The conditions can be:
  - ``$foo`` - evaluates to true **iff** ``$foo`` has value that evaluates to true
    (non-empty string, true)
  - commandline command - evaluates to true **iff** the command returns 0 exit code
    (doesn't interrupt the assistant execution if command fails); assigns both stdout
    and stderr lines in the order they were printed by command
  - not - negates the condition, can only be used once (no, you can't use
    ``not not not $foo, sorry``)
  - defined $foo - returns true **iff** ``foo`` variable is defined (meaning that
    it was set previously or `--foo` argument was used, even though its value may
    have been false or empty string)
``$foo``
  assigns either value of another variable or stdout of a given command to``$foo``
  (doesn't interrupt the assistant execution if command fails)
``call``
  run another section of this assistant (e.g.``call: self.run_foo``) of a snippet
  run section (``call: snippet_name.run_foo``) at this place and then continue execution
``dependencies_from_dda``
  let's you specify a directory where to read ``.devassistant`` file out of which
  dependencies are resolved and installed (devassistant will use dependencies
  from original assistant and specified  ``dependencies`` attribute, if any - this
  has the same structure as ``dependencies`` in normal assistants, but conditions
  are not supported)
``scl``
  run a whole section in SCL environment of one or more SCLs (note: you **must**
  use the scriptlet name - usually ``enable`` - because it might vary) - for example:

.. code:: yaml

   run:
   - scl enable python33 postgresql92:
     - cl_i: python --version
     - cl_i: pgsql --version

Variables
~~~~~~~~~

Initially, variables are populated with values of arguments from
commandline/gui and there are no other variables defined for creator
assistants. For modifier assistants global variables are prepopulated
with some values read from ``.devassistant``. You can either define
(and assign to) your own variables or change the values of current ones.

The variable scope works as follows:

- When invoking ``run`` section (from the current assistant or snippet),
  the variables get passed by value (e.g. they don't get modified for the
  remainder of this scope).
- As you would probably expect, variables that get modified in ``if`` and
  ``else`` sections are modified until the end of the current scope.

All variables are global in the sense that if you call a snippet or another
section, it can see all the arguments that are defined.

Quoting
~~~~~~~

When using variables that contain user input, they should always be
quoted in the places where they are used for bash execution. That
includes ``cl*`` commands, conditions that use bash return values and
variable assignment that uses bash.

Modifier Assistants
-------------------

Modifier assistants are assistants that are supposed to work with
already created project. They must have ``role`` attribute set to
``modifier``:

.. code:: yaml

   eclipse:
     role: modifier``

There are few special things about modifier assistants:

- They read the whole .devassistant file and make its contents available
  as any other variables (notably ``$subassistant_path``).
- They use dependency sections according to the normal rules + they use *all*
  the sections that are named according to current ``$subassistant_path``,
  e.g. if ``$subassistant_path`` is ``[foo, bar]``, dependency sections
  ``dependencies``, ``dependencies_foo`` and ``dependencies_foo_bar`` will
  be used as well as any sections that would get installed according to
  specified parameters.
- By default, they don't use ``run`` section. Assuming that ``$subassistant_path``
  is ``[foo, bar]``, they first try to find ``run_foo_bar``, then ``run_foo``
  and then just ``run``. The first found is used. If you however use cli/gui
  parameter ``spam`` and section ``run_spam`` is present, then this is run instead.

Preparer Assistants
-------------------

Preparer assistants are assistants that are supposed to checkout
existing projects from SCM and setting up the environment according to
``.devassistant``. Preparer assistants must have a ``role`` attribute
set to ``preparer``

.. code:: yaml

   custom:
     role: preparer

Preparer assistants commonly utilize the ``dependencies_from_dda``
command in ``run`` section.