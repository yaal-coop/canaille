Translations are done with [weblate](https://hosted.weblate.org/projects/canaille/canaille/).
Those commands are there as documentation, only the message extraction is needed for contributors.
All the other steps are automatically done with Weblate.

Extract the messages with:

```
pybabel extract --mapping-file canaille/translations/babel.cfg --copyright-holder="Yaal Coop" --output-file canaille/translations/messages.pot canaille
```

Add a new language with:

```
pybabel init --input-file canaille/translations/messages.pot --output-dir canaille/translations --locale <LANG>
```

Update the catalogs with:

```
pybabel update --input-file canaille/translations/messages.pot --output-dir canaille/translations --ignore-obsolete --no-fuzzy-matching --update-header-comment
```

Compile the catalogs with:

```
pybabel compile --directory canaille/translations --statistics
```
