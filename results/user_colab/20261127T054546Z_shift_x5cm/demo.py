
import hashlib, json, math, platform
from pathlib import Path
from datetime import datetime, timezone
from importlib.metadata import version
import numpy as np
from PIL import Image, ImageDraw
import pybullet as p
import pybullet_data
out = Path(__file__).parent
started = datetime.now(timezone.utc).isoformat()
p.connect(p.DIRECT)
p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.setGravity(0, 0, -9.81)
p.setTimeStep(1 / 240)
def box(size, xyz, rgb, mass=0):
    shape = p.createCollisionShape(p.GEOM_BOX, halfExtents=size)
    visual = p.createVisualShape(p.GEOM_BOX, halfExtents=size, rgbaColor=[*rgb, 1])
    return p.createMultiBody(mass, shape, visual, basePosition=xyz)
def hand_pose():
    state = p.getLinkState(robot, hand, computeForwardKinematics=True)
    t = np.eye(4)
    t[:3, :3], t[:3, 3] = np.array(p.getMatrixFromQuaternion(state[5])).reshape(3, 3), state[4]
    return t
def look_at(eye, target):
    z = np.array(target) - eye
    z /= np.linalg.norm(z)
    up = [0., 1., 0.] if abs(z[2]) > .95 else [0., 0., 1.]
    x = np.cross(z, up)
    x /= np.linalg.norm(x)
    t = np.eye(4)
    t[:3, :3], t[:3, 3] = np.column_stack([x, np.cross(z, x), z]), eye
    return t
p.loadURDF("plane.urdf")
box([.7, .5, .035], [.35, 0, .60], [.72, .76, .80])
for x in [-.23, .93]:
    for y in [-.4, .4]:
        box([.035, .035, .285], [x, y, .285], [.24, .29, .36])
robot = p.loadURDF("franka_panda/panda.urdf", [-.25, 0, .636], useFixedBase=True)
hand = next(i for i in range(p.getNumJoints(robot)) if p.getJointInfo(robot, i)[12] == b"panda_hand")
joints = [i for i in range(p.getNumJoints(robot)) if p.getJointInfo(robot, i)[2] == p.JOINT_REVOLUTE]
q = np.array([0., -.45, 0., -2.1, 0., 1.8, .78])
for j, value in zip(joints, q):
    p.resetJointState(robot, j, value)
for j in [9, 10]:
    p.resetJointState(robot, j, .04)
    p.setJointMotorControl2(robot, j, p.POSITION_CONTROL, targetPosition=.04, force=20)
for xyz, rgb in [([.30, -.08, .666], [.9, .14, .16]), ([.20, .17, .666], [.12, .4, .95]), ([.45, .13, .666], [.98, .73, .1])]:
    box([.03, .03, .03], xyz, rgb, .05)
p.setJointMotorControlArray(robot, joints, p.POSITION_CONTROL, targetPositions=q, forces=[80] * 7)
for _ in range(120):
    p.stepSimulation()
initial = hand_pose()
mount = np.linalg.inv(initial) @ look_at((initial @ [.08, -.06, .025, 1])[:3], [.31, .06, .65])
external = look_at(np.array([1.22, -1.32, 1.46]), [.20, 0, .89])
projection = p.computeProjectionMatrixFOV(60, 320 / 240, .02, 4)
shift = np.eye(4)
shift[0, 3] = 0.05
labels = ["Wrist baseline", "Wrist +5cm local x"]
images, states = [], []
for frame in range(30):
    phase = 2 * math.pi * frame / 29
    target = q + np.array([.2, .13, .06, .1, .06, .1, .07]) * math.sin(phase)
    p.setJointMotorControlArray(robot, joints, p.POSITION_CONTROL, targetPositions=target, forces=[80] * 7)
    for _ in range(24):
        p.stepSimulation()
    world_hand = hand_pose()
    wrist = world_hand @ mount
    cameras = [wrist, wrist @ shift]
    canvas = Image.new("RGB", (640, 286), "#101c2d")
    draw = ImageDraw.Draw(canvas)
    for i, camera in enumerate(cameras):
        eye, z, up = camera[:3, 3], camera[:3, 2], -camera[:3, 1]
        view = p.computeViewMatrix(eye.tolist(), (eye + z).tolist(), up.tolist())
        rgba = p.getCameraImage(320, 240, view, projection, renderer=p.ER_TINY_RENDERER)[2]
        x, y = i * 320, 0
        canvas.paste(Image.fromarray(np.array(rgba, dtype=np.uint8).reshape(240, 320, 4)[:, :, :3]), (x, y + 24))
        draw.text((x + 8, y + 6), labels[i], fill="white")
    draw.text((8, 269), f"Frame {frame + 1}/30 | Prescribed motion; no VLA or grasp evaluation", fill="white")
    images.append(canvas)
    states.append({"t_s": .5 + (frame + 1) / 10, "q_rad": [p.getJointState(robot, j)[0] for j in joints],
                   "world_from_hand": world_hand.tolist(), "world_from_cameras": [t.tolist() for t in cameras]})
images[0].save(out / "comparison.gif", save_all=True, append_images=images[1:], duration=100, loop=0, disposal=2)
images[10].save(out / "comparison.png")
record = {"status": "completed", "started_at_utc": started, "completed_at_utc": datetime.now(timezone.utc).isoformat(),
          "python": platform.python_version(), "packages": {n: version(n) for n in ["pybullet", "numpy", "Pillow"]},
          "model": "pybullet_data/franka_panda/panda.urdf", "scope": "30-frame wrist mounting comparison; local optical x +0.05 m; same orientation; prescribed motion; no learned policy or grasp evaluation",
          "frame_count": 30, "camera_size": [320, 240], "physics_hz": 240, "gif_duration_ms": 100,
          "camera_convention": "Column vectors; optical x right, y down, z forward; metre units; two fixed wrist mounts; captures share one state",
          "hand_from_camera": mount.tolist(), "hand_from_camera_reference": "baseline",
          "camera_labels": labels,
          "camera_delta_in_baseline_optical_frame": shift.tolist(),
          "hand_from_cameras": [mount.tolist(), (mount @ shift).tolist()],
          "base_script_sha256": "03d2abfb35bd68be8b43d6c80a8730f337c9cf7ba1b93f5110df5accd844f055",
          "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "states": states}
(out / "metadata.json").write_text(json.dumps(record, indent=2))
p.disconnect()
