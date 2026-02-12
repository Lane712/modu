
from posixpath import basename,dirname
import requests
from fake_useragent import UserAgent
    
import ddddocr

from bs4 import BeautifulSoup

import time
import os,re,json,m3u8
from tqdm import tqdm
from pathlib import Path
from datetime import date
import subprocess

from queue import Queue
from queue import Empty as QueueEmpty
from threading import Event, Lock, Thread
from concurrent.futures import ThreadPoolExecutor, as_completed, Future

from pymongo import MongoClient
from modu.base import Logger

log = Logger(level=Logger.DEBUG, file_level=Logger.DEBUG, stream_level=Logger.DEBUG)
SLog = Logger(name="moduscraper", filename="ScrapeLog.log", stream_level=log.INFO)
DLog = Logger(name="modudownloader", filename="DownloadLog.log", stream_level=log.INFO)

from typing import Literal

MODUTAG = Literal[1,2,3,4,5,6,7,8,9]
    # 国产动漫 1
    # 日韩动漫 2
    # 欧美动漫 3
    # 港台动漫 4
    # 动漫电影 5
    # 里番 6
    # 电影 7
    # 连续剧 8
    # 综艺 9

import configparser

class ModuConfig:
    def __init__(self):
        self.config = configparser.ConfigParser()
        if os.path.exists("config.ini"):
            self.config.read("config.ini", encoding="utf-8")
        self.redirect = self.config['urls']['redirect'] or'https://www.moduzy.vip'
        self.root = self.config['urls']['root'] or 'https://www.moduzy.cc'
        output_dir = Path()
        self.temp_dir = self.config['files']['temp'] or output_dir.joinpath("_temp").as_posix()
        self.m3u8_dir = self.config['files']['m3u8'] or output_dir.joinpath("m3u8").as_posix()
        if not os.path.exists("config.ini"):
            with open("config.ini", "w", encoding="utf-8") as f:
                self.config.write(f)

    def update_root_url(self):
        """Get the latest root url"""
        res = requests.get(self.redirect)
        res.raise_for_status()
        match = re.search(r'<span> <span>魔都资源：</span> <a href="(https?:.*)" target="_blank" class="home_a">',res.text)
        url = match.group(1)
        if url:
            self.root = url
            print("Changed Root:", self.root)
            self.config['urls']['root'] = url
            with open("config.ini", "w", encoding="utf-8") as f:
                self.config.write(f)
        return self.root

    # TODO:
    # 数据文件为json文件夹，1.获取/ 当前目录、软件目录、根目录 2.读取  3.不存在创建，存在就更新
    # 配置文件类似，不存在使用默认配置，或者提示创建

moduConfig = ModuConfig()

