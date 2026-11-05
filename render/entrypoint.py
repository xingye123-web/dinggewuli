"""渲染容器的入口。

协议：从标准输入读一个 JSON 请求，把结果打成 tar 写到标准输出，进度和日志写到标准错误。
不和外部共享任何目录，也不需要网络：配音由外部生成好，随请求传进来。
请求：{"code": "...", "mode": "prepare" 或 "render", "clips": 4,
       "speech": [{"text", "seconds", "clauses"}], "audio": ["每句配音的 base64"]}
结果：result.json，以及成功时的 timeline.json 和 video.mp4。
"""

import base64
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

from scene_check import check_code

HERE = Path(__file__).resolve().parent
WORK_ROOT = os.environ.get("PHYSKIT_WORK_ROOT") or None
WIDTH, HEIGHT = 1920, 1080
FPS = 30
PREPARE_TIMEOUT = 120
RENDER_TIMEOUT = 600
ENCODE_ARGS = [
    "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-pix_fmt", "yuv420p",
    "-g", "15", "-keyint_min", "15", "-sc_threshold", "0", "-movflags", "+faststart",
]


def progress(stage, **fields):
    print(json.dumps({"stage": stage, **fields}, ensure_ascii=False), file=sys.stderr, flush=True)


def child_env(**extra):
    return {**os.environ, "PYTHONPATH": str(HERE), "PYTHONIOENCODING": "utf-8", **extra}


def run_prepare(scene, output, speech_path):
    command = [sys.executable, "-m", "physkit.prepare", str(scene), str(output)]
    if speech_path:
        command.append(str(speech_path))
    completed = subprocess.run(
        command,
        cwd=output,
        env=child_env(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        timeout=PREPARE_TIMEOUT,
    )
    report = output / "prepare.json"
    if not report.exists():
        tail = completed.stderr.decode("utf-8", "replace")[-1500:]
        return {"ok": False, "stage": "scene", "errors": [f"准备阶段崩溃：{tail}"]}
    return json.loads(report.read_text(encoding="utf-8"))


def render_clips(scene, work, unique_count, clips, speech_path):
    """按帧切段并行渲染。每一帧只取决于帧号，所以各段互不依赖。"""
    clips = max(1, min(clips, unique_count))
    # 每段用自己的 media 目录：Manim 的文字缓存不能多进程共用，会读到写了一半的文件
    processes = []
    for k in range(clips):
        env = child_env(
            PHYSKIT_SCENE=str(scene),
            CLIP_FIRST_FRAME=str(unique_count * k // clips),
            CLIP_END_FRAME=str(unique_count * (k + 1) // clips),
        )
        if speech_path:
            env["PHYSKIT_SPEECH"] = str(speech_path)
        media = work / f"clip{k}"
        log = open(work / f"clip{k}.log", "wb")
        command = [
            sys.executable, "-m", "manim", "render",
            "-r", f"{WIDTH},{HEIGHT}", "--fps", str(FPS), "--disable_caching",
            "--progress_bar", "none", "--verbosity", "WARNING", "--media_dir", str(media),
            str(HERE / "physkit" / "manim_entry.py"), "Problem",
        ]
        processes.append((subprocess.Popen(command, cwd=work, env=env, stdout=log, stderr=log), media, log))

    deadline = time.monotonic() + RENDER_TIMEOUT
    outputs = []
    errors = []
    for k, (process, media, log) in enumerate(processes):
        try:
            code = process.wait(timeout=max(deadline - time.monotonic(), 1))
        except subprocess.TimeoutExpired:
            for other, _, _ in processes:
                other.kill()
            return None, [f"渲染超过 {RENDER_TIMEOUT} 秒"]
        log.close()
        found = [p for p in media.rglob("Problem.mp4") if "partial" not in str(p)]
        if code != 0 or not found:
            errors.append((work / f"clip{k}.log").read_text(encoding="utf-8", errors="replace")[-400:])
        else:
            outputs.append(found[0])
        progress("rendering", done=k + 1, total=clips)
    return outputs, errors


def join_clips(clips, work, output):
    listing = work / "clips.txt"
    listing.write_text("".join(f"file '{p.as_posix()}'\n" for p in clips), encoding="utf-8")
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(output)],
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
    )


def expand_frames(unique_video, repeats, output):
    """把不同的画面按次数重复，还原成完整的时间轴。"""
    frame_bytes = WIDTH * HEIGHT * 3 // 2
    decoder = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-i", str(unique_video), "-f", "rawvideo", "-pix_fmt", "yuv420p", "-"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
    )
    encoder = subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "yuv420p",
         "-s", f"{WIDTH}x{HEIGHT}", "-r", str(FPS), "-i", "-", *ENCODE_ARGS, "-an", str(output)],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
    )
    missing = 0
    for repeat in repeats:
        frame = decoder.stdout.read(frame_bytes)
        if len(frame) != frame_bytes:
            missing += 1
            continue
        for _ in range(repeat):
            encoder.stdin.write(frame)
    encoder.stdin.close()
    decoder.stdout.close()
    decoder.wait()
    if encoder.wait() != 0 or missing:
        raise RuntimeError(f"还原时间轴失败，缺少 {missing} 个画面")


