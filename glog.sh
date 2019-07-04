#!/bin/bash
# git log --graph --oneline --all --decorate

git log --graph --all --date=short --pretty=format:"%C(auto)%h%C(auto)%d%n%Cred%ad: %Creset%s"