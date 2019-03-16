import fmframework.io.csv as csvwrite
import fmframework.net.user as user

import sys, datetime, os

def backupScrobbles(): 
    userobj = user.User('sarsoo')

    scrobbles = userobj.getRecentTracks(pagelimit = 2)
    
    path = sys.argv[1]
    
    datepath = str(datetime.datetime.now()).split(' ')[0].replace('-', '/')

    totalpath = os.path.join(path, datepath)
    pathdir = os.path.dirname(totalpath)
    if not os.path.exists(totalpath):
        os.makedirs(totalpath)

    csvwrite.exportScrobbles(scrobbles)

if __name__ == '__main__':
    backupScrobbles()
