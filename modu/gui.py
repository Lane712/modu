
import os,re
from tkinter import *
from tkinter import font as tkfont
from tkinter import ttk
import asyncio
import threading
from modu.main import ModuDownloader

class ModuApp():

    def __init__(self):
        self.root = Tk()
        self.root.title("ModuApp")

        self.download_thread = threading.Thread()
        self.download_loop = asyncio.new_event_loop()
        self.download_future = None

        self.font_var = StringVar(value="黑体")
        self.font_families = tkfont.families()

        self.output_format_array = ["mp4", "mkv", "mov"]
        self.output_format_var = StringVar(value=self.output_format_array[0])
        self.download_thread_var = IntVar(value = (os.cpu_count() or 4))
        self.new_genre_var = StringVar()
        self.search_var = StringVar()
        self.download_var = StringVar()

        self.create_widgets()

        #TODO bug: 子组件也会触发
        self.root.bind("<Configure>", self.window_on_resize)

    def run(self):
        """run TK.mainloop()"""
        self.root.mainloop()

    def window_on_resize(self, event: Event):
        if event.widget == self.root:
            print(f'root | {event.width} x {event.height}')
        if event.widget == self.content_frame:
            print(f'content | {event.width} x {event.height}')
        if event.widget == self.search_input_frame:
            print(f'search input | {event.widget} x {event.height}')
        if event.widget == self.search_results_frame:
            self.search_results_canvas.config(width=event.width)
            print(f'search results | {event.width} x {event.height}')

    def create_widgets(self):
        self.center_window()
        self.root.rowconfigure(1, weight=1)

        # 菜单栏
        self.navigation_frame = ttk.Frame(self.root)
        self.navigation_frame.grid(row=0, sticky=NW, pady=8)
        self.create_navgation()

        # 主内容
        self.content_frame = ttk.Frame(self.root)
        self.content_frame.grid(row=1, sticky=NSEW, pady=8)
        self.create_content()

    def center_window(self):
        # 设置窗口大小和位置
        window_width = 1080
        window_height = 640
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")

    def create_navgation(self):
        ttk.Button(
            self.navigation_frame,
            text = "file"
        ).grid(row=1, column=0, padx=16)

        # ttk.Label(
        #     self.navigation_frame,
        #     text="init" 
        # ).grid(row=1, column=1, padx=10)

        # ttk.Label(
        #     self.navigation_frame,
        #     text="config"
        # ).grid(row=1, column=2, padx=10)

        # ttk.Label(
        #     self.navigation_frame,
        #     text="style"
        # ).grid(row=1, column=3, padx=10)

        # ttk.Label(
        #     self.navigation_frame,
        #     text="about"
        # ).grid(row=1, column=4, padx=10)

        ## 视频输出格式
        ttk.Label(
            self.navigation_frame,
            text="输出格式"
        ).grid(row=1, column=1)

        output_format_optionmenu = ttk.OptionMenu(
            self.navigation_frame, self.output_format_var, *self.output_format_array)
        output_format_optionmenu.grid(row=1, column=2)

        ## 设置下拉菜单
        config_menu = Menu(self.navigation_frame, tearoff=False)
        # config_menu.add_command(label="command") # 命令项
        # config_menu.add_checkbutton(label="checkbutton") # 单选按钮
        # config_menu.add_separator() # 分割线
        
        # 字体
        config_menu_font_menu = Menu(self.navigation_frame, tearoff=False)
        for font in self.font_families:
            if "@" in font:
                continue
            if re.search(r"[\u4e00-\u9fff]+", font):
                config_menu_font_menu.add_radiobutton(
                    label=str(font),
                    value=font,
                    variable=self.font_var
                )
        config_menu.add_cascade(label="字体", menu=config_menu_font_menu)

        # 下载线程数
        config_menu_thread_menu = Menu(self.navigation_frame, tearoff=False)
        for index in range(2, 17, 2):
            config_menu_thread_menu.add_radiobutton(
                label=str(index),
                value=index,
                variable=self.download_thread_var
            )
        config_menu.add_cascade(label="下载线程数", menu=config_menu_thread_menu) # 子菜单

        ttk.Menubutton(
            self.navigation_frame,
            text="设置",
            menu=config_menu
        ).grid(row=1, column=3)    

        ttk.Label(
            self.navigation_frame,
            text="下载线程数"
        ).grid(row=1, column=4)

        ttk.OptionMenu(
            self.navigation_frame,
            self.download_thread_var,
            *[2,4,8,16]
        ).grid(row=1, column=5)

        # ttk.Label(
        #     self.navigation_frame,
        #     text="字体"
        # ).grid(row=1, column=6)

        # self.font_combobox = ttk.Combobox(
        #     self.navigation_frame,
        #     textvariable=self.font_var,
        #     values=self.font_families
        # )

        # self.font_combobox.grid(row=1, column=7)

        # self.font_combobox.bind(
        #     "<<ComboboxSelected>>",
        #     # TODO
        #     lambda e: self.search_results_frame.config()
        # )

    def create_content(self):

        # 搜索框
        self.search_input_frame = ttk.Frame(self.content_frame)
        self.search_input_frame.grid(row=1, padx=16, pady=8)
        self.search_input()

        # 搜索结果
        self.search_results_canvas = Canvas(self.content_frame)
        self.search_results_canvas.config(
            yscrollcommand=None
        )
        self.search_results_frame = ttk.Frame(self.search_results_canvas)
        self.search_results_frame.config(
            border=1,
            borderwidth=1,
            padding=8
        )

        self.content_frame.rowconfigure(2, weight=1)
        self.search_results_canvas.grid(row=2, sticky=NSEW, padx=16, pady=8)
        self.search_results_canvas.create_window((0, 0), window=self.search_results_frame, anchor="nw")

        # 更新滚动区域
        self.search_results_frame.bind(
            "<Configure>",
            lambda e: (self.search_results_canvas.config(scrollregion=self.search_results_canvas.bbox("all")))
        )
        # 绑定滚动事件（TODO: 替换bind_all）
        self.search_results_canvas.bind(
            "<Enter>",
            lambda e1: (self.search_results_canvas.bind_all(
                "<MouseWheel>",
                lambda e2: (self.search_results_canvas.yview_scroll(int(-1 * (e2.delta / 120)), "units"))   
            ))
        )
        # 解绑滚动事件（待优化）
        self.search_results_canvas.bind(
            "<Leave>",
            lambda e: self.search_results_canvas.unbind_all("<MouseWheel>")
        )

    def search_input(self):

        self.search_input_frame.rowconfigure(0, weight=1)
        self.search_input_frame.columnconfigure([0,1], weight=1)

        ttk.Entry(
            self.search_input_frame,
            textvariable=self.search_var
        ).grid(row=1, column=0, sticky=NSEW, padx=(10,0))

        ttk.Button(
            self.search_input_frame,
            text="搜索",
            command=self.search
        ).grid(row=1, column=1, sticky=NSEW, padx=(0,10))

    def search_result(self, result, index):

        search_result_frame = ttk.Frame(self.search_results_frame)
        
        search_result_frame.config(
            border=1, 
            borderwidth=1,
            relief="solid",
            padding=(16, 8)
        )

        self.search_results_frame.rowconfigure(index, weight=1)
        self.search_results_frame.columnconfigure(0, weight=1)
        search_result_frame.grid(row=index, pady=4)
        search_result_frame.columnconfigure([0,1,2,3], weight=1)
        
        for playlist in result["playlists"]:
            index = int(re.search(r'第(\d+)集', playlist).group(1))
            url = re.search(r'https?://.+', playlist).group()
            r = (index - 1) // 4 + 1
            l = (index - 1) % 4
            ttk.Button(
                search_result_frame, text=index, command=lambda url=url: self.start_download_thread(url)
                ).grid(row=r, column=l)
        
        ttk.Label(
            search_result_frame, text=result["title"], justify="left", font=(self.font_var.get(), 12, "bold")
            ).grid(row=0, column=0, columnspan=4, sticky=NSEW, pady=4)

    def search(self):

        keyword = self.search_var.get()
        results = [
            {
            "title": "无职转生Ⅱ 到了异世界就拿出真本事",
            "imgsrc": "https://tu.modututu.com/upload/vod/20231004-1/04e50b5c5db1da946b95ed7d25f5e2b4.jpg",
            "details": {
                "又名": "無職転生Ⅱ～異世界行ったら本気だす～ / 无职转生：到了异世界就拿出真本事 2 / 無職転生～異世界行ったら本気だす～ Seasons 2",
                "导演": "平野宏树",
                "主演": "内山夕实,杉田智和,白石晴香,小林优,羽多野涉,泽城千春,山本格,鸟海浩辅,上田丽奈,兴津和幸,茅野爱衣",
                "类型": "动画",
                "年份": "2023",
                "地区": "日本",
                "更新时间": "2023-10-04"
            },
            "playlists": [
                "第1集$https://play.modujx10.com/20231003/alqUlRrj/index.m3u8",
                "第2集$https://play.modujx10.com/20231003/mLubTjLo/index.m3u8",
                "第3集$https://play.modujx10.com/20231003/PbqeMYYS/index.m3u8",
                "第4集$https://play.modujx10.com/20231003/cUhwHn9x/index.m3u8",
                "第5集$https://play.modujx10.com/20231003/5c16q7T7/index.m3u8",
                "第6集$https://play.modujx10.com/20231003/MiOZgC1m/index.m3u8",
                "第7集$https://play.modujx10.com/20231003/CXI66Dl5/index.m3u8",
                "第8集$https://play.modujx10.com/20231003/8X6D1nix/index.m3u8",
                "第9集$https://play.modujx10.com/20231003/rok8j2l9/index.m3u8",
                "第10集$https://play.modujx10.com/20231003/Russ6aRl/index.m3u8",
                "第11集$https://play.modujx10.com/20231003/FIWMwhUA/index.m3u8",
                "第12集$https://play.modujx10.com/20231003/qYt8n3QL/index.m3u8",
                "第13集$https://play.modujx10.com/20231003/im6HapTe/index.m3u8"
            ]
          },
          {
            "title": "我的青春恋爱物语果然有问题第三季 完",
            "imgsrc": "https://tu.modututu.com/upload/vod/20230914-1/a9f6ec948ba3fc3e755fcdfec6500d21.jpg",
            "details": {
                "又名": "やはり俺の青春ラブコメはまちがっている。完 / 我的青春恋爱物语果然有问题。完",
                "导演": "及川启",
                "主演": "江口拓也,早见沙织,东山奈央,佐仓绫音,悠木碧,小松未可子,近藤隆,桧山修之,柚木凉香,中原麻衣,井上麻里奈,佐佐木望,小清水亚美,堀井茶渡",
                "类型": "爱情,动画",
                "年份": "2020",
                "地区": "日本",
                "更新时间": "2023-09-14"
            },
            "playlists": [
                "第1集$https://play.modujx10.com/20230913/u9Ogil58/index.m3u8",
                "第2集$https://play.modujx10.com/20230913/cr64iaHp/index.m3u8",
                "第3集$https://play.modujx10.com/20230913/STcR5WPV/index.m3u8",
                "第4集$https://play.modujx10.com/20230913/G68UWWZF/index.m3u8",
                "第5集$https://play.modujx10.com/20230913/xph8QWvq/index.m3u8",
                "第6集$https://play.modujx10.com/20230913/8PwgNvMI/index.m3u8",
                "第7集$https://play.modujx10.com/20230913/v23aXjKA/index.m3u8",
                "第8集$https://play.modujx10.com/20230913/LSVciylD/index.m3u8",
                "第9集$https://play.modujx10.com/20230913/uhr2lfkS/index.m3u8",
                "第10集$https://play.modujx10.com/20230913/OP9GKC5W/index.m3u8",
                "第11集$https://play.modujx10.com/20230913/u0wnjNrm/index.m3u8",
                "第12集$https://play.modujx10.com/20230913/FYYiPAEV/index.m3u8"
            ]
          },
          {
            "title": "文豪野犬第五季",
            "imgsrc": "https://tu.modututu.com/upload/vod/20230923-1/1f30a7e90e5cd9c2ea3c20b36bcbd552.jpg",
            "details": {
                "又名": "文豪ストレイドッグス第5シーズン",
                "导演": "五十岚卓哉",
                "主演": "上村祐翔,宫野真守,细谷佳正,神谷浩史,丰永利行,花仓桔道,岛村侑,诸星堇,小山力也,大塚明夫,小市真琴,石田彰,子安武人,草尾毅,梶裕贵,阿座上洋平,千叶翔也",
                "类型": "动画",
                "年份": "2023",
                "地区": "日本",
                "更新时间": "2023-10-04"
            },
            "playlists": [
                "第1集$https://play.modujx10.com/20230919/EYfHo7kq/index.m3u8",
                "第2集$https://play.modujx10.com/20230919/xzQXHFma/index.m3u8",
                "第3集$https://play.modujx10.com/20230919/hqn2FDLR/index.m3u8",
                "第4集$https://play.modujx10.com/20230919/yWLsEqqF/index.m3u8",
                "第5集$https://play.modujx10.com/20230919/gb54ndEd/index.m3u8",
                "第6集$https://play.modujx10.com/20230919/SioFcoBJ/index.m3u8",
                "第7集$https://play.modujx10.com/20230925/ODBTlz0k/index.m3u8",
                "第8集$https://play.modujx10.com/20230927/AX5LPnCd/index.m3u8",
                "第9集$https://play.modujx10.com/20231003/YMXWeMnL/index.m3u8",
                "第10集$https://play.modujx10.com/20231003/kfhboIhr/index.m3u8",
                "第11集$https://play.modujx10.com/20231003/2NbeC75f/index.m3u8"
            ]
          },
        ]

        for widget in self.search_results_frame.winfo_children():
            widget.destroy()

        self.search_results_canvas.yview_moveto(0)

        for index, result in enumerate(results):
            self.search_result(result, index)

    def start_download_thread(self, url):

        if self.download_thread.is_alive():
            return
        self.download_thread = threading.Thread(target=ModuDownloader.download, args=(url, self.download_thread_var.get()), daemon=True)
        self.download_thread.start()

if __name__ == "__main__":

    # root = Tk()
    # VideoPlayerFrame(root).pack(fill=BOTH, expand=True)
    # root.mainloop()

    app = ModuApp()
    app.run()