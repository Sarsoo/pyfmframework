import fmframework.net.user as user

if __name__ == '__main__':
    print('hello world')

    sarsoo = user.User('sarsoo')
    
    tracks = sarsoo.getRecentTracks()
    print(len(tracks))

    for track in tracks:
        print(track['name'])
