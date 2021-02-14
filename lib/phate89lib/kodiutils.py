#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re
import sys
import traceback
from contextlib import contextmanager
from kodi_six import xbmc, xbmcaddon, xbmcplugin, xbmcgui, utils  # pyright: reportMissingImports=false
try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode
from . import staticutils
if sys.version_info < (2, 7):
    import simplejson as json
else:
    import json

ADDON = xbmcaddon.Addon()
ID = ADDON.getAddonInfo('id')
NAME = ADDON.getAddonInfo('name')
VERSION = ADDON.getAddonInfo('version')
PATH = ADDON.getAddonInfo('path')
DATA_PATH = ADDON.getAddonInfo('profile')
PATH_T = xbmc.translatePath(PATH)
DATA_PATH_T = xbmc.translatePath(DATA_PATH)
IMAGE_PATH_T = os.path.join(PATH_T, 'resources', 'media', "")
LANGUAGE = ADDON.getLocalizedString
KODILANGUAGE = xbmc.getLocalizedString
HANDLE = -1

if sys.argv and len(sys.argv)>1:
    try:
        HANDLE = int(sys.argv[1])
    except ValueError:
        pass

def executebuiltin(func, block=False):
    xbmc.executebuiltin(func, block)

def getMedia(asset=''):
    return os.path.join(PATH_T, 'resources', 'media', asset)

def notify(message='', header=NAME, time=4000, icon=''):
    message = 'Notification(%s,%s,%i,%s)' % (header, message, time, icon)
    xbmc.executebuiltin(message)

def log(msg, level=2):
    try:
        message = u'%s: %s' % (ID, msg)
        if level > 1:
            xbmc.log(msg=message, level=xbmc.LOGDEBUG)
        else:
            xbmc.log(msg=message, level=xbmc.LOGNOTICE)
            if level == 0:
                notify(msg)
    except Exception as ex:
        error = u'%s: %s' % (ID, createError(ex))
        xbmc.log(msg=error, level=xbmc.LOGDEBUG)
        pass

def createError(ex):
    template = (
        "EXCEPTION Thrown (PythonToCppException) : -->Python callback/script returned the following error<--\n"
        " - NOTE: IGNORING THIS CAN LEAD TO MEMORY LEAKS!\n"
        "Error Type: <type '{0}'>\n"
        "Error Contents: {1!r}\n"
        "{2}"
        "-->End of Python script error report<--"
    )
    return template.format(type(ex).__name__, ex.args, traceback.format_exc())


def py2_decode(s):
    return utils.py2_decode(s)


def py2_encode(s):
    return utils.py2_encode(s)


def getSetting(setting):
    return ADDON.getSetting(setting).strip()


def getSettingAsBool(setting):
    return getSetting(setting).lower() == "true"


def getSettingAsNum(setting):
    num = 0
    try:
        num = float(getSetting(setting))
    except ValueError:
        pass
    return num


def setSetting(setting, value):
    ADDON.setSetting(id=setting, value=str(value))

def openSettings():
    ADDON.openSettings()

def getKeyboard():
    return xbmc.Keyboard()


def getKeyboardText(heading, default='', hidden=False):
    kb = xbmc.Keyboard(default, heading)
    kb.setHiddenInput(hidden)
    kb.doModal()
    if (kb.isConfirmed()):
        return kb.getText()
    return False


def showOkDialog(heading, line):
    xbmcgui.Dialog().ok(heading, line)


def addListItem(label="", params=None, label2=None, thumb=None, fanart=None, poster=None, arts=None, videoInfo=None, properties=None, isFolder=True, menuItems=None):
    if arts is None:
        arts = {}
    if properties is None:
        properties = {}
    item = xbmcgui.ListItem(label, label2)
    if thumb:
        arts['thumb'] = thumb
    if fanart:
        arts['fanart'] = fanart
    if poster:
        arts['poster'] = poster
    if arts:
        item.setArt(arts)
    if videoInfo:
        item.setInfo('video', videoInfo)
    if isFolder:
        item.setIsFolder(True)
        properties['IsPlayable'] = 'false'
    else:
        item.setIsFolder(False)
        properties['IsPlayable'] = 'true'
    if isinstance(params, dict):
        url = staticutils.parameters(params)
    else:
        url = params
    if isinstance(properties, dict):
        for key, value in list(properties.items()):
            item.setProperty(key, value)
    if menuItems:
        item.addContextMenuItems(menuItems)
    return xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=item, isFolder=isFolder)


def setResolvedUrl(url="", solved=True, subs=None, headers=None, ins=None, insdata=None, properties=None):
    headerUrl = ""
    if headers:
        headerUrl = urlencode(headers)
    path = url + "|" + headerUrl
    item = xbmcgui.ListItem(path=path)
    if subs is not None:
        item.setSubtitles(subs)
    if ins:
        item.setProperty('inputstreamaddon', ins)
        if insdata:
            for key, value in list(insdata.items()):
                item.setProperty(ins + '.' + key, value)
    if properties and isinstance(properties, dict):
        for key, value in list(properties.items()):
            item.setProperty(key, value)
    xbmcplugin.setResolvedUrl(HANDLE, solved, item)
    if solved:
        log('item: {}'.format(str(item)), 4)
        properties['path'] = path
        kodiJsonRequest({'jsonrpc': '2.0', 'method': 'JSONRPC.NotifyAll', 'params': {'sender': ID, 'message': 'onAVStarted' , 'data': properties}, 'id': 1})
    sys.exit()


