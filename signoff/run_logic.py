"""Run every logic simulation in the tool container and keep the result lines (out/logic_sim.txt).

    python -m signoff.run_logic

1. periphery RTL + switch-level array model
2. final gate-level netlist + switch-level array model
3. behavioural model of the macro (release/sram_64x32.v)
4. March C- self-test with a good and a faulty memory
"""
import os
import shutil
import tempfile

from signoff import vm
from sram.report import FLOW_TAG

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run():
    nl = os.path.join(ROOT, "flow", "runs", FLOW_TAG, "final", "nl", "sram_64x32.nl.v")
    with tempfile.TemporaryDirectory() as d:
        shutil.copytree(os.path.join(ROOT, "rtl"), d + "/rtl")
        shutil.copytree(os.path.join(ROOT, "tb"), d + "/tb", ignore=shutil.ignore_patterns("work"))
        shutil.copytree(os.path.join(ROOT, "example"), d + "/example", ignore=shutil.ignore_patterns("runs", "*.log"))
        os.makedirs(d + "/release")
        shutil.copy(os.path.join(ROOT, "release", "sram_64x32.v"), d + "/release")
        shutil.copy(nl, d + "/tb/")
        vm.push(d, "logic", clean=True)
    jobs = [
        ("periphery RTL + array model", "sh tb/run_rtl.sh"),
        ("final gate-level netlist + array model", "sh tb/run_gl.sh sram_64x32.nl.v"),
        ("behavioural model", "iverilog -g2012 -o /tmp/b.vvp release/sram_64x32.v tb/tb_sram.v && vvp /tmp/b.vvp"),
        ("March C- self-test (good and faulty memory)",
         "iverilog -g2012 -o /tmp/t.vvp release/sram_64x32.v example/sram_bist.v example/sram_bist_top.v example/tb_bist.v && vvp /tmp/t.vvp"),
    ]
    out = []
    for name, cmd in jobs:
        log = vm.tool(cmd + " 2>&1 | grep -E 'RESULT|PASS|FAIL|ERROR|memory:' | head -8", "logic", check=False, timeout=3600)
        lines = [l for l in log.splitlines() if l.strip() and "level=warning" not in l]
        out.append(f"== {name}\n" + "\n".join(lines))
        print(out[-1])
    open(os.path.join(ROOT, "out", "logic_sim.txt"), "w").write("\n\n".join(out) + "\n")


if __name__ == "__main__":
    run()
