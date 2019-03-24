import os
import requests

class User:

    def __init__(self, username, pagesize = 200):
        self.api_key = os.environ['FMKEY']
        
        self.username = username
        self.pagesize = pagesize

    def __makeRequest(self, method, extra = {}, page = 1):
       
        data = {
                "format": 'json',
                "method": method,
                "limit": self.pagesize,
                "page": page,
                "user": self.username,
                "api_key":  self.api_key
                }
        data.update(extra)

        req = requests.get('http://ws.audioscrobbler.com/2.0/', params = data)
    
        if req.status_code < 200 or req.status_code > 299:
            
            if req.json()['error'] == 8:
                print('ERROR: retrying call ' + method)
                return __makeRequest(method, extra, page)
            else:
                raise ValueError('HTTP Error Raised: ' + str(req.json()['error']) + ' ' + req.json()['message'])

        return req.json()

    def getRecentTracks(self, offset = 1, pagelimit = 0):
        
        scrobbles = []

        print(str(offset) + ' offset')
        
        json = self.__makeRequest('user.getrecenttracks', page = offset)
        scrobbles += json['recenttracks']['track']
        
        if pagelimit > 0:
            if offset < pagelimit and offset < int(json['recenttracks']['@attr']['totalPages']):
                scrobbles += self.getRecentTracks(offset = offset + 1, pagelimit = pagelimit)
        else:
            if offset < int(json['recenttracks']['@attr']['totalPages']):
                scrobbles += self.getRecentTracks(offset = offset + 1, pagelimit = pagelimit)

        return scrobbles
