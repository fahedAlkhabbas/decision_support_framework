"""Quick check: one feasible deployment on 10 nodes (seed 0)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.user_interface import UserInterface  # noqa: E402

ui = UserInterface()
print("Testing with 10 nodes (seed 0)...")
ok, time_taken, energy, used_nodes = ui.run_deployment_scenario(
    num_nodes=10, objective="feasible", seed=0)
if ok:
    print(f"\nSuccess: time {time_taken:.3f}s, energy {energy}, nodes used {len(used_nodes)}")
else:
    print("\nNo feasible deployment found")
