import { Fragment } from "react";

const TAG = /<(sub|sup)>(.*?)<\/\1>/;

/** 只认 <sub> 下标和 <sup> 上标。这里按文本解析，不插入 HTML，模型的输出不能注入脚本。 */
export default function Markup({ text }: { text: string }) {
  // split 带两个捕获组，每 3 段一组：普通文字、标签名、标签里的文字
  const pieces = text.split(TAG);
  const nodes = [];
  for (let index = 0; index < pieces.length; index += 3) {
    nodes.push(<Fragment key={index}>{pieces[index]}</Fragment>);
    if (index + 2 < pieces.length) {
      const Tag = pieces[index + 1] === "sup" ? "sup" : "sub";
      nodes.push(<Tag key={index + 1}>{pieces[index + 2]}</Tag>);
    }
  }
  return <>{nodes}</>;
}
