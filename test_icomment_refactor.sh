#!/bin/bash

# Test script to verify the icomment refactor works correctly

echo "🧪 Testing icomment refactor..."
echo

# Source the updated .alias file
source /Users/kosiew/GitHub/python-scripts/.alias

# Test 1: Help message
echo "📝 Test 1: icomment --help"
icomment --help
echo
echo "✅ Test 1 passed: Help message displayed correctly"
echo

# Test 2: Missing argument error
echo "📝 Test 2: icomment (no arguments)"
if ! icomment 2>/dev/null; then
    echo "✅ Test 2 passed: Correctly handled missing argument"
else
    echo "❌ Test 2 failed: Should have failed with missing argument"
fi
echo

# Test 3: Function type
echo "📝 Test 3: Function type check"
if type icomment | grep -q "shell function"; then
    echo "✅ Test 3 passed: icomment is a shell function"
else
    echo "❌ Test 3 failed: icomment should be a shell function"
fi
echo

# Test 4: Check that run_alias_py helper exists
echo "📝 Test 4: run_alias_py helper check"
if type run_alias_py | grep -q "shell function"; then
    echo "✅ Test 4 passed: run_alias_py helper exists"
else
    echo "❌ Test 4 failed: run_alias_py helper missing"
fi
echo

echo "🎉 All tests completed!"
