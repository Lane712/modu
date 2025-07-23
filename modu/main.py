
import requests
from fake_useragent import UserAgent
    
import ddddocr

from bs4 import BeautifulSoup
from urllib.parse import unquote, urlparse

import shutil
import time
import os,re,json,m3u8
from tqdm import tqdm
from pathlib import Path
from datetime import date

from queue import Queue
from threading import Event, Lock, Thread
from concurrent.futures import ThreadPoolExecutor, as_completed

from pymongo import MongoClient
from pymongo.collection import Collection

from modu.logger import log, Logger
from modu.utils import modify_m3u8_file

from typing import Literal

class ModuConfig:

    _redirect = 'https://www.moduzy.vip'
    _root = 'https://www.moduzy.cc'

    TAG = Literal[1,2,3,4,5,6,7,8,9]
    # 国产动漫 1
    # 日韩动漫 2
    # 欧美动漫 3
    # 港台动漫 4
    # 动漫电影 5
    # 里番 6
    # 电影 7
    # 连续剧 8
    # 综艺 9
    
    @classmethod
    def update_root_url(cls):
        """Get the latest root url"""
        res = requests.get(cls._redirect)
        res.raise_for_status()
        match = re.search(r'<span> <span>魔都资源：</span> <a href="(https?:.*)" target="_blank" class="home_a">',res.text)
        url = match.group(1)
        if url:
            cls._root = url
            print("Changed Root:", cls._root)
        return cls._root

    # TODO:
    # 数据文件为json文件夹，1.获取/ 当前目录、软件目录、根目录 2.读取  3.不存在创建，存在就更新
    # 配置文件类似，不存在使用默认配置，或者提示创建

SLog = Logger(name="moduscraper", filename="ScrapeLog.log")

