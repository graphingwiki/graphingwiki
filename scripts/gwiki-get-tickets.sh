wget http://graphingwiki.python-hosting.com/report/1 -O report.html
mkdir -p ticket
perl -pi -e 's!/ticket/!./ticket/!' report.html 
grep /ticket/ report.html | cut -d '/' -f 3 | cut -d '"' -f 1 | sort | uniq | \
xargs -I {} wget http://graphingwiki.python-hosting.com/ticket/{} -O ticket/{}