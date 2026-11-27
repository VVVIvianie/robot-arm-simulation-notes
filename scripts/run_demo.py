#!/usr/bin/env python3
"""Run a small, real PyBullet camera-observation demo on a CPU.

Uses the Franka Panda model shipped with pybullet_data. Motion is prescribed
joint-position control, not a learned policy or a successful grasping trial.
The wrist camera is aimed once at setup and then remains rigidly attached.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib import metadata as package_metadata
import json
import math
from pathlib import Path
import platform
import shlex
import subprocess
import sys
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import pybullet as p
import pybullet_data


CAMERA_NAMES = ("external", "wrist_baseline", "wrist_tx_plus_5cm", "wrist_ry_plus_15deg")
PANEL_LABELS = ("Fixed external camera", "Wrist camera: original mount",
                "Wrist mount: local x +5 cm", "Wrist mount: local y +15 deg")


def transform(position, quaternion):
    matrix = np.eye(4)
    matrix[:3, :3] = np.asarray(p.getMatrixFromQuaternion(quaternion)).reshape(3, 3)
    matrix[:3, 3] = position
    return matrix


def look_at_optical(eye, target):
    """World-from-optical pose: optical x right, y down, z forward."""
    eye, target = np.asarray(eye, dtype=float), np.asarray(target, dtype=float)
    forward = target - eye
    forward /= np.linalg.norm(forward)
    up = np.array([0.0, 0.0, 1.0])
    if abs(np.dot(forward, up)) > 0.95:
        up = np.array([0.0, 1.0, 0.0])
    right = np.cross(forward, up)
    right /= np.linalg.norm(right)
    down = np.cross(forward, right)
    matrix = np.eye(4)
    matrix[:3, :3] = np.column_stack([right, down, forward])
    matrix[:3, 3] = eye
    return matrix


def box(half_extents, position, color, mass=0.0):
    shape = p.createCollisionShape(p.GEOM_BOX, halfExtents=half_extents)
    visual = p.createVisualShape(p.GEOM_BOX, halfExtents=half_extents, rgbaColor=color)
    return p.createMultiBody(baseMass=mass, baseCollisionShapeIndex=shape,
                             baseVisualShapeIndex=visual, basePosition=position)


def get_link_transform(robot, link):
    state = p.getLinkState(robot, link, computeForwardKinematics=True)
    # [4:6] are the world URDF link frame, not the centre-of-mass frame.
    return transform(state[4], state[5])


def capture(camera_pose, projection, width, height, target_ids):
    eye = camera_pose[:3, 3]
    forward = camera_pose[:3, 2]
    # OpenGL view up is negative optical y.
    up = -camera_pose[:3, 1]
    view = p.computeViewMatrix(eye.tolist(), (eye + forward).tolist(), up.tolist())
    result = p.getCameraImage(width, height, viewMatrix=view,
                             projectionMatrix=projection,
                             renderer=p.ER_TINY_RENDERER,
                             flags=p.ER_SEGMENTATION_MASK_OBJECT_AND_LINKINDEX,
                             lightDirection=[-1, -1, 3], shadow=1)
    pixels = np.asarray(result[2], dtype=np.uint8).reshape(height, width, 4)
    segmentation = np.asarray(result[4], dtype=np.int64).reshape(height, width)
    object_ids = segmentation & ((1 << 24) - 1)
    visible = {name: int(np.count_nonzero((segmentation >= 0) & (object_ids == body_id)))
               for name, body_id in target_ids.items()}
    return Image.fromarray(pixels[:, :, :3]), visible


def font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def comparison(images, frame_index, count, simulated_time):
    width, height = images[0].size
    label_height, footer_height = 32, 44
    canvas = Image.new("RGB", (width * 2, (height + label_height) * 2 + footer_height), "#101c2d")
    draw = ImageDraw.Draw(canvas)
    for index, (picture, label) in enumerate(zip(images, PANEL_LABELS)):
        x = (index % 2) * width
        y = (index // 2) * (height + label_height)
        canvas.paste(picture, (x, y + label_height))
        draw.text((x + 10, y + 8), label, font=font(14), fill="#f4f7fc")
    y = (height + label_height) * 2
    draw.text((10, y + 5), f"Same state in all four views | frame {frame_index + 1}/{count} | sim t={simulated_time:.2f}s",
              font=font(13), fill="#f4f7fc")
    draw.text((10, y + 24), "PyBullet CPU rendering | Prescribed motion; no VLA or grasp evaluation",
              font=font(12), fill="#bfcadd")
    return canvas


def version(name):
    try:
        return package_metadata.version(name)
    except package_metadata.PackageNotFoundError:
        return "unknown"


def git_state(root):
    try:
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.DEVNULL).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True))
        return {"head": head, "working_tree_dirty": dirty,
                "note": "The script SHA256 below identifies executed code even if this tree was dirty."}
    except (OSError, subprocess.CalledProcessError):
        return {"head": None, "working_tree_dirty": None}


def run(args):
    started = datetime.now(timezone.utc)
    run_dir = args.output / started.strftime("run_%Y%m%dT%H%M%S_%fZ")
    run_dir.mkdir(parents=True, exist_ok=False)
    script = Path(__file__).resolve()
    script_hash = hashlib.sha256(script.read_bytes()).hexdigest()
    vcs = git_state(script.parent.parent)
    client = p.connect(p.GUI if args.gui else p.DIRECT)
    if client < 0:
        raise RuntimeError("PyBullet connection failed. Try again without --gui for CPU image output.")
    physics_hz = 240
    steps_per_frame = max(1, round(physics_hz / args.fps))
    # GIF stores duration in centiseconds. Record the value that is really saved.
    gif_duration_ms = max(10, round(1000 / args.fps / 10) * 10)
    try:
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setGravity(0, 0, -9.81)
        p.setTimeStep(1.0 / physics_hz)
        p.setPhysicsEngineParameter(numSolverIterations=80, deterministicOverlappingPairs=1)
        p.loadURDF("plane.urdf")
        box([0.7, 0.5, 0.035], [0.35, 0, 0.60], [0.72, 0.76, 0.80, 1])
        for x in [-0.23, 0.93]:
            for y in [-0.40, 0.40]:
                box([0.035, 0.035, 0.285], [x, y, 0.285], [0.24, 0.29, 0.36, 1])
        robot = p.loadURDF("franka_panda/panda.urdf", [-0.25, 0, 0.636], useFixedBase=True)
        joints = [index for index in range(p.getNumJoints(robot))
                  if p.getJointInfo(robot, index)[1].decode().startswith("panda_joint")
                  and p.getJointInfo(robot, index)[2] == p.JOINT_REVOLUTE]
        links = {p.getJointInfo(robot, index)[12].decode(): index
                 for index in range(p.getNumJoints(robot))}
        hand_link = links["panda_hand"]
        initial_joints = np.array([0.0, -0.45, 0.0, -2.10, 0.0, 1.80, 0.78])
        for joint, value in zip(joints, initial_joints):
            p.resetJointState(robot, joint, float(value))
        for index in range(p.getNumJoints(robot)):
            if p.getJointInfo(robot, index)[2] == p.JOINT_PRISMATIC:
                p.resetJointState(robot, index, 0.04)
                p.setJointMotorControl2(robot, index, p.POSITION_CONTROL, targetPosition=0.04, force=20)
        targets = {
            "red_cube": box([0.030, 0.030, 0.030], [0.30, -0.08, 0.666], [0.90, 0.14, 0.16, 1], 0.05),
            "blue_cube": box([0.025, 0.025, 0.025], [0.20, 0.17, 0.661], [0.12, 0.40, 0.95, 1], 0.05),
            "yellow_cube": box([0.035, 0.035, 0.035], [0.45, 0.13, 0.671], [0.98, 0.73, 0.10, 1], 0.05),
        }
        p.setJointMotorControlArray(robot, joints, p.POSITION_CONTROL,
                                    targetPositions=initial_joints.tolist(), forces=[80] * 7)
        for _ in range(120):
            p.stepSimulation()
        initial_hand = get_link_transform(robot, hand_link)
        # Aim once, then freeze the E<-C mounting transform for the entire run.
        eye = (initial_hand @ np.array([0.08, -0.06, 0.025, 1.0]))[:3]
        initial_camera = look_at_optical(eye, [0.31, 0.06, 0.65])
        mount = np.linalg.inv(initial_hand) @ initial_camera
        delta_translation = np.eye(4)
        delta_translation[0, 3] = 0.05
        angle = math.radians(15)
        delta_rotation = np.eye(4)
        delta_rotation[:3, :3] = [[math.cos(angle), 0, math.sin(angle)], [0, 1, 0],
                                  [-math.sin(angle), 0, math.cos(angle)]]
        external = look_at_optical([1.22, -1.32, 1.46], [0.20, 0, 0.89])
        projection = p.computeProjectionMatrixFOV(fov=60, aspect=args.width / args.height,
                                                  nearVal=0.02, farVal=4.0)
        if args.gui:
            p.resetDebugVisualizerCamera(cameraDistance=1.75, cameraYaw=42, cameraPitch=-28,
                                          cameraTargetPosition=[0.2, 0, 0.9])
            print("GUI open. Close the PyBullet window to exit; images are also saved to the run folder.")
        frames, records = [], []
        snapshot_index = args.frames // 3
        for frame_index in range(args.frames):
            if not p.isConnected(client):
                raise RuntimeError("GUI closed before the run completed; no completed-run claim was saved.")
            frame_started = time.monotonic()
            phase = 2 * math.pi * frame_index / (args.frames - 1)
            offset = np.array([0.20 * math.sin(phase), 0.13 * math.sin(phase),
                               0.06 * math.sin(phase), 0.10 * math.sin(phase + 0.4),
                               0.06 * math.sin(phase), 0.10 * math.sin(phase), 0.07 * math.sin(phase)])
            p.setJointMotorControlArray(robot, joints, p.POSITION_CONTROL,
                                        targetPositions=(initial_joints + offset).tolist(), forces=[80] * 7)
            for _ in range(steps_per_frame):
                p.stepSimulation()
            world_hand = get_link_transform(robot, hand_link)
            wrist = world_hand @ mount
            poses = [external, wrist, wrist @ delta_translation, wrist @ delta_rotation]
            pictures, visibility = [], {}
            # No simulation step occurs between these captures: they share one state.
            for name, pose in zip(CAMERA_NAMES, poses):
                picture, counts = capture(pose, projection, args.width, args.height, targets)
                pictures.append(picture)
                visibility[name] = counts
            simulated_time = (120 + (frame_index + 1) * steps_per_frame) / physics_hz
            combined = comparison(pictures, frame_index, args.frames, simulated_time)
            frames.append(combined)
            records.append({"frame": frame_index, "simulation_time_s": simulated_time,
                            "joint_positions_rad": [p.getJointState(robot, j)[0] for j in joints],
                            "world_from_hand": world_hand.tolist(),
                            "world_from_optical_camera": {name: pose.tolist() for name, pose in zip(CAMERA_NAMES, poses)},
                            "visible_target_pixels": visibility})
            if frame_index == snapshot_index:
                combined.save(run_dir / "comparison.png")
                for name, picture in zip(CAMERA_NAMES, pictures):
                    picture.save(run_dir / f"{name}.png")
            if args.gui:
                time.sleep(max(0, 1 / args.fps - (time.monotonic() - frame_started)))
        frames[0].save(run_dir / "comparison.gif", save_all=True, append_images=frames[1:],
                       duration=gif_duration_ms, loop=0, optimize=False, disposal=2)
        fy = (args.height / 2) / math.tan(math.radians(60) / 2)
        report = {
            "status": "completed", "started_at_utc": started.isoformat(),
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            "scope": "CPU physics simulation and paired camera observations with prescribed joint motion.",
            "not_evaluated": ["learned VLA policy", "grasping success", "task success rate", "research hypothesis"],
            "runtime": {"python": platform.python_version(), "platform": platform.platform(),
                        "pybullet": version("pybullet"), "numpy": version("numpy"), "Pillow": version("Pillow"),
                        "connection": "GUI" if args.gui else "DIRECT", "renderer": "ER_TINY_RENDERER"},
            "command": shlex.join([sys.executable, *sys.argv]), "script_sha256": script_hash,
            "git": vcs, "seed": args.seed,
            "seed_note": "Scene and trajectory are deterministic; no random sampling is performed.",
            "robot_model": "pybullet_data/franka_panda/panda.urdf", "wrist_link": "panda_hand",
            "control": "POSITION_CONTROL with sinusoidal prescribed joint targets",
            "physics_hz": physics_hz, "warmup_steps": 120, "steps_per_frame": steps_per_frame,
            "frame_count": len(frames), "requested_playback_fps": args.fps,
            "gif_frame_duration_ms": gif_duration_ms,
            "actual_gif_playback_fps": 1000 / gif_duration_ms, "snapshot_frame": snapshot_index,
            "camera": {"width": args.width, "height": args.height, "vertical_fov_deg": 60,
                       "near_m": 0.02, "far_m": 4.0,
                       "intrinsics_pixel_centres": [[fy, 0, (args.width - 1) / 2],
                                                     [0, fy, (args.height - 1) / 2], [0, 0, 1]],
                       "convention": "Column vectors; T_A_B maps B to A; metres; optical x right, y down, z forward.",
                       "view_conversion": "OpenGL view forward = optical +z; up = optical -y.",
                       "hand_from_baseline_camera": mount.tolist(),
                       "translation_delta_local": delta_translation.tolist(),
                       "rotation_delta_local": delta_rotation.tolist(),
                       "composition": "T_world_C = T_world_hand @ T_hand_C @ Delta_local",
                       "synchronization": "All four views rendered without intervening physics steps."},
            "outputs": ["comparison.gif", "comparison.png", *[f"{name}.png" for name in CAMERA_NAMES]],
            "frames": records,
        }
        (run_dir / "metadata.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"Completed {len(frames)} simulated observation frames.")
        print(f"Output: {run_dir.resolve()}")
        print("Open comparison.gif for motion, comparison.png for the four-view snapshot, metadata.json for evidence.")
        if args.gui and args.keep_open:
            print("Run saved. Close the PyBullet window to finish.")
            while p.isConnected(client):
                time.sleep(0.1)
        return run_dir
    except Exception as exc:
        (run_dir / "error.json").write_text(json.dumps({"status": "failed", "error": str(exc),
                                                        "script_sha256": script_hash}, indent=2) + "\n")
        raise
    finally:
        if p.isConnected(client):
            p.disconnect(client)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results/demo"), help="Parent folder; every run gets a new timestamped directory.")
    parser.add_argument("--gui", action="store_true", help="Also open the local PyBullet 3D window.")
    parser.add_argument("--keep-open", action="store_true", help="With --gui, keep the window open after saving.")
    parser.add_argument("--frames", type=int, default=64)
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--width", type=int, default=360)
    parser.add_argument("--height", type=int, default=280)
    parser.add_argument("--seed", type=int, default=7, help="Recorded identifier; this demo does not sample randomness.")
    args = parser.parse_args()
    if not (2 <= args.frames <= 600 and 1 <= args.fps <= 60 and 160 <= args.width <= 1920 and 120 <= args.height <= 1080):
        parser.error("Require frames 2..600, fps 1..60, width 160..1920 and height 120..1080.")
    if args.keep_open and not args.gui:
        parser.error("--keep-open requires --gui.")
    run(args)


if __name__ == "__main__":
    main()