class ModuScraper:
    _ua = UserAgent(os=["Windows","Android"])
    _session = requests.Session()
    _session.headers['User-Agent'] = _ua.random
    _ocr = None
    _root = ModuConfig._root

    def __init__(
            self,
            ua_os: list[str] = ...
        ):
        self.ua = UserAgent(os=ua_os if (ua_os is not Ellipsis) else self.__class__._ua.os)
        self.session = requests.Session()
        self.session.headers['User-Agent'] = self.ua.random
        self.ocr = None
        self.root = self.__class__._root

    def verify_search_cookie(self):
        """Verify to use search function"""
        res = self.session.get(self.root)
        print(res.headers, self.session.cookies.items())
        r1 = self.session.get(self.root + "/index.php/verify/index.html")
        r1.raise_for_status()
        if self.ocr is None:
            self.ocr = ddddocr.DdddOcr()
            print("Create ddddcor.DdddOcr's Object")
        result = self.ocr.classification(r1.content)
        print("验证码识别结果：", result)
        r2 = self.session.get(self.root + f"/index.php/ajax/verify_check?type=search&verify={result}")
        print(r2.text)
        if r2.json()['msg'] == "ok":
            return self.session.cookies.items()

    @classmethod
    def verify_search_cookie(cls):
        """Verify to use search function"""
        res = cls._session.get(cls._root)
        print(res.headers, cls._session.cookies.items())
        r1 = cls._session.get(cls._root + "/index.php/verify/index.html")
        r1.raise_for_status()
        if cls._ocr is None:
            cls._ocr = ddddocr.DdddOcr()
        result = cls._ocr.classification(r1.content)
        print("验证码识别结果：", result)
        r2 = cls._session.get(cls._root + f"/index.php/ajax/verify_check?type=search&verify={result}")
        print(r2.text)
        if r2.json()['msg'] == "ok":
            return cls._session.cookies.items()
        
    def search(self, kwd: str):
        """Search by **kwd**. Return **list[** {title, status, updated, url} **]**"""
        search_url = self.root + f"/search/-------------/?wd={kwd}&submit="
        res = self.session.get(search_url)
        res.raise_for_status()
        if res.headers.get("Set-Cookie"):
            self.verify_search_cookie()
            return self.session.cookies.items()
        return self._get_vod_list(res.text)
    
    @classmethod
    def search(cls, kwd: str):
        """Search by **kwd**. Return **list[** {title, status, updated, url} **]**"""
        search_url = cls._root + f"/search/-------------/?wd={kwd}&submit="
        res = cls._session.get(search_url)
        res.raise_for_status()
        if res.headers.get("Set-Cookie"):
            cls.verify_search_cookie()
            return cls._session.cookies.items()
        return cls._get_vod_list(res.text)

    @staticmethod
    def _get_vod_list(html: str):
        soup = BeautifulSoup(html, "html.parser")
        tbody = soup.find("tbody")
        if tbody is None:
            return []
        
        vod_list = []
        trs = tbody.find_all("tr")
        for tr in trs:
            td1 = tr.find("td")
            title = td1.find("a").string
            url = ModuConfig._root + td1.find("a").get("href")
            status = td1.find("small").string
            updated = tr.find_all("td")[2].string
            vod_list.append({
                "title": title,
                "status": status,
                "updated": updated,
                "url": url
            })
        return vod_list
    
    @staticmethod
    def _get_vod_data(html: str):
        """### *Return*
        > a ***dict*** container **details** about this video.
        """
        soup = BeautifulSoup(html, "html.parser")
        img = soup.find("p", attrs={'class': 'thumb'}).find('img',src=True)
        title = img.get('alt')
        imgsrc = img.get('src')

        details = {}
        ps = soup.find("div",attrs={'class':"content__detail"}).find_all("p", attrs={"class":"mb-2"})
        for p in ps:
            match = re.split(r"：", p.text, maxsplit=1)
            details[match[0]] = match[1]

        titles = []
        genres = []
        directors = []
        actors = []
        aired = ""
        region = ""
        updated = ""
        
        for key, val in details.items():
            if key == "又名":
                titles = re.split(r"[\W]+", val, flags=re.U)
            elif key == "导演":
                directors = val.split(",")
            elif key == "主演":
                actors = val.split(",")
            elif key == "类型":
                genres = val.split(",")
            elif key == "年份":
                if val == "未知":
                    aired = 0
                else:
                    aired = int(val)
            elif key == "地区":
                region = val
            elif key == "更新时间":
                updated = val

        playlists = []
        lists = soup.find('ul', attrs={'class': 'content__playlist'}).find_all('li')
        for li in lists:
            playlist = li.find('a').string
            playlists.append(playlist)

        status = re.search(r'<small class="text-red h5">(.*)</small>', html).group(1)

        return {
            'title': title,
            "titles": titles,
            'region': region,
            'aired':aired,
            'status': status,
            "updated": updated,
            'genres': genres,
            'directors': directors,
            'actors': actors,
            'imgsrc': imgsrc,
            'playlists': playlists
        }

    def scraper_worker(self, url_queue: Queue, col: Collection):
        error_urls = []
        user_agent = self.ua.random
        while not url_queue.empty():
            url = url_queue.get()
            try:
                res = requests.get(url, timeout=20, headers={"User-Agent": user_agent})
                res.raise_for_status()
                data = self._get_vod_data(res.text)
                data['id'] = re.search(r'\d+', url).group()
                data['url'] = url
                col.update_one({"id": data['id']}, {"$set": data}, upsert=True)
            except Exception as e:
                print(col.name, url, e)
                error_urls.append(url)
        return error_urls

    def scraper(self, tag_queue: Queue, updated_date: str = "0000-00-00"):
        try:
            client = MongoClient("mongodb://localhost:27017")
            db = client['moduzy']
            print("mongodb connected")
        except Exception as e:
            print(e)
            return
        print(updated_date)
        stop_event = Event()
        while not tag_queue.empty():
            stop_event.clear()
            tag = tag_queue.get()
            url = self.root + f"/list{tag}"
            print(f"[Scraper tag: {tag}, url: {url}]")
            try:
                res = requests.get(url)
                res.raise_for_status()
                mat = re.search(r'<a href="/list[0-9]+-([0-9]+)/" title="尾页">尾页</a>', res.text)
                end_page = int(mat.group(1))
            except Exception as e:
                print(tag, "Get end page error:", e)
                continue
            url_queue = Queue()
            user_agent = self.ua.random   
            for index in range(1, end_page + 1):
                if stop_event.is_set():
                    break
                page = self.root + f"/list{tag}-{index}"
                print(tag, "get vod list on page", index)
                try:
                    res = requests.get(page, timeout=20, headers={"User-Agent": user_agent})
                    res.raise_for_status()
                    vod_list = self._get_vod_list(res.text)
                except Exception as e:
                    print(tag, "Get vod list error on page", index, e)
                    break
                for vod in vod_list:
                    updated = date.fromisoformat(vod['updated'])
                    if updated < date.fromisoformat(updated_date):
                        stop_event.set()
                        print(tag, "Before updated_date, stop on page", index, ",vod", vod)
                        break
                    url_queue.put(vod['url'])
            try:
                col = db[str(tag)]
                with ThreadPoolExecutor(max_workers=16) as executor:
                    for _ in range(16):
                       executor.submit(self.scraper_worker, url_queue, col)
            except Exception as e:
                print(tag, "fetch data error:", e)
                continue

    def update_all(self, after: str = date.today().isoformat()):
        tag_queue = Queue()
        for index in range(1, 9+1):
            tag_queue.put(index)
        self.scraper(tag_queue, after)

    def update(self, *tags: int, after: str = date.today().isoformat()):
        tag_queue = Queue()
        for tag in tags:
            tag_queue.put(tag)
        self.scraper(tag_queue, after)

    # TODO: 待完善
    def fetch_page_worker(
            self,
            tag_queue: Queue,
            page_queue: Queue,
        ):
        while not tag_queue.empty():
            tag = tag_queue.get()
            try:
                url = self.root + f"/list{tag}"
                res = requests.get(url)
                res.raise_for_status()
                mat = re.search(r'<a href="/list[0-9]+-([0-9]+)/" title="尾页">尾页</a>', res.text)
                end_page = int(mat.group(1))   
                for index in range(1, end_page + 1):
                    page = self.root + f"/list{tag}-{index}"
                    page_queue.put((tag, page))
            except Exception as e:
                print("tag", tag, e)
                tag_queue.put(tag)
    # TODO: 待完善
    def fetch_url_worker(
            self,
            page_queue: Queue,
            url_queue: Queue,
            data_stop_event: Event,
            page_stop_event: Event,
            stop_tags: set,
            stop_tags_lock: Lock,
            after_updated_date: str = '0000-00-00',
        ):
        while not page_queue.empty():
            tag, page = page_queue.get()
            if tag in stop_tags:
                continue
            try:
                res = requests.get(page, timeout=10, headers={"User-Agent": self.ua.random})
                res.raise_for_status()
                vod_list = self._get_vod_list(res.text)
                for vod in vod_list:
                    updated = date.isoformat(vod['updated'])
                    if updated < date.isoformat(after_updated_date):
                        page_stop_event.set()
                        with stop_tags_lock:
                            stop_tags.add(tag)
                        break
                    url_queue.put((tag, vod['url']))
            except Exception as e:
                print(page, e)
        data_stop_event.set()

    # TODO: 待完善
    def fetch_data_worker(
            self,
            url_queue: Queue,
            data_queue: Queue,
            data_stop_event: Event,
            write_stop_event: Event
        ):
        while True:
            if url_queue.empty():
                if data_stop_event.is_set():
                    break
                time.sleep(1)
                continue
            tag, url = url_queue.get()
            try:
                res = requests.get(url, timeout=10, headers={"User-Agent": self.ua.random})
                res.raise_for_status()
                data = self._get_vod_data(res.text)
                data['id'] = re.search(r"\d+", url).group()
                data['url'] = url
                data_queue.put((tag, data))
            except Exception as e:
                print(url, e)
        write_stop_event.set()
    # TODO: 待完善
    def write_data_worker(
            self,
            mongo_client: MongoClient,
            db_col: tuple[str, int],
            data_queue: Queue,
            write_stop_event: Event
        ):
        db, col = db_col
        collection = mongo_client[db][str(col)]
        while True:
            if data_queue.empty():
                if write_stop_event.is_set():
                    break
                time.sleep(1)
                continue
            tag, data = data_queue.get()
            if tag != col:
                data_queue.put(tag, data)
                continue
            try:
                collection.update_one({"id": data['id']}, { "$set": data})
            except Exception as e:
                print(data, e)

