import logging
from typing import List, Tuple
from backend.app.services.clip_generation.schemas import ConversionMode, normalize_conversion_mode

logger = logging.getLogger("clipsly.clip_generation.filtergraphs")


def build_filtergraph(
    conversion_mode: str,
    target_width: int = 1080,
    target_height: int = 1920,
    background_color: str = "black",
) -> Tuple[str, str]:
    """Generates the appropriate FFmpeg filtergraph string and output label for the requested conversion mode.

    Returns:
        (filtergraph_string, output_map_label) e.g. ("[0:v]...[outv]", "[outv]")
    """
    mode = normalize_conversion_mode(conversion_mode)
    w = target_width
    h = target_height

    if mode == ConversionMode.BLUR_PAD.value:
        # Mode A: Blurred Background (Default)
        # Background: scaled to cover 1080x1920, cropped to bounds, blurred heavily via boxblur
        # Foreground: scaled to fit within bounds preserving aspect ratio
        # Composition: foreground overlaid centered on blurred background
        filter_str = (
            f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h},boxblur=25:5,setsar=1[bg];"
            f"[0:v]scale={w}:{h}:force_original_aspect_ratio=decrease,setsar=1[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[outv]"
        )
        return filter_str, "[outv]"

    elif mode == ConversionMode.CROP_CENTER.value:
        # Mode B: Center Crop
        # Scaled to fill 1080x1920 canvas, central portion cropped
        filter_str = (
            f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h}:(in_w-{w})/2:(in_h-{h})/2,setsar=1[outv]"
        )
        return filter_str, "[outv]"

    elif mode == ConversionMode.FIT_LETTERBOX.value:
        # Mode C: Fit Letterbox / Solid Color Background
        # Scaled to fit within 1080x1920, padded with solid color (black)
        filter_str = (
            f"[0:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:({w}-iw)/2:({h}-ih)/2:color={background_color},setsar=1[outv]"
        )
        return filter_str, "[outv]"

    else:
        # Fallback to Mode A
        return build_filtergraph(ConversionMode.BLUR_PAD.value, w, h, background_color)


def get_filter_args(
    conversion_mode: str,
    target_width: int = 1080,
    target_height: int = 1920,
    background_color: str = "black",
) -> List[str]:
    """Returns the FFmpeg command-line filter arguments and output stream mapping."""
    filtergraph, out_label = build_filtergraph(
        conversion_mode=conversion_mode,
        target_width=target_width,
        target_height=target_height,
        background_color=background_color,
    )
    return ["-filter_complex", filtergraph, "-map", out_label]
