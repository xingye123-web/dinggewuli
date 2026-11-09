/** 底部横栏，和顶栏呼应。全部灰字，不抢正文。 */
export default function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="site-footer-inner">
        <span className="footer-mark">
          <i aria-hidden="true" />
          定格物理 ©2026
        </span>
        <span className="footer-slogan">停在任意一帧，看清每一个物理量</span>
      </div>
    </footer>
  );
}
