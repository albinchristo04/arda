from lib.utils import *

SESSION = 'love'


class Love():
    def __init__(self, *args, **kwargs):
        params = kwargs['params']
        artist = xbmc.getInfoLabel('MusicPlayer.Artist')
        song   = xbmc.getInfoLabel('MusicPlayer.Title')
        action = params.get('action')
        # check if the skin provided valid params
        if artist and song and (action == 'LastFM.Love'):
            settings = read_settings(SESSION)
            sesskey  = settings['sesskey']
            confirm  = settings['confirm']
            # check if we have an artist name and song title
            if sesskey:
                self._submit_love(action, artist, song, confirm, sesskey)
            else:
                log('no sessionkey, artistname or songname provided', SESSION)

    def _submit_love(self, action, artist, song, confirm, sesskey):
        # love a track
        if action == 'LastFM.Love':
            action = 'track.love'
            # popup a confirmation dialog if specified by the skin
            if confirm:
                dialog = xbmcgui.Dialog()
                ack = dialog.yesno(LANGUAGE(32011), LANGUAGE(32012) + ' ' + artist + ' - ' + song)
                if not ack:
                    return
            # submit data to last.fm
            result = self._post_data(action, artist, song, sesskey)
            # notify user on success / fail
            if result:
                msg = 'Notification(%s,%s,%i)' % (LANGUAGE(32011), LANGUAGE(32014) % song, 7000)
            else:
                msg = 'Notification(%s,%s,%i)' % (LANGUAGE(32011), LANGUAGE(32015) % song, 7000)

    def _post_data(self, action, artist, song, sesskey):
        # love
        log('love submission', SESSION)
        # collect post data
        data = {}
        data['method'] = action
        data['artist'] = artist
        data['track'] = song
        data['sk'] = sesskey
        # connect to last.fm
        result = lastfm.post(data, SESSION)
        if not result:
            return False
        # parse response
        if 'status' in result:
            result = result['status']
            return True
        elif 'error' in result:
            code = result['error']
            msg = result['message'] 
            xbmc.executebuiltin('Notification(%s,%s,%i)' % (LANGUAGE(32011), msg, 7000))
            log('%s returned failed response: %s' % (action,msg), SESSION)
            # evaluate error response
            if code == 9:
                # inavlid SESSION key response, drop our key
                drop_sesskey()
        else:
            log('%s returned an unknown response' % action, SESSION)
        return False
