Troubleshooting
###############

The web interface throws unuseful error messages
================================================

Unless the current user has admin :class:`permissions <canaille.core.configuration.Permission>`, or the installation is in :attr:`~canaille.app.configuration.RootSettings.DEBUG` mode, error messages won't be too technical.
For instance, you can see *The request you made is invalid*.
To enable detailed error messages, you can **temporarily** enable the :attr:`~canaille.app.configuration.RootSettings.DEBUG` configuration parameter.