class ModuScraper:
    def __init__(self):
        self.root = moduConfig.root
        self.ua = UserAgent(os=["Windows","Android"])
        self.session = requests.Session()
        self.session.headers['User-Agent'] = self.ua.random
        self.ocr = None

    def update_user_agent(self):
        self.session.headers['User-Agent'] = self.ua.random
        return self.session.headers

    def verify_search_cookie(self):
        """Verify to use search function"""
        res = self.session.get(self.root)
        print(res.headers, self.session.cookies.items())
        r1 = self.session.get(self.root + "/index.php/verify/index.html")
        r1.raise_for_status()
        if self.ocr is None:
            self.ocr = ddddocr.DdddOcr()
        result = self.ocr.classification(r1.content)
        print("验证码识别结果：", result)
        r2 = self.session.get(self.root + f"/index.php/ajax/verify_check?type=search&verify={result}")
        print(r2.text)
        if r2.json()['msg'] == "ok":
            return self.session.cookies.items()

    def search(self, kwd: str):
        """Search by `kwd`. Return `list`**[ {title, status, updated, url} ]**"""
        search_url = self.root + f"/search/-------------/?wd={kwd}&submit="
        res = self.session.get(search_url)
        res.raise_for_status()
        if res.headers.get("Set-Cookie"):
            self.verify_search_cookie()
            return self.session.cookies.items()
        return self._get_vod_list(res.text)

    @staticmethod
    def _get_vod_list(html: str):
        """
        ### return
        > `list[dict]` => **dict** `{ title, status, updated, url }`
        """
        soup = BeautifulSoup(html, "html.parser")
        tbody = soup.find("tbody")
        if tbody is None:
            return []

        vod_list = []
        trs = tbody.find_all("tr")
        for tr in trs:
            td1 = tr.find("td")
            title = td1.find("a").string
            url = moduConfig.root + td1.find("a").get("href")
            status = td1.find("small").string
            updated = tr.find_all("td")[2].string
            vod_list.append({
                "title": title,
                "status": status,
                "updated": updated,
                "url": url
            })
        return vod_list
    
    def get_vods(
            self,
            page: str
        ):
        """
        ### page
        > a `url` whose page is consistent of vod list.
        """
        urls = []
        try:
            res = requests.get(page, timeout=10, headers={"User-Agent": self.ua.random})
            res.raise_for_status()
            vod_list = self._get_vod_list(res.text)
            for vod in vod_list:
                urls.append(vod['url'])
        except Exception as e:
            print(page, e)
        return urls
    
    def get_urls_by_tag(
            self,
            tag: int,
            updated_date: str = "0000-00-00"
        ):
        """
        ### tag
        > an `int` that stand for a vod's tag.  
        > **example**: `1` => "国产动漫".

        ### return
        > `array` all the links of every vod detail page.
        """
        urls = []
        SLog.info("start get urls, Tag:", tag)
        try:
            url = self.root + f"/list{tag}"
            res = requests.get(url, timeout=16, headers={"User-Agent": self.ua.random})
            res.raise_for_status()
            mat = re.search(r'<a href="/list[0-9]+-([0-9]+)/" title="尾页">尾页</a>', res.text)
            end_page = int(mat.group(1))
        except Exception as e:
            SLog.error("get_urls() error on get 'end_page'. Tag:", tag, "Detail:", e)   
        for index in range(1, end_page + 1):
            page = self.root + f"/list{tag}-{index}"
            try:
                res = requests.get(page, timeout=10, headers={"User-Agent": self.ua.random})
                res.raise_for_status()
                vod_list = self._get_vod_list(res.text)
                for vod in vod_list:
                    updated = date.fromisoformat(vod['updated'])
                    if updated < date.fromisoformat(updated_date):
                        return urls
                    urls.append(vod['url'])
            except Exception as e:
                SLog.error("get_urls() error on get 'urls'. Detail:", e)
        return urls
    
    @staticmethod
    def _get_imgsrc(soup: BeautifulSoup):
        '''
        获取视频封面链接

        Args:
            soup: 
        Returns:
            dict: 返回一个 ***dict*** 变量，格式为 {
                **`"title"`**: str,
                **`"imgsrc"`**: imgsrc
            }
        '''
        img = soup.find("p", attrs={'class': 'thumb'}).find('img',src=True)
        title = img.get('alt')
        imgsrc = img.get('src')
        return {
            "title": title,
            "imgsrc": imgsrc
        }
    
    @staticmethod
    def _get_playlists(soup: BeautifulSoup):
        '''
        Args:
            soup (BeautifulSoup): 
        
        Returns:
            list: 视频播放列表
        '''
        playlists = []
        lists = soup.find('ul', attrs={'class': 'content__playlist'}).find_all('li')
        for li in lists:
            playlist = li.find('a').string
            playlists.append(playlist)
        return playlists
    
    @staticmethod
    def _get_details(soup: BeautifulSoup):
        """
        ### *return*
        > a `dict` container **details** about this video.
        """
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
        return {
            'title': titles[0],
            "titles": titles,
            'region': region,
            'aired':aired,
            "updated": updated,
            'genres': genres,
            'directors': directors,
            'actors': actors,
        }
    
    def _get_vod_data(self, html: str):
        soup = BeautifulSoup(html, "html.parser")
        data = self._get_details(soup)
        data.update(self._get_imgsrc)
        data.update(self._get_playlists)
        return data

    def get_data(
            cls,
            url: str,
        ):
        """
        ### url
        > the link of a vod detail page.  
        > **example**: `www.moduzy.net/vod/123/`
        """
        SLog.info("start get data, Url:",url)
        try:
            res = requests.get(url, timeout=10, headers={"User-Agent": self.ua.random})
            res.raise_for_status()
            data = cls._get_vod_data(res.text)
            data['id'] = re.search(r"\d+", url).group()
            data['url'] = url
        except Exception as e:
            SLog.error("get_data() error. Url:", url, "Deatail:", e)
            return {}
        return data

    def get_data_worker(self, tag: int, url_queue: Queue, data_queue: Queue):
        error_urls = []
        while not url_queue.empty():
            url = url_queue.get()
            try:
                data = self.get_data(url)
                data['tag'] = tag
                data_queue.put(data)
            except Exception as e:
                SLog.error("ModuScraper.get_data_worker() error. Url:", url, "Detail:", e)
                error_urls.append(url)
        return error_urls

    #TODO:扩展
    def write_data_worker(self, data_queue: Queue):
        try:
            client = MongoClient("mongodb://localhost:27017")
            db = client['moduzy']
            SLog.info("mongodb connected")
        except Exception as e:
            SLog.error("mongodb connection error. Detail:", e)
            return
        while not data_queue.empty():
            data = data_queue.get()
            col = db[str(data['tag'])]
            SLog.info("write data to mongodb collection:", col.name)
            col.update_one({"id": data['id']}, {"$set": data}, upsert=True)

    def scraper(self, *tags: int, updated_date: str = "0000-00-00"):
        SLog.info("ModuScraper.scraper(). Tags:",tags,"Updated:",updated_date)
        url_queue = Queue()
        data_queue = Queue()
        for tag in tags:
            try:
                urls = self.get_urls_by_tag(tag, updated_date)
                for url in urls:
                    url_queue.put(url)
                SLog.info("ModuScraper.scraper() get urls ok. Total:", url_queue.qsize())
                with ThreadPoolExecutor(max_workers=min(url_queue.qsize(), 16)) as executor:
                    SLog.info("ModuScraper.scraper() start get data. Max_Workers:", executor._max_workers)
                    for _ in range(16):
                       executor.submit(self.get_data_worker, tag, url_queue, data_queue)
                SLog.info("ModuScraper.scraper() get data ok. Total:", data_queue.qsize())
            except Exception as e:
                SLog.error("ModuScraper.scraper() error. Tag:", tag, "Detail:", e)
                continue
        return list(data_queue.queue)

    def update_all(self, updated_date: str = date.today().isoformat()):
        tags = []
        for index in range(1, 9+1):
            tags.append(index)
        SLog.info("update tags:", tags, "updated_date:", updated_date)
        self.scraper(*tags, updated_date=updated_date)

class DownloadTask:
    """
    下载任务

    ---

    给定下载的m3u8链接和对应mid
    """
    def __init__(
            self,
            url: str,
            mid: str,
            name: str | None = None,
            max_workers: int | None = None,
            output_dir: str | Path | None = None,
        ):
        self.url = url
        self.mid = mid
        self.name = mid if name is None else name
        self.output_dir = Path(output_dir) if output_dir else Path()
        self._temp_dir = self.output_dir.joinpath("_temp")
        
        self.max_workers = os.cpu_count() if max_workers is None else max_workers # 适合16线程，多余的会被拒绝

        self.ts_queue = Queue()
        self.stop_signal = False
        self.start_event = Event()

        self._parse(self.url, self.mid, self.ts_queue)

    def _parse(self, url: str, mid: str, ts_queue: Queue):
        self.temp_dir = self._temp_dir.joinpath(mid)
        self.temp_dir.mkdir(exist_ok=True)
        try:
            m3 = m3u8.load(url, timeout=16, headers={"User-Agent": UserAgent().random})
            m3.dump(self.output_dir.joinpath("m3u8", f"{mid}.m3u8")) 
            for seg in m3.segments:
                if mid in seg.absolute_uri:
                    ts_queue.put(seg.absolute_uri)
        except Exception as e:
            DLog.error("DownloadTask.parse() error.", "Url:", url, "Detail:", e)
            return False
        finally:
            DLog.info("DownloadTask.pasre() OK.", "Total:", ts_queue.qsize())
        
        self.total = ts_queue.qsize()
        self.executor = ThreadPoolExecutor(self.max_workers)
        for _ in range(self.max_workers):
            self.executor.submit(self.ts_worker, self.ts_queue)
        self.start()
        return True

    def ts_worker(self, ts_queue: Queue):
        ua = UserAgent()
        while not ts_queue.empty():
            self.start_event.wait()
            if self.stop_signal:
                break
            try:
                url = ts_queue.get(timeout=16)
                output = self.temp_dir.joinpath(basename(url))
                if os.path.exists(output):
                    continue
                res = requests.get(url, timeout=8, headers={"User-Agent": ua.random})
                res.raise_for_status()
                with open(output, "wb") as f:
                    f.write(res.content)
            except QueueEmpty:
                break
            except requests.Timeout:
                ts_queue.put(url)
                continue
            except requests.ConnectionError:
                time.sleep(8)
                ts_queue.put(url)
                continue

    def start(self):
        self.stop_signal = False
        self.start_event.set()

    def stop(self):
        self.stop_signal = True
        self.start_event.clear()
        self.executor = None

    def pause(self):
        self.start_event.clear()

    def __str__(self):
        return self.name

    def __del__(self):
        self.stop()

class ModuDownloader:
    """
    下载管理类

    ---

    添加下载任务，管理下载任务

    """
    def __init__(
            self,
            output_dir: str | Path | None = None,
        ):
        """

        """
        self.output_dir = Path(output_dir) if output_dir is not None else Path(__file__).parent
        self.ua = UserAgent()
        self.start_event = Event()
        self.stop_event = Event()

        self.tasks = [DownloadTask]

    def add_tasks(
            self,
            *playlists: str,
        ):
        if len(playlists) == 0:
            DLog.warning("ModuDownloader.add_tasks() waring.No playlists get.")
            return []
        mids = []
        for playlist in playlists:
            mid = basename(dirname(playlist))
            try:
                m3 = m3u8.load(playlist, timeout=16, headers={"User-Agent": self.ua.random})
                d_task = DownloadTask(m3.playlists[0].absolute_uri, mid, output_dir=self.output_dir)
                self.tasks.append(d_task)
                mids.append(mid)
            except Exception as e:
                DLog.error("ModuDownloader.add_tasks() error on M3U8 ID:", mid, e)
        DLog.info("ModuDonloader.add_tasks() ok. New Tasks MID:", mids)
        return len(self.tasks)

    def stop_all_tasks(self):
        for task in self.tasks:
            task.stop()
        
        self.stop_event.set()

    def check_process(self):
        while not self.stop_event.is_set():
            time.sleep(8)
            for task in self.tasks:
                DLog.info(f"DownloadTask {task.name}: {task.ts_queue.qsize()}/{task.total}")

    def start_check_loop(self):
        self.thread = Thread(
            target=self.check_process,
            daemon=True
        )
        self.thread.start()

    def __del__(self):
        self.stop_all_tasks()

import os.path
import random
import cv2 as cv

class ModuUtils:
    output_dir = Path(__file__).parent
    temp_dir = output_dir.joinpath("./_temp")
    m3u8_dir = output_dir.joinpath("./m3u8")

    @classmethod
    def extract_random_frames(cls, video_file: str, n: int = 1):
        """
        ### video_file  
            视频文件

        ### n   
            需要截取的帧总数，默认为 `1`
        """
        video_file = os.path.normpath(video_file)
        id = os.path.splitext(os.path.basename(video_file))[0]

        cap = cv.VideoCapture(video_file)
        total_frames = int(cap.get(cv.CAP_PROP_FRAME_COUNT))
        fps = int(cap.get(cv.CAP_PROP_FPS))

        # 生成不重复的随机帧号（0-based）
        random_frames = random.sample(range(total_frames), min(n, total_frames))
        random_frames.sort()
        log.info(f"ModuUtils.extract_random_frames. Frames:", total_frames)

        extracted_frame_count = 0
        output_dir = cls.output_dir.joinpath("shotcut", id)
        output_dir.mkdir(exist_ok=True)

        with tqdm(total=len(random_frames), desc="extract frame") as pbar:
            for frame_num in random_frames:
                # TODO: 会报错，H.264编码问题，但能正常输出
                cap.set(cv.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = cap.read()
                if not ret:
                    break
                filename = f"{id}_{frame_num:06d}.png"
                output_path = output_dir.joinpath(filename)
                cv.imwrite(output_path.as_posix(), frame) # TODO: cv2库 中文路径会写入失败！
                extracted_frame_count += 1
                pbar.update(1)

        cap.release()

    @staticmethod
    def _get_size(file: str | Path):
        size = os.path.getsize(file)
        for x in ["bytes", "KB", "MB", "GB" ,"TB"]:
            if size < 1024:
                return f"{size:.2f}{x}"
            size = size / 1024
        return f"{size:.2f}PB"

    @classmethod
    def merge(cls, *mids):
        if len(mids) == 0:
            mids = os.listdir(cls.temp_dir)
            log.warning("ModuUtils.merge() no `mids` arguments get. Default get from `_temp/`:", mids)
        for mid in mids:
            pt = cls.m3u8_dir.joinpath(f"{mid}.m3u8")
            if not pt.exists():
                log.warning("ModuUtils.merge() skip. m3u8 file doesn't exist. M3U8 ID:", mid, "Path:", pt)
                continue
            m3 = m3u8.load(pt.as_uri())
            ts = set(os.listdir(cls.temp_dir.joinpath(mid)))
            fls = []
            for seg in m3.segments:
                if mid in seg.absolute_uri:
                    fls.append(os.path.basename(seg.absolute_uri).replace(".jpg", ".ts"))
            s_fls = set(fls)
            if not s_fls.issubset(ts):
                log.warning("ModuUtils.merge() stop. M3U8 ID:", mid, "Losing:", s_fls.difference(ts))
                continue
            output = cls.output_dir.joinpath("video", f"{mid}.ts")
            if os.path.exists(output):
                log.warning("ModuUtils.merge() skip. File exists:", output)
                continue
            with open(output, "wb") as f1:
                for fl in tqdm(fls, desc=mid):
                    f = cls.temp_dir.joinpath(mid, fl)
                    with open(f, "rb") as f2:
                        f1.write(f2.read())
            size = cls._get_size(output)
            log.info("ModuUtils.merge() ok. Output:", output, "Size:", size)

    @classmethod
    def convert(cls, copy: bool = True, remove: bool = False):
        """
        ### copy  
            if `copy` is `True`, this videos file will not redecode -- use`-c copy`, othesize redecode.
        ### remove  
            whether remove the original file.
        """
        di = cls.output_dir.joinpath("video")
        vdos = os.listdir(di)
        for vdo in vdos:
            mid, ext = os.path.splitext(vdo)
            if ext != ".ts":
                DLog.info("ModuUtils.convert() skip. It's not a ts-file. Video:", vdo)
                continue
            input = di.joinpath(vdo)
            output = di.joinpath(f"{mid}.mp4")
            if os.path.exists(output):
                DLog.warning(f"ModuUtils.convert() skip. Output {output.as_posix()} already existed.")
            else:
                if copy:
                    subprocess.run(["ffmpeg", "-i", input.as_posix(), "-c", "copy", output.as_posix()])
                else:
                    subprocess.run(["ffmpeg", "-i", input.as_posix(), output.as_posix()])
                DLog.info("ModuUtils.convert() ok. Output:", output.as_posix())
            if remove:
                os.remove(input)
                DLog.info("ModuUtils.convert() remove original file. File:", input.as_posix())

    @classmethod
    def clear_temp(cls):
        mids = os.listdir(cls.temp_dir)
        for mid in mids:
            di = cls.temp_dir.joinpath(mid)
            fls = os.listdir(di)
            for fl in tqdm(fls,desc=f"clear {mid}"):
                f = di.joinpath(fl)
                os.remove(f)
            DLog.info("ModuUtils clear temp files. Directory:", di.as_posix())

if __name__ == '__main__':

    # def input_listener():
    #     while True:
    #         cmd = input(">>> ")
    #         if cmd == "exit()":
    #             break
    #         exec(cmd)
    # input_thread = Thread(
    #     target=input_listener, daemon=True
    # )
    # input_thread.start()

    md = ModuDownloader()
    md.add_tasks(
        "https://play.modujx11.com/20250802/Cha4M4YU/index.m3u8"
    )

    md.start_check_loop()

    time.sleep(16)

    md.stop_all_tasks() # 无法释放所有资源

    del md

    pass