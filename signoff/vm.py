"""Run the sign-off tools (Magic, Netgen, KLayout, LibreLane) inside a Linux container.

The tools live in the LibreLane container image, which runs in a Lima virtual machine on
macOS. Files are copied in and out with tar pipes, so nothing has to be mounted. On another
host, replace `sh` and `tool` below with direct calls to the container runtime.

environment
    LIMACTL    path of limactl             (default: the copy shipped with the sibling project)
    LIMA_HOME  Lima home directory         (default: ~/.lima-gpu)
    LIMA_VM    virtual machine name        (default: sram)
    SRAM_IMAGE container image             (default: ghcr.io/librelane/librelane:3.0.17)
"""
import os
import shlex
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIMACTL = os.environ.get("LIMACTL", os.path.join(os.path.dirname(ROOT), "gpu_sky130", "tools", "lima", "bin", "limactl"))
VM = os.environ.get("LIMA_VM", "sram")
IMAGE = os.environ.get("SRAM_IMAGE", "ghcr.io/librelane/librelane:3.0.17")
ENV = dict(os.environ, LIMA_HOME=os.environ.get("LIMA_HOME", os.path.expanduser("~/.lima-gpu")))
REMOTE = "sram"                       # ~/sram inside the VM
PDK_IN_VM = "$(ls -d $HOME/pdk/ciel/sky130/versions/*/sky130A | head -1)"


def sh(cmd, inp=None, check=True, timeout=None):
    """Run a shell command inside the VM."""
    r = subprocess.run([LIMACTL, "shell", "--workdir", "/tmp", VM, "--", "bash", "-lc", cmd],
                       input=inp, capture_output=True, env=ENV, timeout=timeout)
    if check and r.returncode != 0:
        raise RuntimeError(f"VM command failed ({r.returncode}): {cmd}\n{r.stdout.decode()[-3000:]}\n{r.stderr.decode()[-3000:]}")
    return r.stdout.decode(errors="replace") + r.stderr.decode(errors="replace")


def push(local_dir, sub, clean=False):
    """Copy a local directory tree to ~/sram/<sub> in the VM."""
    tar = subprocess.run(["tar", "-C", local_dir, "--exclude", "._*", "-cf", "-", "."], capture_output=True, check=True,
                         env=dict(os.environ, COPYFILE_DISABLE="1")).stdout
    pre = f"rm -rf ~/{REMOTE}/{sub}; " if clean else ""
    sh(f"{pre}mkdir -p ~/{REMOTE}/{sub} && tar -C ~/{REMOTE}/{sub} -xf -", inp=tar)


def pull(sub, local_dir, patterns=("*",)):
    """Copy files matching the patterns from ~/sram/<sub> back to a local directory."""
    os.makedirs(local_dir, exist_ok=True)
    pat = " ".join(patterns)
    r = subprocess.run([LIMACTL, "shell", "--workdir", "/tmp", VM, "--", "bash", "-lc",
                        f"cd ~/{REMOTE}/{sub} && tar -cf - {pat} 2>/dev/null"], capture_output=True, env=ENV)
    subprocess.run(["tar", "-C", local_dir, "-xf", "-"], input=r.stdout, check=False)


def tool(cmd, sub="", timeout=None, check=True):
    """Run a command in the tool container with ~/sram mounted at /work and the PDK at /pdk."""
    inner = f"export PDK_ROOT=/pdkroot PDK=sky130A PDKPATH=/pdkroot/sky130A; cd /work/{sub} && {cmd}"
    full = (f"mkdir -p ~/{REMOTE}/{sub}; nerdctl run --rm -v $HOME/{REMOTE}:/work -v {PDK_IN_VM}:/pdkroot/sky130A:ro "
            f"{IMAGE} bash -c {shlex.quote(inner)}")
    return sh(full, check=check, timeout=timeout)