DLog = Logger(name="modudownloader", filename="DownloadLog.log")

class ModuDownloader:
    # 类级变量
    _max_workers = os.cpu_count() or 8
    _output_dir = Path(__file__).parent
    _ua = UserAgent()
    _ua_lock = Lock()
    _m3u8_queue = Queue()
    _ts_queue = Queue()
    _stop_mids = []
    _stop_mids_lock = Lock()

    def __init__(self,
        max_workers: int | None = None,
        output_dir: str | None = None,
        ):
        """
        任务模式：add_task -> m3u8_queue, do_task => ( m3u8_worker(m3u8_queue) -> ts_worker(ts_queue) )
        """
        # 实例变量
        self.max_workers = max_workers if max_workers is not None else self.__class__._max_workers
        self.output_dir = Path(output_dir) if output_dir is not None else self.__class__._output_dir
        self.ua = UserAgent()
        self.ua_lock = Lock()
        self.stop_mids = set()
        self.stop_mids_lock = Lock()
        self.m3u8_queue = Queue()
        self.ts_queue = Queue()
        self.all_task_stop = Event()

    def m3u8_worker(
            self,
            m3u8_queue: Queue,
            ts_queue: Queue,
            stop_event: Event
        ):
        while not m3u8_queue.empty():
            if self.all_task_stop.is_set():
                return 
            mid, url = m3u8_queue.get()
            os.makedirs(mid, exist_ok=True)
            try:
                with self.ua_lock:
                    user_agent = self.ua.random
                m3 = m3u8.load(url, timeout=16, headers={"User-Agent": user_agent})
                m3.dump(f"{mid}/{mid}.m3u8") 
                for seg in m3.segments:
                    if mid in seg.absolute_uri:
                        ts_queue.put((mid, seg.absolute_uri))
                print("m3u8 worker ok. ID:", mid)
            except Exception as e:
                print("m3u8 worker error. ID:", mid)
                DLog.error(e)
        stop_event.set()
    
    def ts_worker(
            self,
            ts_queue: Queue,
            stop_event: Event
        ):
        with self.ua_lock:
            user_agent = self.ua.random
        while True:
            if self.all_task_stop.is_set():
                print("ts worker stop. All task stop event is set")
                break
            if ts_queue.empty():
                if stop_event.is_set():
                    print("ts worker stop. No task to do.")
                    break
                time.sleep(1)
                continue
            mid, url = ts_queue.get()
            with self.stop_mids_lock:
                if mid in self.stop_mids:
                    continue
            output = os.path.join(mid, os.path.basename(url))
            if os.path.exists(output):
                print("ts worker ok. Ts file existed:", output)
                continue
            try:
                res = requests.get(url, timeout=16, headers={"User-Agent": user_agent})
                res.raise_for_status()
                with open(output, "wb") as f:
                    f.write(res.content)
                print("ts worker ok. Url:", url)
            except Exception as e:
                print("ts worker error. Url:", url)
                DLog.error(e)

    def add_task(
            self,
            *playlists: str,
        ):
        # TODO: 判断任务是否重复，避免重复添加任务
        mids = []
        for playlist in playlists:
            mid = os.path.basename(os.path.dirname(playlist))
            try:
                m3 = m3u8.load(playlist, timeout=16)
                self.m3u8_queue.put((mid, m3.playlists[0].absolute_uri))
                mids.append(mid)
            except Exception as e:
                print("add task error. ID:", mid)
                DLog.error(e)
        print("New Tasks:", mids)
        return mids

    def do_task(
            self,
            *playlists: str
        ):
        mids = self.add_task(*playlists)
        for mid in mids:
            with self.stop_mids_lock:
                if mid in self.stop_mids:
                    self.stop_mids.remove(mid)
        self.all_task_stop.clear()
        # TODO: 添加终止逻辑
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            stop_event = Event()
            for _ in range(self.max_workers - 1):
                executor.submit(self.ts_worker, self.ts_queue, stop_event)
            executor.submit(self.m3u8_worker, self.m3u8_queue, self.ts_queue, stop_event)
        print("do task done.")

    def stop_task(
            self,
            *mids: str
        ):
        for mid in mids:
            with self.stop_mids_lock:
                self.stop_mids.add(mid)

    def stop_all_task(self):
        self.all_task_stop.set()
        print("all task stop event is set.")
    
    def start_all_task(self):
        with self.stop_mids_lock:
            self.stop_mids.clear()
        self.all_task_stop.clear()
        print("start all task.")

    # TODO
    @staticmethod
    def merge_files(*files: str, output: str):
        with open(output, 'wb') as f1:
            for file in tqdm(files):
                with open(file, "rb") as f2:
                    while True:
                        chunk = f2.read(8192)
                        if not chunk:
                            break
                        f1.write(chunk)
        size = os.path.getsize(output)
        for x in ["bytes", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.2f}{x}"
            size = size / 1024
        return f"{size}TB"
    
if __name__ == '__main__':

    def input_listener():
        while True:
            cmd = input(">>> ")
            if cmd == "exit()":
                break
            exec(cmd)
    input_thread = Thread(
        target=input_listener, daemon=True
    )
    input_thread.start()

    md = ModuDownloader()
    md.do_task(
        "https://play.modujx11.com/20250523/vSvLIoFA/index.m3u8",
        "https://play.modujx11.com/20250523/G0fGeFe2/index.m3u8",
        "https://play.modujx11.com/20250530/U5SSkdIG/index.m3u8",
        "https://play.modujx11.com/20250606/sL3KRYlo/index.m3u8",
        "https://play.modujx11.com/20250613/t1NlEk4n/index.m3u8",
        "https://play.modujx11.com/20250620/xUBbfNgW/index.m3u8",
        "https://play.modujx11.com/20250627/pYDNghZw/index.m3u8",
        "https://play.modujx11.com/20250704/GGUAlW2o/index.m3u8",
        "https://play.modujx11.com/20250711/XK5XCgdN/index.m3u8",
        "https://play.modujx11.com/20250718/Vj5fF8Fp/index.m3u8",
    )

    