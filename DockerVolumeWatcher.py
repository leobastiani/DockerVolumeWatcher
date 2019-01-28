import os
import re
import sys
import sublime
import sublime_plugin
import glob
import socket

isPortOpen = None
def getIsPortOpen(port):
    global isPortOpen
    if isPortOpen is not None:
        return isPortOpen
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    if result == 0:
        sock.close()
        isPortOpen = True
    else:
        isPortOpen = False
    return isPortOpen

Settings = {}
DEBUG = False
def getSetting(name, default=None):
    if name in Settings:
        return Settings[name]
    view = sublime.active_window().active_view()
    ret = view.settings().get('DockerVolumeWatcher.'+name)
    if ret is not None:
        Settings[name] = ret
        return ret
    res = sublime.load_resource("Packages/User/DockerVolumeWatcher.sublime-settings")
    ret = sublime.decode_value(res).get(name, default)
    if ret is not None:
        Settings[name] = ret
        return ret
    ret = sublime.load_settings("DockerVolumeWatcher.sublime-settings").get(name, default)
    Settings[name] = ret
    return ret

def debug(*args):
    '''funciona como print, mas só é executada se sys.flags.debug == 1'''
    if not DEBUG:
        return ;
    print('DockerVolumeWatcher: ', end='')
    print(*args)

class LeoCodeIntelEventListener(sublime_plugin.EventListener):

    def on_post_save_async(self, view):
        global DEBUG, isPortOpen
        DEBUG = getSetting('debug', False)
        debug("DEBUG:", DEBUG)
        isEnabled = getSetting('enabled')
        debug("isEnabled:", isEnabled)
        if not getSetting('enabled'):
            return ;

        port = getSetting('port', 80)
        debug("port:", port)
        isPortOpen = None
        path_mappings = getSetting('path_mapping', {})
        debug("path_mappings:", path_mappings)
        if path_mappings:
                filePath = view.file_name().replace('\\', '/')
                for p in path_mappings:
                    name = p['name']
                    destPath = p['dest']
                    srcPath = p['src'].replace('\\', '/')
                    debug("name:", name)
                    debug("destPath:", destPath)
                    debug("srcPath:", srcPath)
                    debug("filePath:", filePath)
                    mustTouch = re.search('^'+srcPath, filePath)
                    debug("mustTouch:", mustTouch)
                    if mustTouch:
                        portOpen = getIsPortOpen(port)
                        debug("portOpen:", portOpen)
                        if portOpen:
                            # faz a troca
                            filePath = re.sub('^'+srcPath, destPath, filePath)
                            cmd = 'docker exec "'+name+'" touch "'+filePath+'"'
                            print("cmd:", cmd)
                            if not DEBUG:
                                view.window().run_command("exec", {
                                    'shell_cmd': cmd,
                                    'quiet': True,
                                })
                                # https://github.com/SublimeText/LaTeXTools/issues/566
                                view.window().run_command("hide_panel", {"panel": "output.exec"})
                        break
