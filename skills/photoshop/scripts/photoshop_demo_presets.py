"""Visible Photoshop demo presets.

Use this script when the user asks to create an image in Photoshop and wants
to see the process. It runs several small JSX snippets with pauses, so the
Photoshop canvas changes step by step instead of finishing silently.
"""

from __future__ import annotations

import argparse
import math
import os
from pathlib import Path

from photoshop_visible_runner import (
    close_open_documents_without_saving,
    connect_photoshop,
    run_visible_steps,
)


def js_color(name: str, r: int, g: int, b: int) -> str:
    return (
        f"var {name} = new SolidColor();"
        f"{name}.rgb.red = {r};"
        f"{name}.rgb.green = {g};"
        f"{name}.rgb.blue = {b};"
    )


def ellipse_points(cx: float, cy: float, rx: float, ry: float, count: int = 96) -> str:
    pts = []
    for i in range(count):
        a = math.tau * i / count
        pts.append(f"[{cx + math.cos(a) * rx:.1f},{cy + math.sin(a) * ry:.1f}]")
    return "[" + ",".join(pts) + "]"


def heart_points(cx: float, cy: float, scale: float, count: int = 160) -> str:
    pts = []
    for i in range(count):
        t = math.tau * i / count
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append(f"[{cx + x * scale:.1f},{cy - y * scale:.1f}]")
    return "[" + ",".join(pts) + "]"


def fill_polygon(points: str, color_name: str) -> str:
    return (
        "var doc = app.activeDocument;"
        f"doc.selection.select({points});"
        f"doc.selection.fill({color_name});"
        "doc.selection.deselect();"
    )


def add_text(text: str, x: int, y: int, size: int, color_name: str) -> str:
    safe_text = text.replace("\\", "\\\\").replace('"', '\\"')
    return (
        "var doc = app.activeDocument;"
        "var layer = doc.artLayers.add();"
        "layer.kind = LayerKind.TEXT;"
        f'layer.textItem.contents = "{safe_text}";'
        f"layer.textItem.position = [{x},{y}];"
        f"layer.textItem.size = {size};"
        f"layer.textItem.color = {color_name};"
    )


def new_doc(title: str, width: int = 900, height: int = 650) -> str:
    safe_title = title.replace("\\", "\\\\").replace('"', '\\"')
    return (
        "app.documents.add("
        f'{width}, {height}, 72, "{safe_title}", NewDocumentMode.RGB, DocumentFill.WHITE'
        ");"
        "app.preferences.rulerUnits = Units.PIXELS;"
    )


def save_jpeg(path: str) -> str:
    safe_path = path.replace("\\", "\\\\").replace('"', '\\"')
    return (
        "var doc = app.activeDocument;"
        "var opt = new JPEGSaveOptions();"
        "opt.quality = 12;"
        f'doc.saveAs(File("{safe_path}"), opt, true);'
    )


def cartoon_mouse_steps(output: str):
    black = js_color("black", 35, 35, 35)
    gray = js_color("gray", 82, 82, 82)
    face = js_color("face", 245, 216, 178)
    pink = js_color("pink", 255, 154, 178)
    red = js_color("red", 224, 46, 46)
    white = js_color("white", 255, 255, 255)
    return [
        ("new canvas", new_doc("cartoon mouse demo")),
        ("prepare colors", black + gray + face + pink + red + white),
        ("draw ears", fill_polygon(ellipse_points(290, 210, 100, 100), "gray") + fill_polygon(ellipse_points(610, 210, 100, 100), "gray")),
        ("draw inner ears", fill_polygon(ellipse_points(290, 210, 58, 58), "pink") + fill_polygon(ellipse_points(610, 210, 58, 58), "pink")),
        ("draw head", fill_polygon(ellipse_points(450, 330, 160, 150), "gray")),
        ("draw face", fill_polygon(ellipse_points(450, 370, 125, 95), "face")),
        ("draw eyes", fill_polygon(ellipse_points(405, 325, 20, 32), "white") + fill_polygon(ellipse_points(495, 325, 20, 32), "white") + fill_polygon(ellipse_points(405, 333, 8, 12), "black") + fill_polygon(ellipse_points(495, 333, 8, 12), "black")),
        ("draw nose", fill_polygon(ellipse_points(450, 375, 26, 18), "black")),
        ("draw smile", fill_polygon(ellipse_points(450, 430, 58, 14), "red")),
        ("add label", add_text("Photoshop visible demo", 265, 575, 30, "black")),
        ("save jpeg", save_jpeg(output)),
    ]


