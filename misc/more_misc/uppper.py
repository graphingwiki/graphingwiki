import couchdb
import shelve
import json

couch = couchdb.Server()


gdata = shelve.open('graphdata.shelve')
dbname = 'gwikidata'


try:
    db = couch[dbname]
except couchdb.http.ResourceNotFound:
    db = couch.create(dbname)


for page, pagedata in gdata.items():
    #print page

    # for link, values in pagedata['out'].items():
    #     print "+ ", link, values
    # print '...'
    # for key, values in pagedata['meta'].items():
    #     print "* ", key, values

    db.save({'_id': page, 'meta': pagedata.get('meta', {}), 'out': pagedata.get('out', {})})



