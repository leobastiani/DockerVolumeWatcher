import re
import sublime
import sublime_plugin
import json
import subprocess

openedContainers = None
def getOpenedContainers():
    global openedContainers
    if openedContainers is not None:
        return openedContainers
    lines = check_output(r'docker ps -q --format "{{.Names}}"')
    # remove os espaços em branco
    lines = [x for x in re.split(r'[\n\r]+', lines) if x]
    openedContainers = lines
    return openedContainers

volumes = None
def getVolumes():
    global volumes
    if volumes is not None:
        return volumes
    openedContainers = getOpenedContainers()
    if openedContainers:
        volumes = []
    for c in openedContainers:
        res = json.loads(check_output(r'docker inspect --format "{{json .Mounts}}" '+c))
        for d in res:
            d['container'] = c
        volumes += res
    return volumes

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
    try:
        res = sublime.load_resource("Packages/User/DockerVolumeWatcher.sublime-settings")
        ret = sublime.decode_value(res).get(name, default)
        if ret is not None:
            Settings[name] = ret
            return ret
    except IOError:
        pass
    ret = sublime.load_settings("DockerVolumeWatcher.sublime-settings").get(name, default)
    Settings[name] = ret
    return ret

def debug(*args):
    if not DEBUG:
        return ;
    print('DockerVolumeWatcher: ', end='')
    print(*args)

# https://github.com/davidolrik/sublime-rsync-ssh/blob/master/rsync_ssh.py#L34
def check_output(*args, **kwargs):
    """Runs specified system command using subprocess.check_output()"""
    startupinfo = None
    if sublime.platform() == "windows":
        # Don't let console window pop-up on Windows.
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

    try:
        debug("check_output_args:", args)
        ret = subprocess.check_output(*args, universal_newlines=True, startupinfo=startupinfo, **kwargs)
        debug("check_output_ret:", ret)
        return ret
    except Exception as e:
        global Settings
        Settings['enabled'] = False
        raise e


class DockerVolumeWatcherEventListener(sublime_plugin.EventListener):

    def on_post_save_async(self, view):
        global DEBUG
        DEBUG = getSetting('debug', False)
        debug("DEBUG:", DEBUG)
        isEnabled = getSetting('enabled')
        debug("isEnabled:", isEnabled)
        if not getSetting('enabled'):
            return ;

        volumes = getVolumes()
        debug("volumes:", volumes)
        if volumes:
            # troca C:\ por C:/
            filePath = view.file_name().replace('\\', '/')
            # troca C:/ por /c/
            filePath = re.sub(
                r'^([\w]):/',
                lambda x: '/%s/' % x.group(1).lower(),
                filePath
            )
            for v in volumes:
                container = v['container']
                destPath = v['Destination']
                srcPath = v['Source']
                debug("container:", container)
                debug("destPath:", destPath)
                debug("srcPath:", srcPath)
                debug("filePath:", filePath)
                mustTouch = re.search('^'+srcPath, filePath)
                debug("mustTouch:", mustTouch)
                if mustTouch:
                    # faz a troca
                    filePath = re.sub('^'+srcPath, destPath, filePath)
                    cmd = 'docker exec "'+container+'" chmod 777 "'+filePath+'"'
                    print("cmd:", cmd)
                    if not DEBUG:
                        check_output(cmd)
