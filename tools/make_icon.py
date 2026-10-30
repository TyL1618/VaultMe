"""
make_icon.py - 產生 VaultMe 全部圖示（桌面 .ico + PWA png + favicon）

設計：深色底 + 青色發光盾牌 + 鑰匙孔，配色同 theme.py 的 Cyberpunk 風格。
用法：python tools/make_icon.py   （產出會直接覆蓋專案內既有圖示）

輸出：
  icon.ico              桌面 exe / 視窗 / 工作列（16~256 多尺寸，圓角透明底）
  docs/icon-192.png     PWA（滿版底，內容在 maskable 安全區內，any/maskable 共用）
  docs/icon-512.png     同上
  docs/apple-touch-icon.png   iOS 主畫面（180，不透明）
  docs/favicon.ico      瀏覽器分頁
"""
import os

from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
N = 1024  # 母圖尺寸，縮小時才不會鋸齒

BG_EDGE = (5, 8, 15)        # #05080f
BG_CENTER = (13, 32, 56)    # 中心稍亮，讓盾牌「浮」出來
PANEL = (9, 15, 26)         # #090f1a
CYAN = (0, 245, 255)        # #00f5ff
BLUE = (26, 111, 255)       # #1a6fff


def bezier(p0, p1, p2, p3, steps=48):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        pts.append((
            u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0],
            u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1],
        ))
    return pts


def shield_points():
    """盾牌外形（1024 座標），內容全落在 maskable 安全區（半徑 ~410）內。"""
    pts = []
    pts += bezier((512, 170), (440, 232), (370, 252), (292, 252))      # 左肩
    pts += [(292, 252), (292, 500)]                                    # 左側
    pts += bezier((292, 500), (292, 690), (400, 780), (512, 852))      # 左下弧
    pts += bezier((512, 852), (624, 780), (732, 690), (732, 500))      # 右下弧
    pts += [(732, 500), (732, 252)]                                    # 右側
    pts += bezier((732, 252), (654, 252), (584, 232), (512, 170))      # 右肩
    return pts


def scale_about(pts, k, cx=512, cy=520):
    return [(cx + (x - cx) * k, cy + (y - cy) * k) for x, y in pts]


def radial_bg():
    """放射狀底色。"""
    bg = Image.new("RGB", (N, N), BG_EDGE)
    center = Image.new("RGB", (N, N), BG_CENTER)
    mask = Image.new("L", (N, N), 0)
    d = ImageDraw.Draw(mask)
    d.ellipse((N * 0.12, N * 0.08, N * 0.88, N * 0.92), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(170))
    return Image.composite(center, bg, mask)


def gradient(size, c1, c2):
    """上 → 下 的線性漸層。"""
    g = Image.new("RGB", (1, size))
    for y in range(size):
        t = y / (size - 1)
        g.putpixel((0, y), tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3)))
    return g.resize((size, size))


def poly_mask(pts):
    m = Image.new("L", (N, N), 0)
    ImageDraw.Draw(m).polygon(pts, fill=255)
    return m


def build_master():
    img = radial_bg().convert("RGBA")

    outer = shield_points()
    outer_mask = poly_mask(outer)

    # 外發光
    glow_mask = outer_mask.filter(ImageFilter.GaussianBlur(46))
    glow = Image.new("RGBA", (N, N), CYAN + (0,))
    glow.putalpha(glow_mask.point(lambda v: int(v * 0.55)))
    img = Image.alpha_composite(img, glow)

    # 盾牌外框（青 → 藍漸層）
    frame = gradient(N, CYAN, BLUE).convert("RGBA")
    frame.putalpha(outer_mask)
    img = Image.alpha_composite(img, frame)

    # 盾牌內板（深色），留出外框粗細
    inner_mask = poly_mask(scale_about(outer, 0.86))
    panel = Image.new("RGBA", (N, N), PANEL + (255,))
    panel.putalpha(inner_mask)
    img = Image.alpha_composite(img, panel)

    # 內板微光，讓鑰匙孔有底
    inner_glow = Image.new("RGBA", (N, N), CYAN + (0,))
    ring = Image.new("L", (N, N), 0)
    ImageDraw.Draw(ring).ellipse((512 - 150, 470 - 150, 512 + 150, 470 + 150), fill=70)
    inner_glow.putalpha(ring.filter(ImageFilter.GaussianBlur(70)))
    img = Image.alpha_composite(img, Image.composite(inner_glow, Image.new("RGBA", (N, N), (0, 0, 0, 0)), inner_mask))

    # 鑰匙孔：圓 + 梯形
    key = Image.new("L", (N, N), 0)
    kd = ImageDraw.Draw(key)
    kd.ellipse((512 - 66, 452 - 66, 512 + 66, 452 + 66), fill=255)
    kd.polygon([(512 - 30, 480), (512 + 30, 480), (512 + 58, 640), (512 - 58, 640)], fill=255)
    kd.rounded_rectangle((512 - 58, 622, 512 + 58, 646), radius=12, fill=255)

    key_glow = Image.new("RGBA", (N, N), CYAN + (0,))
    key_glow.putalpha(key.filter(ImageFilter.GaussianBlur(26)).point(lambda v: int(v * 0.8)))
    img = Image.alpha_composite(img, key_glow)

    key_fill = Image.new("RGBA", (N, N), CYAN + (255,))
    key_fill.putalpha(key)
    img = Image.alpha_composite(img, key_fill)

    return img


def rounded(img, radius_ratio=0.22):
    """圓角透明底（桌面 ico 用）。"""
    m = Image.new("L", img.size, 0)
    r = int(img.size[0] * radius_ratio)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, img.size[0] - 1, img.size[1] - 1), radius=r, fill=255)
    out = img.copy()
    out.putalpha(m)
    return out


def main():
    master = build_master()

    def path(*p):
        return os.path.join(ROOT, *p)

    master_rgb = master.convert("RGB")

    # PWA：滿版不透明（maskable 會被系統裁成圓/圓角，內容在安全區內）
    for s in (192, 512):
        master_rgb.resize((s, s), Image.LANCZOS).save(path("docs", f"icon-{s}.png"), optimize=True)
    master_rgb.resize((180, 180), Image.LANCZOS).save(path("docs", "apple-touch-icon.png"), optimize=True)

    # 桌面 ico：圓角透明，多尺寸
    sizes = [16, 24, 32, 48, 64, 128, 256]
    rounded(master).resize((256, 256), Image.LANCZOS).save(
        path("icon.ico"), format="ICO", sizes=[(s, s) for s in sizes])

    # favicon：16/32/48
    rounded(master).resize((256, 256), Image.LANCZOS).save(
        path("docs", "favicon.ico"), format="ICO", sizes=[(16, 16), (32, 32), (48, 48)])

    # 預覽用母圖（不進版控也無妨）
    print("done")


if __name__ == "__main__":
    main()
