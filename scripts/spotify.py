from tqdm import tqdm
import requests, webbrowser, urllib.parse, json


def Authorize(client_id):
    scopes = 'playlist-modify-private%20playlist-modify-public%20playlist-read-private'
    redirect_url = urllib.parse.quote_plus('http://example.com/callback/')

    requestURL = 'https://accounts.spotify.com/authorize?client_id={0}&response_type=token&redirect_uri={1}&scope={2}'.format(client_id, redirect_url, scopes)
    
    webbrowser.open(requestURL, new=1)

    print('Пожалуйста, разрешите приложению вносить изменения в Ваши плейлисты в открывшемся окне браузера.')
    print('После подтверждения, пожалуйста, скопируйте и вставьте ссылку в консоль.')

    responseURL = input()
    params = responseURL.split('#')[1].split('&')

    response = {}
    for i in params:
        x = i.split('=')
        response.update({x[0]: x[1]})

    return response['access_token']
    

def SearchTrack(searchname, access_token):
    headers = {
        'Authorization': 'Bearer {}'.format(access_token),
        'Content-Type' : 'application/x-www-form-urlencoded'
    }
    requestURL = 'https://api.spotify.com/v1/search?type=track&q={}&limit=1'.format(urllib.parse.quote_plus(searchname))
    response = requests.get(requestURL, headers=headers)
    data = json.loads(response.content.decode('utf-8'))
    try:       
        result = data['tracks']['items'][0]['id']
        return result
    except Exception:
        return 0


def CreateJsonIds(path, access_token):
    with open(path, 'r', encoding='utf-8') as file:
        data = json.load(file)
        k = len(data)
        tracksNotFoundInSpotify = []
        countOfNotFoundTracks = 0
        countOfFoundTracks = 0
        print('Создаются ID треков в Spotify, пожалуйста, подождите.')
        with tqdm(total=k) as pbar:
            for item in data:              
                searchname = ''
                if item['IsPlaylist']:
                    for track in item['Tracks']:
                        searchname = item['Artist'] + ' ' + track['Title']
                        trackID = SearchTrack(searchname, access_token)
                        if trackID != 0:
                            countOfFoundTracks += 1
                            track['Id'] = trackID
                        else:
                            countOfNotFoundTracks += 1                           
                            tracksNotFoundInSpotify.append({
                                'Title' : track['Title'],
                                'Artist' : item['Artist']
                            })
                else:
                    searchname = item['Artist'] + ' ' + item['Title']
                    trackID = SearchTrack(searchname, access_token)
                    if trackID != 0:
                        countOfFoundTracks += 1
                        item['Id'] = trackID
                    else:
                        countOfNotFoundTracks += 1
                        tracksNotFoundInSpotify.append({
                            'Title' : item['Title'],
                            'Artist' : item['Artist']
                        })
                k -= 1
                pbar.set_description('Осталось {0} элементов (плейлистов/треков)'.format(k))
                pbar.update(1)
            countOfFoundTracksInPercent = '{0:.0f}%'.format(countOfFoundTracks/(countOfNotFoundTracks + countOfFoundTracks) * 100)
            tracksNotFoundInSpotify.append({
                "countOfFoundTracksInPercent" : countOfFoundTracksInPercent
            })
            file.close()
    with open('parsed/tracksNotFoundInSpotify.json', 'w', encoding='utf-8') as newfile:
        json.dump(tracksNotFoundInSpotify, newfile, ensure_ascii=False, indent=4)
        newfile.close()
    with open(path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)
        file.close()
                

def CreatePlaylistSpotify(name, access_token):
    with open('config.json', 'r', encoding='utf-8') as file:
        userID = json.load(file)['spotifyid']
        file.close()
        
    headers = {
        'Authorization': 'Bearer {}'.format(access_token),
        'Content-Type' : 'application/json'
    }
    data = {
        'name' : name,
        'public' : False
    }
    requestURL = 'https://api.spotify.com/v1/users/{0}/playlists'.format(userID)
    response = requests.post(requestURL, headers=headers, data=json.dumps(data))
    responseData = json.loads(response.content.decode('utf-8'))
    
    return responseData['id']


def AddTrackToPlaylist(playlistID, trackID, access_token):
    if trackID != '':
        headers = {
            'Authorization': 'Bearer {}'.format(access_token),
            'Content-Type' : 'application/json'
        }
        data = {
            'uris': ['spotify:track:{}'.format(trackID)]
        }

        requestURL = 'https://api.spotify.com/v1/playlists/{0}/tracks'.format(playlistID)
        requests.post(requestURL, headers=headers, data=json.dumps(data))  


def TransferTracks(path, access_token):
    with open(path, 'r', encoding='utf-8') as file:
        data = json.load(file)

        with open('config.json', 'r', encoding='utf-8') as cfg:
            defaultPlaylistName = json.load(cfg)['DefaultPlaylistName']
        cfg.close()
        k = len(data)
        basePlaylistId = CreatePlaylistSpotify(defaultPlaylistName, access_token)

        print('Добавляем плейлисты/треки в Spotify.')

        with tqdm(total=k) as pbar:
            for item in data:
                if item['IsPlaylist']:
                    playlistId = CreatePlaylistSpotify(item['Artist'], access_token)
                    for track in item['Tracks']:
                        AddTrackToPlaylist(playlistId, track['Id'], access_token)
                    item['Id'] = playlistId
                else:
                    AddTrackToPlaylist(basePlaylistId, item['Id'], access_token)
                k -= 1
                pbar.set_description('Осталось {0} элементов (плейлистов/треков)'.format(k))
                pbar.update(1)
            file.close()

    with open(path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)
        file.close()


def main(path, client_id):
    access_token = Authorize(client_id)
    CreateJsonIds(path, access_token)
    TransferTracks(path, access_token)