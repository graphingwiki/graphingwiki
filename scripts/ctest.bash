#!/usr/bin/env bash

function fail {
    echo "$@" >&2

cat <<EOF
Usage:

 -p prog        shell command specifying program to be run and any arguments
 -i file        reference stdin file
 -o file        reference stdout/err file
 -f file1 file2 auxiliary file in a file system,
                file1 is reference and file2 is path where
                the program under test is expected to place its file
                (can be specified multiple times)
EOF
    exit 1
}

while [ $# -gt 0 ]; do
    case "$1" in
	-p)
	    prog="$2"
	    shift
	    ;;
	-o)
	    refout="$2"
	    shift
	    ;;
	-i)
	    refin="$2"
	    shift
	    ;;
	-f)
	    aux="$aux $2 $3"
	    shift; shift
	    ;;
    esac
    shift
done

[ -z "$prog" ] && fail "program must be specified using -p"
[ -z "$refout" ] && fail "reference stdin be specified using -i"
[ -z "$refin" ] && fail "reference stdin must be specified using -o"

pout=`mktemp /tmp/ctestXXXXXX`
(ulimit -t 15; ulimit -f 10000; $prog < $refin > $pout 2>&1)
pass=yes
if diff -wy $refout $pout; then
    echo stdout matches reference, good
else
    echo stdout differs, see above
    pass=no
fi

set -- $aux
while [ $# -gt 0 ]; do
    ref=$1
    f=$2
    shift; shift
    if diff -wy $ref $f; then
	echo file $f matches reference, good
    else
        echo file $f differs from reference, see above
	pass=no
    fi
done
if [ $pass = no ]; then
    echo "You shall not pass.. yet."
    exit 1
else
    echo "Test passed."
fi

