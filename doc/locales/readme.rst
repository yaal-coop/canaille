Translations are done with `Weblate <https://hosted.weblate.org/projects/canaille/documentation>`__.

The following commands are there as documentation, only the message extraction and the language addition is needed for contributors.

Message extraction
~~~~~~~~~~~~~~~~~~

After you have edited translatable strings, you should extract the messages with:

.. code-block:: bash

    sphinx-build --builder gettext doc doc/locales

Language addition
~~~~~~~~~~~~~~~~~

You can add a new language manually with the following command, however this should not be needed as Weblate takes car of this:

.. code-block:: bash

    sphinx-intl update --pot-dir doc/locales --locale-dir doc/locales -l fr

Build the documentation in another language
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    sphinx-build --builder html --define language=fr doc build/sphinx/html/fr
