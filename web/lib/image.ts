const MAX_SIDE = 2000;
const JPEG_QUALITY = 0.9;

/** 手机照片通常很大，缩小后转成 JPEG 的 base64。题目文字在这个尺寸下仍然清晰。 */
export async function imageToBase64(file: File): Promise<string> {
  let bitmap: ImageBitmap;
  try {
    bitmap = await createImageBitmap(file);
  } catch {
    throw new Error("这张图片打不开，请换成 JPG、PNG 或 WebP");
  }
  const scale = Math.min(1, MAX_SIDE / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  const context = canvas.getContext("2d");
  if (!context) throw new Error("浏览器无法处理这张图片");
  // 透明背景转 JPEG 会变黑，先铺白底
  context.fillStyle = "#fff";
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close();
  return canvas.toDataURL("image/jpeg", JPEG_QUALITY).split(",")[1];
}
