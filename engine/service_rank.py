"""Read GarlicSaves' official queue snapshot for jobs submitted by this instance."""
import json
import os
import re
import subprocess
import threading
import time


class QueueRanks:
    def __init__(self, client, cookie_file):
        self.client = client
        self.cookie_file = cookie_file
        self.lock = threading.Lock()
        self.cache = {}

    def snapshot(self, job_id):
        if (self.client.server not in ('https://garlicsaves.com', 'https://www.garlicsaves.com')
                or not isinstance(job_id, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', job_id)):
            return {}
        url = self.client.server + '/jobs/' + job_id + '/queue'
        result = {'queueUrl': url}
        if not isinstance(self.cookie_file, str) or not os.path.isfile(self.cookie_file):
            return result
        with self.lock:
            now = time.monotonic()
            self.cache = {k: v for k, v in self.cache.items() if now - v[0] < 120}
            item = self.cache.get(job_id)
            if item is None or now - item[0] >= 15:
                self.cache[job_id] = (now, {})
                threading.Thread(target=self._refresh, args=(job_id, url, now), daemon=True).start()
            else:
                result.update(item[1])
        return result

    def _refresh(self, job_id, url, stamp):
        args = [self.client.curl, '-q', '--silent', '--fail', '--max-time', '8',
                '--cookie', self.cookie_file, '--header', 'Accept: application/json']
        if self.client.proxy:
            args.extend(['--proxy', self.client.proxy])
        try:
            answer = subprocess.run(args + [url], capture_output=True, timeout=10, check=True,
                                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            data = json.loads(answer.stdout)
            pos, total = data['position'], data['total']
            if type(pos) is not int or type(total) is not int or not 0 <= pos <= total:
                return
        except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError):
            return
        with self.lock:
            if self.cache.get(job_id, (None,))[0] == stamp:
                self.cache[job_id] = (stamp, {'queuePosition': pos, 'queueTotal': total})
