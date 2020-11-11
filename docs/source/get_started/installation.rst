.. _installation:

Installation
============

.. contents::

Installing PyCLibrary is straightforward. It is a pure python package and can
be installed using pip (NB : for the time being there is no PyPI package so you
must get a copy from github see using_dev_)::

	$ pip install pyclibrary

It has a single mandatory dependency : `pyparsing`_.

In order to run the testsuite you will also need py.test and if you want to
build the docs you will need sphinx (>1.3 current development version). All
those can be installed through pip using the following commands::

    $ pip install py.test
    $ pip install sphinx

.. _pyparsing: https://github.com/pyparsing/pyparsing/


Testing your installation
-------------------------

To test your installation open a python interpreter and import pyclibrary.

    >>> import pyclibrary

The last command will have no output if everything went well.

If you encounter any problem, take a look at the :ref:`faqs`. If everything
fails, feel free to open an issue in our `issue_tracker`_.

.. _issue_tracker: http://github.com/MatthieuDartiailh/pyclibrary/issues

.. _using_dev:

Using the development version
-----------------------------

You can install the development version directly from `Github`_::

    $ pip install https://github.com/MatthieuDartiailh/pyclibrary/zipball/master

.. _Github: http://github.com