def add_narration(silent_video, audio_items, starts, seconds, work, output):
    """把每句配音放到它的开始时间，合成一条音轨。不加音乐和音效。"""
    inputs = []
    filters = []
    labels = []
    for index, (encoded, start) in enumerate(zip(audio_items, starts)):
        path = work / f"speech{index}.mp3"
        path.write_bytes(base64.b64decode(encoded))
        inputs += ["-i", str(path)]
        delay = int(round(start * 1000))
        filters.append(f"[{index + 1}:a]aresample=44100,adelay={delay}:all=1[a{index}]")
        labels.append(f"[a{index}]")
    filters.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0,apad[voice]")
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(silent_video), *inputs,
         "-filter_complex", ";".join(filters), "-map", "0:v", "-map", "[voice]",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-t", f"{seconds:.3f}",
         "-movflags", "+faststart", str(output)],
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
    )


def count_frames(video):
    output = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v", "-count_frames",
         "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(video)],
        check=True,
        capture_output=True,
        text=True,
    )
    return int(output.stdout.strip().split(",")[0])


def handle(request, work):
    code = request["code"]
    problems = check_code(code)
    if problems:
        return {"ok": False, "stage": "check", "errors": problems}

    scene = work / "scene.py"
    scene.write_text(code, encoding="utf-8")
    speech_path = None
    if request.get("speech"):
        speech_path = work / "speech.json"
        speech_path.write_text(json.dumps(request["speech"], ensure_ascii=False), encoding="utf-8")

    progress("preparing")
    prepared = run_prepare(scene, work, speech_path)
    if not prepared["ok"] or request.get("mode") == "prepare":
        return prepared

    started = time.monotonic()
    repeats = prepared["repeats"]
    clip_count = int(request.get("clips", 4))
    progress("rendering", done=0, total=clip_count, unique_frames=len(repeats))
    clips, errors = render_clips(scene, work, len(repeats), clip_count, speech_path)
    if errors:
        return {"ok": False, "stage": "render", "errors": errors}
    render_seconds = time.monotonic() - started

    progress("encoding")
    unique_video = work / "unique.mp4"
    join_clips(clips, work, unique_video)
    silent = work / "silent.mp4"
    expand_frames(unique_video, repeats, silent)
    video = work / "video.mp4"
    if request.get("audio"):
        add_narration(silent, request["audio"], prepared["starts"], prepared["seconds"], work, video)
    else:
        silent.replace(video)

    frames = count_frames(video)
    if frames != prepared["frames"]:
        # 帧号错位会让面板读数和画面对不上，宁可失败
        return {"ok": False, "stage": "render", "errors": [f"视频有 {frames} 帧，时间线有 {prepared['frames']} 帧"]}
    return {
        **prepared,
        "repeats": None,
        "unique_frames": len(repeats),
        "render_seconds": round(render_seconds, 1),
        "total_container_seconds": round(time.monotonic() - started, 1),
        "video_frames": frames,
    }


def main():
    request = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    with tempfile.TemporaryDirectory(dir=WORK_ROOT, ignore_cleanup_errors=True) as directory:
        work = Path(directory)
        try:
            result = handle(request, work)
        except subprocess.TimeoutExpired as error:
            result = {"ok": False, "stage": "timeout", "errors": [f"运行超时：{error.timeout} 秒"]}
        except subprocess.CalledProcessError as error:
            result = {"ok": False, "stage": "encode", "errors": [f"{error.cmd[0]} 退出码 {error.returncode}"]}
        except RuntimeError as error:
            result = {"ok": False, "stage": "encode", "errors": [str(error)[:400]]}
        (work / "result.json").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        with tarfile.open(fileobj=sys.stdout.buffer, mode="w|") as archive:
            for name in ("result.json", "timeline.json", "video.mp4"):
                if (work / name).exists() and (name == "result.json" or result.get("ok")):
                    archive.add(work / name, arcname=name)
        sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
