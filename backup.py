import fmframework.io.csv as csvwrite
import fmframework.net.user as user

import sys, datetime, os

def backupScrobbles(path): 
    userobj = user.User('sarsoo')

    scrobbles = userobj.getRecentTracks()
    
    path = sys.argv[1]
    
    if not os.path.exists(path):
        os.makedirs(path)

    csvwrite.exportScrobbles(scrobbles, path)

if __name__ == '__main__':
    backupScrobbles(sys.argv[1])
