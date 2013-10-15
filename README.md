[This repository has moved; click here.](http://github.com/CenterForOpenScience/openscienceframework/)
===========================

Quickstart
==========

These instructions should work on Mac OSX >= 10.7

- Create your virtualenv.
- Install MongoDB. On MacOSX with [homebrew](http://brew.sh/) (click link for homebrew installation instructions), run:

```bash
$ brew update 
$ brew install mongodb
```

- Install libxml2 and libxslt (required for installing lxml).

```bash
$ brew install libxml2
$ brew install libxslt
```

- Install requirements.

```bash
$ pip install -r dev-requirements.txt
```

- Create your local settings file.

```bash
$ cp website/settings/local-dist.py website/settings/local.py
```

`local.py` will override settings in `base.py`. It will not be added to source control.

- Run your mongodb process.

```bash
$ invoke mongo
```

- Run your local development server.

```bash
$ invoke server
```

Running Tests
=============

To run all tests:

```bash
$ nosetests tests/
```

To run a certain test method

```bash
$ nosetests tests/test_module.py:TestClass.test_method
```
