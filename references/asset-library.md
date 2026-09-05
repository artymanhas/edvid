# Asset library — sourced music & SFX

Files Eduardo downloaded himself (Pixabay, Mixkit, YouTube Audio Library, a
client's own folder, etc.) — **not** code-generated, so each row must carry
where it came from and under what license, unlike `generate_sfx.py`'s pack
(which needs none of that, see `shortform.md`'s SFX table).

**Read this file before generating a new SFX or asking to search Freesound —
something already sourced here that fits the mood may save the trip.**

Registered via `helpers/register_asset.py` (measures duration + peak dB,
copies the file into the right folder, appends the row below — never hand-edit
the numbers, they come from ffmpeg).

Folders:
- `assets/shortform/public/music/` — background tracks
- `assets/shortform/public/sfx_sourced/` — one-off downloaded SFX (real/complex
  sounds a DSP synth can't fake well — see `generate_sfx.py`'s docstring for
  the line on why the generated pack stays code-only)

## Music

| File | Duração | Pico | Clima / uso | Fonte | Licença |
|---|---|---|---|---|---|
| upbeat-pop-fashion-store-575759.mp3 | 38.40s | -0.6 dB | animado, pop instrumental leve, loja de moda, promo/oferta -- fonte original 38.4s, cortar/fade por video | https://freesound.org/people/code_box/sounds/575759/ | CC0 |

## SFX

| File | Duração | Pico | Quando usar | Fonte | Licença |
|---|---|---|---|---|---|
| whoosh-transition-1-fs427823.mp3 | 0.80s | -5.0 dB | whoosh curto, bom pra transicao de corte ou entrada de card | https://freesound.org/people/Kinoton/sounds/427823/ | CC0 |
