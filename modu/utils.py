
def update_json_data(json_file, new_data):
    import json

    try:
        # 读取数据
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        data = []
    # 合并数据
    for item in new_data:
        if not item in data:
            data.append(item)
    # 存储数据
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def modify_m3u8_file(file, url):
    """
    file m3u8文件

    url m3u8文件的原始下载链接

    return 输出文件名
    """
    import os, re
    from pathlib import Path
    from urllib.parse import urlparse

    parsed_url = urlparse(url)
    root_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    dir_url = re.split

    with open(file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    ## 修正规则 TODO: 变成可以替换的内容 ##
    skip = False
    modified_lines = []
    for line in lines:
        parsed_line = line.strip()
        if parsed_line == "#EXT-X-DISCONTINUITY" and not skip:
            skip = True
        elif parsed_line == "#EXT-X-DISCONTINUITY" and skip:
            skip = False
        elif parsed_line == "#EXT-X-ENDLIST" and skip:
            skip = False
        elif not skip:
            parsed_line = parsed_line.replace('.jpg', '.ts')
            if parsed_line.startswith("/"):
                new_line = root_url + parsed_line + "\n"
            elif re.match(r"^\d", parsed_line):
                new_line = dir_url + "/" + parsed_line + "\n"
            else:
                new_line = parsed_line + "\n"
            modified_lines.append(new_line)
    ## 修正结束 ##

    backup_file = file + ".bak"
    os.rename(file, backup_file)
    try:
        with open(file, 'w', encoding='utf-8') as f:
            f.writelines(modified_lines)
    except Exception as e:
        os.rename(backup_file, file)
        raise OSError(f"write fault! file: {file}")
    os.remove(backup_file)

    return Path(file)

def extract_random_frames(video_file: str, n: int = 1):
    """
    video_file => 视频文件

    n => 需要截取的帧总数，默认为 1
    
    """
    import os.path
    import random
    import cv2 as cv
    from tqdm import tqdm

    video_file = os.path.normpath(video_file)
    id = os.path.splitext(os.path.basename(video_file))[0]

    cap = cv.VideoCapture(video_file)
    total_frames = int(cap.get(cv.CAP_PROP_FRAME_COUNT))
    fps = int(cap.get(cv.CAP_PROP_FPS))

    # 生成不重复的随机帧号（0-based）
    random_frames = random.sample(range(total_frames), min(n, total_frames))
    random_frames.sort()
    print(f"random frames | {random_frames}")

    extracted_frame_count = 0
    output_dir = "shotcut/" + id

    os.makedirs(output_dir, exist_ok=True)

    with tqdm(total=len(random_frames), desc="extract frame") as pbar:
        for frame_num in random_frames:
            # TODO: 会报错，H.264编码问题，但能正常输出
            cap.set(cv.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = cap.read()
            if not ret:
                break
            filename = f"{id}_{frame_num:06d}.png"
            output_path = os.path.join(output_dir, filename)
            cv.imwrite(output_path, frame) # TODO: cv2库 中文路径会写入失败！
            tqdm.write(f"extract frame | Output: {output_path}")
            extracted_frame_count += 1
            pbar.update(1)

    cap.release()

def convert_video(file: str, output_format: str, output: str | None = None):
    """
    转换视频格式
    """
    import subprocess, os
    from pathlib import Path

    preset = "veryfast"

    base_dir = Path(__file__).parent.parent
    ffmpeg_path = base_dir / "res" / "ffmpeg" / "bin" / "ffmpeg"

    if output is None:
        output = os.path.splitext(file)[0] + output_format

    os.makedirs(os.path.dirname(output), exist_ok=True)

    if os.path.exists(output):
        print(f"{output} existed")
        return

    subprocess.run([ffmpeg_path, '-i', file, "-preset", preset ,output], check=True)

    