def append_subtitle(sUrl, subtitlename, sync=False, provider=None):
    #listitem = createListItem({'label': 'Italian', 'label2': subtitlename, 'thumbnailImage': 'it'})
    if not provider:
        tUrl = {'action': 'download', 'subid': sUrl}
    elif provider == 'ItalianSubs':
        p = re.search('subtitle_id=(?P<SUBID>[0-9]+)', sUrl, re.IGNORECASE)
        if not p:
            return False
        tUrl = "plugin://service.subtitles.itasa/?action=download&subid={subid}".format(
            subid=p.group('SUBID'))
    else:
        tUrl = {'action': 'download', 'url': sUrl}
    log("aggiungo il sottotitolo '" + subtitlename + "' alla lista", 3)
    return addListItem(label="Italian", label2=subtitlename, params=tUrl, thumb="it",
                       properties={"sync": 'true' if sync else 'false', "hearing_imp": "false"},
                       isFolder=False)


def setContent(ctype):
    if ctype:
        xbmcplugin.setContent(HANDLE, ctype)


def endScript(message=None, loglevel=2, closedir=True, update_listing=False, update_dir=False):
    if message:
        log(message, loglevel)
    if closedir:
        xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_DATE)
        xbmcplugin.endOfDirectory(handle=HANDLE, succeeded=True, updateListing=update_listing)
    if update_dir:
        refresh()
    sys.exit()


def createAddonFolder():
    if not os.path.isdir(DATA_PATH_T):
        log("Creating the addon data folder")
        os.makedirs(DATA_PATH_T)


def getShowID():
    json_query = xbmc.executeJSONRPC((
        '{"jsonrpc":"2.0","method":"Player.GetItem","params":'
        '{"playerid":1,"properties":["tvshowid"]},"id":1}'))
    jsn_player_item = json.loads(utils.py2_decode(json_query, 'utf-8', errors='ignore'))
    if 'result' in jsn_player_item and jsn_player_item['result']['item']['type'] == 'episode':
        json_query = xbmc.executeJSONRPC((
            '{"jsonrpc":"2.0","id":1,"method":"VideoLibrary.GetTVShowDetails","params":'
            '{"tvshowid":%s, "properties": ["imdbnumber"]}}') % (
                jsn_player_item['result']['item']['tvshowid']))
        jsn_ep_det = json.loads(utils.py2_decode(json_query, 'utf-8', errors='ignore'))
        if 'result' in jsn_ep_det and jsn_ep_det['result']['tvshowdetails']['imdbnumber'] != '':
            return str(jsn_ep_det['result']['tvshowdetails']['imdbnumber'])
    return False


def containsLanguage(strlang, langs):
    for lang in strlang.split(','):
        if xbmc.convertLanguage(lang, xbmc.ISO_639_2) in langs:
            return True
    return False


def isPlayingVideo():
    return xbmc.Player().isPlayingVideo()


def getInfoLabel(lbl):
    return xbmc.getInfoLabel(lbl)


def getRegion(r):
    return xbmc.getRegion(r)


def getEpisodeInfo():
    episode = {}
    episode['tvshow'] = staticutils.normalizeString(
        xbmc.getInfoLabel('VideoPlayer.TVshowtitle'))    # Show
    episode['season'] = xbmc.getInfoLabel(
        'VideoPlayer.Season')                            # Season
    episode['episode'] = xbmc.getInfoLabel(
        'VideoPlayer.Episode')                           # Episode
    file_original_path = xbmc.Player().getPlayingFile()  # Full path

    # Check if season is "Special"
    if str(episode['episode']).lower().find('s') > -1:
        episode['season'] = 0
        episode['episode'] = int(str(episode['episode'])[-1:])

    elif file_original_path.find('rar://') > -1:
        file_original_path = os.path.dirname(file_original_path[6:])

    elif file_original_path.find('stack://') > -1:
        file_original_path = file_original_path.split(' , ')[0][8:]

    episode['filename'] = os.path.splitext(os.path.basename(file_original_path))[0]

    return episode


def getFormattedDate(dt):
    fmt = getRegion('datelong')
    fmt = fmt.replace("%A", KODILANGUAGE(dt.weekday() + 11))
    fmt = fmt.replace("%B", KODILANGUAGE(dt.month + 20))
    return dt.strftime(py2_encode(fmt))

@contextmanager
def busy_dialog():
    showBusy()
    try:
        yield
    finally:
        closeBusy()

def showBusy():
    xbmc.executebuiltin('ActivateWindow(busydialognocancel)')

def closeBusy():
    xbmc.executebuiltin('Dialog.Close(busydialognocancel)')

def refresh():
    xbmc.executebuiltin('Container.Refresh()')

def kodiJsonRequest(params):
    result = None
    response = None
    try:
        data = json.dumps(params)
        request = xbmc.executeJSONRPC(data)
        response = json.loads(request)
        if 'result' in response:
            result = response['result']
    except KeyError:
        log("[%s] %s" % (params['method'], response['error']['message']))
    return result

if sys.argv and len(sys.argv)>2:
    log("Starting module '%s' version '%s' with command '%s'" % (NAME, VERSION, sys.argv[2]), 1)
