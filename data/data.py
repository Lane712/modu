
# import re
# import json
# from tqdm import tqdm

# if __name__ == "__main__":

    # with open("json/_movie.json", encoding="utf-8") as f:
    #     data = json.load(f)

    # for vod in tqdm(data):

    #     titles = vod['titles']

    #     if len(titles) == 1:
    #         vod['titles'] = titles[0].split(",")
    #         print(vod['titles'])

        # titles = []
        # genres = []
        # directors = []
        # actors = []
        # aired = ""
        # region = ""
        
        # for key, val in vod["details"].items():
        #     if key == "又名":
        #         titles = val.split(" / ")
        #     elif key == "导演":
        #         directors = val.split(",")
        #     elif key == "主演":
        #         actors = val.split(",")
        #     elif key == "类型":
        #         genres = val.split(",")
        #     elif key == "年份":
        #         if val == "未知":
        #             aired = 0
        #         else:
        #             aired = int(val)
        #     elif key == "地区":
        #         region = val
        
        # vod['titles'] = titles
        # vod['genres'] = genres
        # vod['directors'] = directors
        # vod['actors'] = actors
        # vod['aired'] = aired
        # vod['region'] = region

        # del vod["details"]
    
    # with open("json/_movie.json", "w", encoding="utf-8") as f:
    #     json.dump(data, f, ensure_ascii=False, indent=2)


import json
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")

db = client['mospace']

# with open("json/2.json",'r',encoding='utf-8') as f:
#     vods = json.load(f)
# for vod in vods:
#     db['animes'].update_one({'title': vod['title']}, {'$set': vod}, upsert=True)

# with open("json/1.json",'r',encoding='utf-8') as f:
#     vods = json.load(f)
# for vod in vods:
#     db['guomans'].update_one({'_id': vod['_id']}, {'$set': vod}, upsert=True)

# with open("json/5.json",'r',encoding='utf-8') as f:
#     vods = json.load(f)
# for vod in vods:
#     db['movies'].update_one({'title': vod['title']}, {'$set': vod}, upsert=True)




# with open('json/animemovie_list.json', encoding='utf-8') as file:
#     manga_list = json.load(file)

# with open('json/animemovie.json', encoding='utf-8') as file:
#     manga_data = json.load(file)

# for manga in tqdm(manga_list):
#     for man in manga_data:
#         if manga['title'] == man['title']:
#             man['url'] = manga['url']
#             man['status'] = manga['status']
#             man['update'] = manga['update']

# with open("json/AM.json", 'w', encoding='utf-8') as f:
#     json.dump(manga_data, f, ensure_ascii=False, indent=2)

# from concurrent.futures import ThreadPoolExecutor, as_completed
# import os,re,m3u8
# from urllib.parse import urlparse

# def m3u8_col(title, playlists):
#     os.makedirs(f"m3u8/{title}", exist_ok=True)
#     for playlist in playlists:
#         index = re.search(r'第([\d]+)集', playlist).group(1)
#         url = re.search(r'https?://.*', playlist).group()
#         target_id = re.search(r'([0-9A-Za-z]{8})/index.m3u8',url).group(1)
#         if os.path.exists(f"m3u8/{title}/{title}「{index}」.m3u8"):
#             continue
#         base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
#         try:
#             obj = m3u8.load(url, timeout=5)
#             if obj.is_variant:
#                 obj = m3u8.load(obj.playlists[0].absolute_uri)
#         except m3u8.ParseError:
#             print(title, index, url, "False")
#             continue
#         except Exception:
#             print(title, index, url, "False")
#             continue

#         segments_to_remove = []
#         for seg in obj.segments:
#             seg_uri = seg.uri
#             if seg.discontinuity:
#                 seg.discontinuity = False
#             if re.search(r'.jpg', seg_uri):
#                 seg.uri.replace(".jpg", ".ts")
#             if target_id not in seg_uri:
#                 segments_to_remove.append(seg)
#             elif seg_uri.startswith('/'):
#                 seg.uri = base_url + seg.uri
#         for seg in segments_to_remove:
#             obj.segments.remove(seg)

#         obj.dump(f"m3u8/{title}/{title}「{index}」.m3u8")

#         print(title, index)

#     return True


# if __name__ == "__main__":

#     with open("json/RH.json", encoding='utf-8') as f:
#         data = json.load(f)

#     with ThreadPoolExecutor(max_workers=64) as ext:
#         futures = []
#         for vod in data:
#             title = vod['title']
#             playlists = vod['playlists']
#             futures.append(ext.submit(m3u8_col, title, playlists))
        
#         for future in as_completed(futures):
#             result = future.result()
    