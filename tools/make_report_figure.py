from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.image as mpimg


BASE_DIR = Path(__file__).resolve().parent.parent
PLOTS_DIR = BASE_DIR / "resultplots"
OUTPUT = PLOTS_DIR / "report_schedule_comparison.png"


ROWS = [
    (
        "Full Utilization (U = 1)",
        [
            PLOTS_DIR / "gantt_DM_wcet_Full_Utilization_Unique_Periods_taskset.png",
            PLOTS_DIR / "gantt_RM_wcet_Full_Utilization_Unique_Periods_taskset.png",
            PLOTS_DIR / "gantt_EDF_wcet_Full_Utilization_Unique_Periods_taskset.png",
        ],
    ),
    (
        "High Utilization (U < 1)",
        [
            PLOTS_DIR / "gantt_DM_wcet_High_Utilization_NonUnique_Periods_taskset.png",
            PLOTS_DIR / "gantt_RM_wcet_High_Utilization_NonUnique_Periods_taskset.png",
            PLOTS_DIR / "gantt_EDF_wcet_High_Utilization_NonUnique_Periods_taskset.png",
        ],
    ),
]

COLUMN_TITLES = ["DM", "RM", "EDF"]


def draw_panel(ax, image_path: Path, title: str):
    ax.set_title(title, fontsize=14, pad=8)
    ax.set_xticks([])
    ax.set_yticks([])

    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(1.2)
        spine.set_color("black")

    if image_path.exists():
        image = mpimg.imread(image_path)
        ax.imshow(image)
    else:
        ax.set_facecolor("#f7f7f7")
        ax.text(
            0.5,
            0.5,
            f"Missing image:\n{image_path.name}",
            ha="center",
            va="center",
            fontsize=11,
            color="crimson",
            transform=ax.transAxes,
        )


def main():
    fig, axes = plt.subplots(
        nrows=len(ROWS),
        ncols=len(COLUMN_TITLES),
        figsize=(18, 8.5),
        constrained_layout=True,
    )

    if len(ROWS) == 1:
        axes = [axes]

    for row_index, (row_label, image_paths) in enumerate(ROWS):
        row_axes = axes[row_index]

        for col_index, (ax, image_path, col_title) in enumerate(
            zip(row_axes, image_paths, COLUMN_TITLES)
        ):
            draw_panel(ax, image_path, col_title)

            if col_index == 0:
                ax.set_ylabel(
                    row_label,
                    fontsize=14,
                    rotation=90,
                    labelpad=30,
                    weight="bold",
                )

    fig.suptitle(
        "Schedule Comparison Across Utilization Levels",
        fontsize=18,
        weight="bold",
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved report figure to {OUTPUT}")


if __name__ == "__main__":
    main()
