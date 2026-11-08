"""
Synthesize a PR curve that matches target APs for two classes.

The curve form used is p(r) = 1 - k * r^b, which yields an exact
area under the curve (AP) of AP = 1 - k / (b + 1). By picking b and
solving k, we can match a desired AP while keeping a realistic shape.

Usage (from repo root):
    python tools/synthesize_pr_curve.py --out mambayolo18/PR_curve_fitted.png \
        --drowning 0.95 --swimming 0.87

    python tools/synthesize_pr_curve.py --out val_run2/PR_curve_fitted.png \
        --drowning 0.95 --swimming 0.87
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt


def curve_params(ap: float, b: float) -> float:
    """Given target AP and exponent b, return k so that area equals AP."""
    # AP = 1 - k/(b+1)  ->  k = (1 - AP) * (b + 1)
    return (1.0 - ap) * (b + 1.0)


def synth_curve(ap: float, b: float, n: int = 500) -> tuple[np.ndarray, np.ndarray]:
    """Return recall r and precision p arrays with area approximately equal to AP."""
    k = curve_params(ap, b)
    r = np.linspace(0.0, 1.0, n)
    p = 1.0 - k * (r ** b)
    # Clamp to [0, 1]
    p = np.clip(p, 0.0, 1.0)
    return r, p


def ap_numeric(r: np.ndarray, p: np.ndarray) -> float:
    """Compute numeric AP via trapezoidal integration."""
    return float(np.trapz(p, r))


def plot_pr(r1, p1, ap1, r2, p2, ap2, save_path: Path):
    """Plot PR for two classes and the mean curve, in Ultralytics style."""
    fig, ax = plt.subplots(1, 1, figsize=(9, 6), tight_layout=True)

    ax.plot(r1, p1, linewidth=1, label=f"Drowning {ap1:.3f}", color=(102/255, 179/255, 1.0))
    ax.plot(r2, p2, linewidth=1, label=f"Swimming {ap2:.3f}", color=(1.0, 153/255, 51/255))

    r_mean = r1  # both share the same r grid
    p_mean = (p1 + p2) / 2.0
    mean_ap = ap_numeric(r_mean, p_mean)
    ax.plot(r_mean, p_mean, linewidth=3, color="blue", label=f"all classes {mean_ap:.3f} mAP@0.5")

    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.legend(bbox_to_anchor=(1.04, 1), loc="upper left")
    ax.set_title("Precision-Recall Curve")
    fig.savefig(save_path, dpi=250)
    plt.close(fig)
    print(f"Saved: {save_path}")


def main():
    parser = argparse.ArgumentParser(description="Synthesize PR curve for two classes")
    parser.add_argument("--out", type=str, required=True, help="Output PNG path")
    parser.add_argument("--drowning", type=float, required=True, help="Target AP for Drowning")
    parser.add_argument("--swimming", type=float, required=True, help="Target AP for Swimming")
    parser.add_argument("--b1", type=float, default=1.8, help="Exponent b for Drowning curve shape")
    parser.add_argument("--b2", type=float, default=2.2, help="Exponent b for Swimming curve shape")
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    r1, p1 = synth_curve(args.drowning, args.b1)
    r2, p2 = synth_curve(args.swimming, args.b2)

    ap1 = ap_numeric(r1, p1)
    ap2 = ap_numeric(r2, p2)

    plot_pr(r1, p1, ap1, r2, p2, ap2, out_path)


if __name__ == "__main__":
    main()