def heart_steps(output: str):
    red = js_color("red", 218, 35, 62)
    dark = js_color("dark", 70, 30, 40)
    return [
        ("new canvas", new_doc("heart demo")),
        ("prepare colors", red + dark),
        ("draw heart", fill_polygon(heart_points(450, 330, 16), "red")),
        ("add label", add_text("Photoshop Heart Demo", 280, 575, 32, "dark")),
        ("save jpeg", save_jpeg(output)),
    ]


def parking_steps(output: str):
    blue = js_color("blue", 0, 82, 204)
    white = js_color("white", 255, 255, 255)
    dark = js_color("dark", 28, 38, 52)
    frame = "[[210,90],[690,90],[690,570],[210,570]]"
    inner = "[[245,125],[655,125],[655,535],[245,535]]"
    return [
        ("new canvas", new_doc("parking sign demo")),
        ("prepare colors", blue + white + dark),
        ("draw background", fill_polygon(frame, "blue")),
        ("draw inner panel", fill_polygon(inner, "white")),
        ("draw p letter", add_text("P", 360, 435, 310, "blue")),
        ("draw caption", add_text("PARKING", 300, 610, 36, "dark")),
        ("save jpeg", save_jpeg(output)),
    ]


def gamepad_steps(output: str):
    bg = js_color("bg", 30, 30, 50)
    body = js_color("body", 70, 70, 85)
    dark = js_color("dark", 55, 55, 65)
    mid = js_color("mid", 120, 120, 135)
    white = js_color("white", 220, 220, 230)
    yellow = js_color("yellow", 230, 210, 50)
    red = js_color("red", 230, 50, 50)
    green = js_color("green", 50, 210, 50)
    blue = js_color("blue", 50, 100, 230)
    return [
        ("new canvas", new_doc("gamepad demo")),
        ("prepare colors", bg + body + dark + mid + white + yellow + red + green + blue),
        ("draw background", fill_polygon("[[0,0],[900,0],[900,650],[0,650]]", "bg")),
        ("draw main body", fill_polygon(ellipse_points(450, 310, 245, 135), "body")),
        ("draw handles", fill_polygon(ellipse_points(285, 430, 95, 145), "body") + fill_polygon(ellipse_points(615, 430, 95, 145), "body")),
        ("draw shoulder buttons", fill_polygon("[[250,145],[390,145],[390,185],[250,185]]", "mid") + fill_polygon("[[510,145],[650,145],[650,185],[510,185]]", "mid")),
        ("draw d-pad", fill_polygon("[[300,285],[330,285],[330,375],[300,375]]", "dark") + fill_polygon("[[270,315],[360,315],[360,345],[270,345]]", "dark")),
        ("draw joysticks", fill_polygon(ellipse_points(390, 390, 42, 42), "mid") + fill_polygon(ellipse_points(510, 390, 42, 42), "mid") + fill_polygon(ellipse_points(390, 390, 27, 27), "dark") + fill_polygon(ellipse_points(510, 390, 27, 27), "dark")),
        ("draw buttons", fill_polygon(ellipse_points(575, 260, 18, 18), "yellow") + fill_polygon(ellipse_points(625, 310, 18, 18), "red") + fill_polygon(ellipse_points(575, 360, 18, 18), "green") + fill_polygon(ellipse_points(525, 310, 18, 18), "blue")),
        ("draw home button", fill_polygon(ellipse_points(450, 320, 13, 13), "white")),
        ("add label", add_text("Photoshop Gamepad Demo", 285, 590, 30, "white")),
        ("save jpeg", save_jpeg(output)),
    ]


def build_steps(preset: str, output: str):
    if preset == "cartoon_mouse":
        return cartoon_mouse_steps(output)
    if preset == "heart":
        return heart_steps(output)
    if preset == "parking":
        return parking_steps(output)
    if preset == "gamepad":
        return gamepad_steps(output)
    raise ValueError(f"Unknown preset: {preset}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preset", choices=["cartoon_mouse", "heart", "parking", "gamepad"], required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--delay", type=float, default=1.2)
    args = parser.parse_args()

    output = str(Path(args.output).expanduser())
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    if os.path.exists(output):
        os.remove(output)

    ps = connect_photoshop()
    close_open_documents_without_saving(ps)
    results = run_visible_steps(ps, build_steps(args.preset, output), delay=args.delay)
    if not os.path.exists(output):
        raise RuntimeError(f"Photoshop finished but output was not found: {output}")
    print({"ok": True, "output": output, "size": os.path.getsize(output), "steps": results})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
