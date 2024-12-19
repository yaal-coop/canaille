Theming
#######

Canaille comes with a default theme based on `Fomantic UI <https://fomantic-ui.com/>`__ but any part of the UI can be slightly modified or even entierely rewritten if needed.

Custom templates
================

To use a custom theme, set the :attr:`~canaille.core.configuration.CoreSettings.THEME` to a path to a directory where you will host your custom templates.

Then in this directory, create new files for templates you want to override. The exhaustive list of templates is available in the :doc:`reference <../references/templates>`.
You must respect the template file paths. So for instance if you want to customize the *about page*, you need to do it in a ``core/about.html`` file.
You can inherit from the origin template by using the Jinja ``extend`` directive.

.. code-block:: jinja
    :caption: core/about.html

    {% extends "core/about.html" %}
    {% import 'macro/form.html' as fui %}

    {% block content %}
        Your custom content goes here
    {% endblock %}

Custom style sheets
===================

If you simply want to put your custom style sheets in the default theme, you can just push it in the ``base.html`` template.
Put your file in a ``static`` subdirectory of your theme, for instance ``static/css/custom.css`` and reference it with ``theme_static``.

.. code-block:: jinja
    :caption: base.html

    {% extends "base.html" %}

    {% block style %}
        <link href="{{ theme_static("css/custom.css") }}" rel="stylesheet">
    {% endblock %}

Development
===========

To write your custom theme and check how it is rendered, you can put the path to your theme in a ``.env`` file and run the Canaille demo instance, as described in the :ref:`contributing guide <local_environment>`

.. code-block:: bash
   :caption: .env

    CANAILLE__THEME=/path/to/your/theme

.. code-block:: console
   :caption: Run the demo instance

   $ ./demo/run.sh
