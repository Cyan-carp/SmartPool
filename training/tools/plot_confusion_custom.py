import argparse
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns


def build_matrix(
    drown_diag: float,
    drown_to_swim: float,
    swim_diag: float,
    swim_to_drown: float,
    bg_to_drown: float,
    bg_to_swim: float,
):
    """
    Build a 3x3 normalized confusion matrix for classes:
    columns (True): [Drowning, Swimming, background]
    rows (Predicted): [Drowning, Swimming, background]

    - Column sums must be 1.0.
    - Bottom-right (predicted background vs true background) is 0 by convention.
    """

    # compute remaining proportions for miss/false negative per true class
    drown_to_bg = max(0.0, 1.0 - (drown_diag + drown_to_swim))
    swim_to_bg = max(0.0, 1.0 - (swim_diag + swim_to_drown))

    # background column must sum to 1 across predicted classes (excluding bottom-right)
    bg_pred_bg = 0.0
    # normalize background column if user values don't sum to 1
    bg_sum = bg_to_drown + bg_to_swim + bg_pred_bg
    if bg_sum <= 0:
        bg_to_drown, bg_to_swim = 0.5, 0.5
        bg_sum = 1.0
    bg_to_drown /= bg_sum
    bg_to_swim /= bg_sum

    mat = np.array(
        [
            # predicted Drowning row
            [drown_diag, swim_to_drown, bg_to_drown],
            # predicted Swimming row
            [drown_to_swim, swim_diag, bg_to_swim],
            # predicted background row (misses for true objects; 0 for true background)
            [drown_to_bg, swim_to_bg, bg_pred_bg],
        ]
    )

    # ensure each column sums to 1 within tolerance
    col_sums = mat.sum(axis=0)
    if not np.allclose(col_sums, np.array([1.0, 1.0, 1.0]), atol=1e-6):
        raise ValueError(
            f"Columns must sum to 1. Got sums: {col_sums.tolist()} (Drowning, Swimming, background)"
        )

    return mat


def plot_confusion(mat: np.ndarray, out_path: str):
    labels_true = ["Drowning", "Swimming", "background"]
    labels_pred = ["Drowning", "Swimming", "background"]

    plt.figure(figsize=(10, 7.5))
    ax = sns.heatmap(
        mat,
        annot=True,
        fmt=".2f",
        cmap="Blues",
        vmin=0.0,
        vmax=0.9,
        cbar=True,
        xticklabels=labels_true,
        yticklabels=labels_pred,
        linewidths=0.5,
        linecolor="white",
    )
    ax.set_xlabel("True")
    ax.set_ylabel("Predicted")
    ax.set_title("Confusion Matrix Normalized")
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    print(f"Saved confusion matrix to: {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Plot a custom normalized confusion matrix")
    parser.add_argument("--out", type=str, default="./confusion_matrix_custom.png", help="Output image path")
    # desired diagonal recalls
    parser.add_argument("--drowning", type=float, default=0.95, help="Recall for Drowning (diagonal)")
    parser.add_argument("--swimming", type=float, default=0.87, help="Recall for Swimming (diagonal)")
    # misclassification proportions (per true column)
    parser.add_argument("--drown_to_swim", type=float, default=0.03, help="True Drowning misclassified as Swimming")
    parser.add_argument("--swim_to_drown", type=float, default=0.06, help="True Swimming misclassified as Drowning")
    # background column (false positives distribution on background)
    parser.add_argument("--bg_to_drown", type=float, default=0.35, help="True background predicted as Drowning proportion")
    parser.add_argument("--bg_to_swim", type=float, default=0.65, help="True background predicted as Swimming proportion")
    args = parser.parse_args()

    mat = build_matrix(
        drown_diag=args.drowning,
        drown_to_swim=args.drown_to_swim,
        swim_diag=args.swimming,
        swim_to_drown=args.swim_to_drown,
        bg_to_drown=args.bg_to_drown,
        bg_to_swim=args.bg_to_swim,
    )
    plot_confusion(mat, args.out)


if __name__ == "__main__":
    main()

