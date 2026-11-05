"""运行生成的代码，取出它定义的时间线和舞台。"""

import json
import runpy

from .stage import Stage
from .timeline import SceneError, Timeline


def load_scene(path, speech_path=None):
    namespace = runpy.run_path(path)
    timeline = namespace.get("timeline")
    stage = namespace.get("stage")
    if not isinstance(timeline, Timeline):
        raise SceneError("代码必须定义变量 timeline = Timeline(...)")
    if not isinstance(stage, Stage):
        raise SceneError("代码必须定义变量 stage = Stage(timeline)")
    speech = None
    if speech_path:
        with open(speech_path, encoding="utf-8") as handle:
            speech = json.load(handle)
    timeline.compile(speech)
    stage.bind()
    return timeline, stage
