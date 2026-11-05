"""渲染前的准备：运行生成的代码，算出时间线，检查布局。

用法：python -m physkit.prepare scene.py 输出目录 [speech.json]
"""

import json
import sys
import traceback
from pathlib import Path

from .loader import load_scene
from .timeline import SceneError


def _scene_traceback(scene_path):
    """只保留生成代码里的行，模型据此修改，也不泄露内部路径。"""
    lines = []
    for item in traceback.extract_tb(sys.exc_info()[2]):
        if Path(item.filename).name == Path(scene_path).name:
            lines.append(f"第 {item.lineno} 行：{item.line}")
    error = sys.exc_info()[1]
    lines.append(f"{type(error).__name__}: {error}")
    return "\n".join(lines)


def prepare(scene_path, output_dir, speech_path=None):
    output = Path(output_dir)
    result = {"ok": False, "stage": "scene", "errors": []}
    try:
        timeline, stage = load_scene(scene_path, speech_path)
        problems = stage.lint()
        if problems:
            result.update(stage="layout", errors=problems[:12])
        else:
            (output / "timeline.json").write_text(
                json.dumps(timeline.export(stage), ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
            )
            _, repeats = timeline.unique_frames()
            result.update(
                ok=True,
                frames=timeline.frame_count,
                seconds=timeline.duration,
                repeats=repeats,
                narration=[line["text"] for line in timeline.lines],
                starts=[line["start"] for line in timeline.lines],
                answers=timeline.answer_values(),
            )
    except SceneError as error:
        result["errors"] = [str(error)]
    except Exception:
        result["errors"] = [_scene_traceback(scene_path)]
    (output / "prepare.json").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return result


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    report = prepare(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    print(json.dumps({k: v for k, v in report.items() if k != "repeats"}, ensure_ascii=False, indent=1))
