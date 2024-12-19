Templates
#########

This references the template files, their role and the variables available in their contexts.
The intended audience for this reference is designers wishing to build their custom Canaille theme.

Base
====

Those templates are shared by all the pages rendered by Canaille.

Template files
--------------

.. autotemplate:: base.html

.. autotemplate:: error.html

.. autotemplate:: macro

Forms
-----

.. autoclass:: canaille.app.forms.TableForm
    :members:
    :show-inheritance:
    :undoc-members:

Core
====

The core templates are displayed in the authentication and profile edition pages.

Template files
--------------

.. autotemplate:: core

Forms
-----

.. automodule:: canaille.core.endpoints.forms
    :members:
    :show-inheritance:
    :undoc-members:

OIDC
====

The OIDC templates are displayed in the OIDC consent pages.

Template files
--------------

.. autotemplate:: oidc/

Forms
-----

.. automodule:: canaille.oidc.endpoints.forms
    :members:
    :show-inheritance:
    :undoc-members:
