
from datetime import date
import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry
from fake_useragent import UserAgent

from bs4 import BeautifulSoup
from urllib.parse import unquote, urlparse

import shutil,sys
import os,re,json,m3u8
from tqdm import tqdm
from pathlib import Path

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from modu.logger import log
from modu.utils import modify_m3u8_file

from typing import Literal

class ModuConfig:
    REDIRECT_URL = 'https://www.moduzy.vip'
    BASE_URL = 'https://www.moduzy.net'

    DONGMAN = 1
    ANIME = 2
    AMOVIE = 5
    LIFUN = 6
    TAG = Literal[1, 2, 5, 6]

    DATA_FILRS = ['json', 'm3u8', 'temp']

    # TODO:
    # 数据文件为json文件夹，1.获取/ 当前目录、软件目录、根目录 2.读取  3.不存在创建，存在就更新
    # 配置文件类似，不存在使用默认配置，或者提示创建

class ModuScraper:

    ua = UserAgent(os=["Windows"])

    @staticmethod
    def get_root_url():
        res = requests.get(ModuConfig.REDIRECT_URL)
        match = re.search(r'<span> <span>魔都资源：</span> <a href="(https?:.*)" target="_blank" class="home_a">',res.text)
        url = match.group(1)
        return url
        
    @staticmethod
    def fetch(url: str):
        """
        return error or res.content

        获取成功时返回请求结果，失败时返回错误内容
        """
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504], # 429 请求频率过高，网络速率限制
            allowed_methods=["GET"]
        )

        session = requests.Session()
        session.headers['User-Agent'] = UserAgent(os=["Windows"]).random
        session.mount("https://", HTTPAdapter(max_retries=retry))

        error = None
        try:
            res = session.get(url)
            res.raise_for_status()
        except requests.exceptions.RequestException as e:
            log.error(f'fetch RequestException {url} | {e} | {res.headers}')
            error = e
        except Exception as e:
            log.error(f'fetch Error {url} | {e}')
            error = e
        finally:
            session.close()
        
        return error or res
    
    @classmethod
    def update(cls, 
        tag: ModuConfig.TAG = ModuConfig.DONGMAN,
        after: str = date.today().isoformat(),
        workers: int = os.cpu_count() * 4 | 16
        ):

        base_url = ModuConfig.BASE_URL + f"/list{tag}"
        res = cls.fetch(base_url)
        match = re.search(r'<a href="/list[0-9]+-([0-9]+)/" title="尾页">尾页</a>', res.text)
        lp = int(match.group(1))

        vl = cls.get_vod_list(base_url, after=after)
        for i in range(2, lp + 1):
            url = base_url + f"-{i}"
            vll = cls.get_vod_list(url, after=after)
            if len(vll) == 0:
                break
            else:
                vl.extend(vll)

        if len(vl) == 0:
            return 0
        
        vld = []
        with ThreadPoolExecutor(max_workers=workers) as et:
            fs = []
            for ld in vl:
                fs.append(et.submit(cls.get_vod_data, ld['url']))
            
            for f in tqdm(as_completed(fs), total=len(fs)):
                vd = f.result()
                vld.append(vd)

        vld = sorted(vld, key=lambda vd: date.fromisoformat(vd['update']), reverse=True)

        try:
            with open(f'data/json/{tag}.json', "r", encoding='utf-8') as f:
                ovld = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            ovld = []

        with open(f'data/json/{tag}.json', "w", encoding='utf-8') as f:
            print('total', len(ovld))
            for vd in vld:
                for ovd in ovld[:]:
                    if vd['title'] == ovd['title']:
                        ovld.remove(ovd)
                        break
                ovld.append(vd)
            
            ovld = sorted(ovld, key=lambda ovd: (date.fromisoformat(ovd['update']), ovd['aired']), reverse=True)
            print('total', len(ovld), "update", len(vld))
            json.dump(ovld, f, ensure_ascii=False, indent=2)

        return len(vld)

    @staticmethod
    def get_vod_list(url: str, today: bool = False, after: str = ...):
        """ 
        **return**
            vod { title, url, status, update }
        """
        res = requests.get(url, headers={'User-Agent':UserAgent(os=["Windows","Linux"]).random})
        soup = BeautifulSoup(res.text, 'html.parser')
        trs = soup.find("tbody").find_all("tr")
    
        vod_list = []
        today_vod_list = []
        after_vod_list = []
        for tr in trs:
            td_a = tr.find("td").find("a")
            title = td_a.string
            href = ModuConfig.BASE_URL + td_a.get("href")
            status = tr.find("td").find("small").string
            update = date.fromisoformat(re.search(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', tr.text).group())

            vod = {
                "title": title,
                "url": href,
                "status": status,
                "update": update.isoformat()
            }
            vod_list.append(vod)
            
            td_red = tr.find("td", attrs={"class":"text-red"})
            if today:
                if td_red:
                    today_vod_list.append(vod)
                else:
                    return today_vod_list
                
            if after is not Ellipsis:
                if date.fromisoformat(after) <= update:
                    after_vod_list.append(vod)
                else:
                    return after_vod_list
                
            print(title, href, status, update)

        return vod_list

    @staticmethod
    def get_vod_data(url: str):
        res = requests.get(url, headers={"User-Agent": UserAgent().random})
        soup = BeautifulSoup(res.text, 'html.parser')
        
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
        update = ""
        
        for key, val in details.items():
            if key == "又名":
                titles = val.split(" / ")
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
                update = val

        playlists = []
        lists = soup.find('ul', attrs={'class': 'content__playlist'}).find_all('li')
        for li in lists:
            playlist = li.find('a').string
            playlists.append(playlist)

        status = re.search(r'<small class="text-red h5">(.*)</small>', res.text).group(1)

        return {
            'title': title,
            "titles": titles,
            'region': region,
            'aired':aired,
            'status': status,
            "update": update,
            'genres': genres,
            'directors': directors,
            'actors': actors,
            'url': url,
            'imgsrc': imgsrc,
            'playlists': playlists
        }
    
    @classmethod
    def update_vods_list_thread(cls):
        
        def get_last_page_index(url):
            res = cls.fetch(url)
            match = re.search(r'<a href="/list[0-9]+-([0-9]+)/" title="尾页">尾页</a>', res.text)
            return int(match.group(1))
        
        with ThreadPoolExecutor(max_workers=os.cpu_count() * 2 | 4) as ext:
            base_url = "https://www.moduzy.net/list2"
            vod_list = cls.get_vod_list(base_url)
            
            futures = []
            last_index = get_last_page_index(base_url)
            for index in range(2, last_index):
                url = base_url + f"-{index}"
                futures.append(ext.submit(cls.get_vod_list, url))

            for future in as_completed(futures):
                vod_list.extend(future.result())
            print("last_index", last_index, "total", len(vod_list))
        
            with open("data/json/anime_list.json", 'w', encoding='utf-8') as f:
                json.dump(vod_list, f, ensure_ascii=False, indent=2)

    @classmethod
    def update_vods_data_thread(cls):

        with open("data/json/guoman_list.json", encoding='utf-8') as f:
            vod_list = json.load(f)
        
        with ThreadPoolExecutor(max_workers=os.cpu_count() * 4 | 4) as ext:
            futures = []
            for li in tqdm(vod_list):
                url = li['url']
                futures.append(ext.submit(cls.get_vod_data, url))
            vods = []
            for future in tqdm(as_completed(futures), total=len(futures)):
                vods.append(future.result())
            with open('data/json/guoman.json', 'w', encoding='utf-8') as file:
                json.dump(vods, file, ensure_ascii=False, indent=2)

class ModuDownloader:
    # 类级变量
    max_workers = os.cpu_count() or 8
    output_dir = Path(__file__).parent
    m3u8_dir = output_dir.joinpath('m3u8')
    temp_dir = output_dir.joinpath("_temp")

    def __init__(self,
        max_workers: int | None = ...,
        output_dir: str | Path | None = ...,
        ):
        # 实例变量
        self.max_workers = max_workers if max_workers is not None else self.__class__.max_workers
        self.output_dir = Path(output_dir) if output_dir is not None else self.__class__.output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def download_file(url: str, output: str | Path, retry_times: int = 3):
        """
        Return output file's path
        """
        if output.exists():
            return output
        try:
            res = requests.get(url, headers={"User-Agent": UserAgent().random}, timeout=5)
            res.raise_for_status()
            with open(output, 'wb') as f:
                f.write(res.content)
        except Exception as e:
            return False
        return output
    
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

    def load_m3u8(self, url: str):
        m3u8_obj = m3u8.load(url, timeout=5, headers={"User-Agent": UserAgent().random})
        filename = Path(url).parent.name
        if m3u8_obj.is_variant:
            m3u8_obj = m3u8.load(m3u8_obj.playlists[0].absolute_uri, timeout=5)
        output = self.m3u8_dir.joinpath(filename + ".m3u8")
        m3u8_obj.dump(output)
        return modify_m3u8_file(str(output), url)
    
    @classmethod
    def load_m3u8(cls, url: str):
        m3u8_obj = m3u8.load(url, timeout=5, headers={"User-Agent": UserAgent().random})
        filename = Path(url).parent.name
        if m3u8_obj.is_variant:
            m3u8_obj = m3u8.load(m3u8_obj.playlists[0].absolute_uri, timeout=5)
        output = cls.m3u8_dir.joinpath(filename + ".m3u8")
        m3u8_obj.dump(output)
        return modify_m3u8_file(str(output), url)
    
    # TODO: eq load_m3u8()
    @staticmethod
    def download_m3u8(url: str, output: Path, fid: str | None = None):
        m3 = m3u8.load(url)
        base_uri = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        if m3.is_variant:
            m3 = m3u8.load(m3.playlists[0].absolute_uri)
        segments_to_remove = []
        for seg in m3.segments:
            uri = seg.absolute_uri or seg.uri
            if uri.startswith("/"):
                seg.uri = base_uri + uri
            if uri.endswith(".jpg"):
                seg.uri = uri.replace(".jpg", ".ts")
            if fid and fid not in uri:
                segments_to_remove.append(seg)
        for seg in segments_to_remove:
            m3.segments.remove(seg)
        m3.dump(output)
        return output
    
    @classmethod
    def download_all_m3u8(cls):
        with open('data/json/manga.json', encoding='utf-8') as file:
            vod_data = json.load(file)
        with ThreadPoolExecutor(max_workers=32) as ext:
            futures = []
            urls = []
            for vod in tqdm(vod_data):
                playlists = vod['playlists']
                for playlist in playlists:
                    urls.append(re.sub(r"第\d+集\$", "" ,playlist))
            for url in tqdm(urls):
                try:
                    filename = os.path.dirname(url) + ".m3u8"
                    output = Path(__file__).parent.joinpath("m3u8", filename)
                    if output.exists():
                        continue
                    futures.append(ext.submit(cls.download_m3u8, url, output))
                except Exception as e:
                    print(url, e)
                    continue
            for future in tqdm(as_completed(futures), total=len(futures)):
                result = future.result()

    def download_all_segments(self, m3u8_file: str):
        m3u8_obj = m3u8.load(m3u8_file)
        id, extension = os.path.splitext(Path(m3u8_file).name)[0]
        downloaded_segments = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as ext:
            futures = []
            for index, seg in enumerate(m3u8_obj.segments):
                url = seg.uri
                output = self.temp_dir.joinpath(id, f"{index:4d}{id}{extension}")
                futures.append(ext.submit(self.download_file, url, output))
            for future in tqdm(as_completed(futures), total=len(futures)):
                res = future.result()
                if res:
                    downloaded_segments.append(res)
        return sorted(downloaded_segments)
    
    @classmethod
    def download_all_segments(cls,
            m3u8_file: str | Path,
            max_workers: int | None = None
        ) -> list[str] | list[Path]:
        # TODO: 
        m3u8_obj = m3u8.load(m3u8_file.as_uri())
        id = os.path.splitext(Path(m3u8_file).name)[0]
        downloaded_segments = []
        while True:
            downloaded_segments = []
            with ThreadPoolExecutor(max_workers=max_workers or cls.max_workers) as ext:
                futures = []
                for index, seg in enumerate(m3u8_obj.segments):
                    url = seg.uri
                    cls.temp_dir.joinpath(id).mkdir(parents=True, exist_ok=True)
                    output = cls.temp_dir.joinpath(id, f"{index:04d}{id}.ts")
                    if os.path.exists(output):
                        downloaded_segments.append(output)
                        continue
                    futures.append(ext.submit(cls.download_file, url, output))
                for future in tqdm(as_completed(futures), total=len(futures)):
                    res = future.result()
                    if res:
                        downloaded_segments.append(res)
            if len(downloaded_segments) == len(m3u8_obj.segments):
                break

        return sorted(downloaded_segments)
    
    @classmethod
    def download(cls, url: str, max_workers: int | None = None, output: str | Path = ...):
        id = Path(url).parent.name
        print(id)
        m3u8_file = cls.load_m3u8(url)
        ts_files = cls.download_all_segments(m3u8_file, max_workers)
        if output == Ellipsis:
            print(cls.merge_files(*ts_files, output=cls.output_dir.joinpath("video", f"{id}.ts")))
        else:
            print(cls.merge_files(*ts_files, output=output))
        return shutil.rmtree(cls.temp_dir.joinpath(id))
    
if __name__ == '__main__':

    ModuScraper.update(tag="2", after='2025-06-08')

    pass