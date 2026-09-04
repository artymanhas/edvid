"""Generate the overlay noise/grain texture used by the glitch and light-leak
cut transitions (CustomGraphics.tsx). Procedural, no external files/licensing
— same policy as generate_sfx.py, just pixels instead of samples.

Run: uv run python generate_fx.py -> public/fx/noise.png
"""
import pathlib
import numpy as np
from PIL import Image

# Quarter-res of the 1080x1920 frame: the texture is used at low opacity as
# grain/static, so it doesn't need to be full-res — objectFit:cover upscales
# it cleanly and the softness actually reads better as grain than a crisp
# full-res noise field would.
W, H = 540, 960
SEED = 7  # fixed seed: the texture ships as a committed asset, not
# regenerated per render, so it only needs to look right once.

out = pathlib.Path(__file__).parent / "public" / "fx"
out.mkdir(parents=True, exist_ok=True)

rng = np.random.default_rng(SEED)
mono = rng.integers(0, 256, size=(H, W), dtype=np.uint8)
rgb = np.stack([mono, mono, mono], axis=-1)

path = out / "noise.png"
Image.fromarray(rgb, "RGB").save(path)
print("wrote", path, f"{W}x{H}")
