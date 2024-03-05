#!/bin/bash

# Run tests on application.
# Show coverage report if all tests pass.

# From the excellent Ned Batchelder
# https://coverage.readthedocs.io/

set -o nounset
set -o errexit
set +o xtrace


# Usage
if [ $# -ne 0 ]; then
    echo "Produce a coverage report for unit tests"
    echo "usage: $0"
    exit 1
fi


# Find coverage command in Debian/Ubuntu or Mac OS + MacPorts
if [ -x "$(command -v python3-coverage)" ]; then
    COVERAGE=python3-coverage
elif [ -x "$(command -v coverage-3.9)" ]; then
    COVERAGE=coverage-3.9
else
    echo "No Python coverage command found"
    exit 1
fi


# Run unit tests under the supervision of 'coverage.py'
$COVERAGE run --branch --module unittest --failfast --catch
$COVERAGE report --show-missing
rm -f .coverage
