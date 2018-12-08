====
Tips
====

To run a subset of tests::

$ py.test tests/test_radutil.py

helper scripts
--------------

* bump.sh
	- walks through bump/docs/commmit/push cycle
	- usage: bash bump.sh [patch/minor/major]
* flake8.sh
	- clears all existing flake8 marks
	- adds marks to all errors and prints to std out
	- open in textmate at use f3 to jump through errors
	- usage: bash flake8.sh path/to/script.py

setup
-----

* pip install -U cookiecutter
* cookiecutter https://github.com/audreyr/cookiecutter-pypackage.git
* cookiecutter cookiecutter-pypackage
* pip install -r requirements_dev.txt

**edit:**

* setup.py

	- requirements (list of imports)
	- setup['url']

* README.rst

	- description
	- installation
	- features

* docs/conf.py

	- html_theme_options = { 'page_width' : '1000px' }
	- extensions = [..., 'sphinx.ext.napoleon']
	- autodoc_member_order = 'bysource'


bumpversion
-----------

* clean directory (all changes committed) on master branch
* edit setup.cfg to add additional files with version tags
* bumpversion major/minor/patch setup.cfg (use --dry-run --verbose to test)

Command Sequence:

::

	bash bump.sh patch/minor/major

git stuff
---------

* git init
* git remote add origin https://stephenwasilewski@bitbucket.org/loisosubbelohde/clasp.git


* git pull origin master						pull master from remote
* git checkout master						switch to master branch
* git status
* push to remote:							git push origin master
* view commit history with branches:		git log --graph --oneline --all --decorate
* checkout single file from other branch:	git checkout codetest filter_points.py (repeat with base branch to revert)
* see what files have changed:				git diff --name-status master codetest
* pick a file that conflicts when merging:
	- git checkout --ours index.html (current branch)
	- git checkout --theirs _layouts/default.html (branch thats merging in)
	- then git add ...

Developer Install
-----------------

* pip install -e ./


Make
----

**make help:**

* clean                remove all build, test, coverage and Python artifacts
* clean-build          remove build artifacts
* clean-pyc            remove Python file artifacts
* clean-test           remove test and coverage artifacts
* lint                 check style with flake8
* test                 run tests quickly with the default Python
* test-all             run tests on every Python version with tox
* coverage             check code coverage quickly with the default Python
* docs                 generate Sphinx HTML documentation, including API docs
* servedocs            compile the docs watching for changes
* release              package and upload a release
* dist                 builds source and wheel package
* install              install the package to the active Python's site-packages

**not used / not working:**

* test-all
* servedocs
* release

directory files
---------------

**setup.cfg**

* bumpversion
* flake8
* pytest