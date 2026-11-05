import { Fragment } from "react";

/** 模型写的符号里只允许 <sub> 下标。这里按文本解析，不插入 HTML，模型的输出不能注入脚本。 */
export default function Markup({ text }: { text: string }) {
  const pieces = text.split(/<sub>(.*?)<\/sub>/);
  return (
    <>
      {pieces.map((piece, index) =>
        index % 2 === 1 ? <sub key={index}>{piece}</sub> : <Fragment key={index}>{piece}</Fragment>,
      )}
    </>
  );
}
