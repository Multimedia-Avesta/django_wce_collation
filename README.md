# The Collation app

This Django app forms part of the MUYA Workspace for Collaborative Editing (MUYA-WCE).

This app is the wrapper for the collation editor code (https://github.com/itsee-birmingham/collation_editor_core) which
is included as a submodule. It links the collation editor to the database and also provides all of the apparatus and
provides many additional functions including:

- editorial text selection
- apparatus exports
- export of data from transcriptions (eg. notes and ritual directions)
- project management functions such as setting the project transcriptions, ceremony mappings and supplement ranges


## Configuration/Dependencies

This app is tested with Django 3.2.

It requires the MUYA-WCE api (https://github.com/Multimedia-Avesta/django_wce_api), accounts
(https://github.com/Multimedia-Avesta/django_wce_accounts) and transcriptions
https://github.com/Multimedia-Avesta/django_wce_transcriptions apps to be installed.

It also requires a JavaScript file to be added to the ```common-static/js``` directory in the main Django project with
the file name ```static_url.js```. This file should set the staticUrl variable to the full url to the static directory
for example:

```js
const staticUrl = 'https://example.com/static/';
```

A Java version of CollateX is included in the repository, other version can be access from the website
(https://collatex.net/). It can be run locally for testing using the management command ```runcollatex```. In
production it should be run as a service/daemon.

The app requires Celery (https://docs.celeryproject.org/en/stable/) and a message broker such as RabbitMQ
(https://www.rabbitmq.com/) for handling the long running task of generating the apparatus and other outputs. It has
been tested with Celery 5.1.2.

A celery result backend is also required such as django-celery-results
(https://github.com/celery/django-celery-results). It has been tested with django-celery-results 2.2.0.

lxml (https://lxml.de/) is required to build the apparatus and other output formats. The app has been tested with lxml
4.6.3.

Celery and RabbitMQ require some configuration in the Django settings file as shown in the following example:

```python
CELERY_BROKER_URL = 'amqp://me:example@localhost'
CELERY_RESULT_BACKEND = 'django-db'
```

The following two directories must be configured in the Django settings to store the generated outputs before download.
The directories can be anywhere on the system and do not need to match the example. The directories must be created on
the server and have the appropriate permissions set so that the webserver user can write to the directories.

```python
APPARATUS_BASE_DIR = BASE_DIR / 'apparatus'
EXPORT_BASE_DIR = BASE_DIR / 'exports'
```

## License

This app is licensed under the GNU General Public License v3.0.

## Acknowledgments

This application was released as part of the Multimedia Yasna Project funded by the European Union Horizon 2020
Research and Innovation Programme (grant agreement 694612).

The software was created by Catherine Smith at the Institute for Textual Scholarship and Electronic Editing (ITSEE) in
the University of Birmingham. It is based on a suite of tools developed for and supported by the following research
projects:

- The Workspace for Collaborative Editing (AHRC/DFG collaborative project 2010-2013)
- COMPAUL (funded by the European Union 7th Framework Programme under grant agreement 283302, 2011-2016)
- CATENA (funded by the European Union Horizon 2020 Research and Innovation Programme under grant agreement 770816, 2018-2023)

[![DOI](https://zenodo.org/badge/431917309.svg)](https://zenodo.org/badge/latestdoi/431917309)
