Translations are done with `Weblate <https://hosted.weblate.org/projects/canaille/canaille>`__.

The following commands are there as documentation, only the message extraction is needed for contributors.
All the other steps are automatically done with Weblate.


Message extraction
~~~~~~~~~~~~~~~~~~

After you have edited translatable strings, you should extract the messages with:

.. code-block:: bash

    pybabel extract --mapping-file pyproject.toml --copyright-holder="Yaal Coop" --output-file canaille/translations/messages.pot canaille

Language addition
~~~~~~~~~~~~~~~~~

You can add a new language manually with the following command, however this should not be needed as Weblate takes car of this:

.. code-block:: bash

    pybabel init --input-file canaille/translations/messages.pot --output-dir canaille/translations --locale <LANG>

Catalog update
~~~~~~~~~~~~~~

You can update the catalogs with the following command, however this should not be needed as Weblate automatically update language catalogs when it detects new strings or when someone translate some existing strings.
Weblate pushes happen every 24h.

.. code-block:: bash

    pybabel update --input-file canaille/translations/messages.pot --output-dir canaille/translations --ignore-obsolete --no-fuzzy-matching --update-header-comment

Catalog compilation
~~~~~~~~~~~~~~~~~~~

You can compile the catalogs with the following command, however this should not be needed as catalogs are automatically compiled before running the unit tests, before launching the demo and before compiling the Canaille python package:

.. code-block:: bash

    pybabel compile --directory canaille/translations --statistics
