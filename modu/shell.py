import argparse
from modu.main import ModuDownloader
from datetime import date

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    subparser = parser.add_subparsers(dest="command")

    parser.add_argument("update", action="store_true", help="更新数据")

    parser_search = subparser.add_parser("search")
    parser_search.add_argument("name", type=str, help="标题")
    parser_search.add_argument("-g", "--genres", nargs="+", type=str, help="分类")
    parser_search.add_argument("-r", "--region", choices=["大陆", "日本", "韩国", "美国"], help="国家" )
    parser_search.add_argument("-a", "--aired", type=int, help="年份")

    parser_download = subparser.add_parser("d")
    parser_download.add_argument("url", type=str, help="m3u8文件链接")
    parser_download.add_argument("-w", "--workers", type=int, help="下载线程数")
    parser_download.add_argument("-o", "--output", default=date.ctime()+".ts" , type=str, help="输出文件路径")

    args = parser.parse_args()

    if args.command == "search":
        print("ssssssss")
    elif args.command == "d":
        ModuDownloader.download(args.url, max_workers=args.workers, output=args.output)

