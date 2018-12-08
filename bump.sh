#!/bin/bash
clean=$(git status --porcelain --untracked-files=no | wc -l)
if [ \( $# -eq 1 \) -a \( $clean -lt 1 \) ]
then
	eval "$(bumpversion --list "$1")"

	echo 'Bump version: '"$current_version"' → '"$new_version"''

	read -p "proceed to build docs? " -n 1 -r
	echo    # (optional) move to a new line
	if [[ $REPLY =~ ^[Yy]$ ]]
	then
		mate -w history.rst
		make docs
		git add ru_docs/
	fi

	read -p "proceed with commit? " -n 1 -r
	echo    # (optional) move to a new line
	if [[ $REPLY =~ ^[Yy]$ ]]
	then
		git commit -a -m 'Bump version: '"$current_version"' → '"$new_version"''
		git tag v$new_version
		git push --tags
		git checkout master
		git merge develop
		git checkout develop
		git push origin master
		git push origin develop
	fi

	git log --graph --oneline --all --decorate

	echo 'Bump version: '"$current_version"' → '"$new_version"''
else
	echo usage: ./bump.sh [patch/minor/major]
fi