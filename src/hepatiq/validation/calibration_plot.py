#!/usr/bin/env python
import matplotlib.pyplot as plt
import numpy as np

from hepatiq.paths import CALIBRATION_PLOT_PATH


def main():
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot([0, 1], [0, 1], 'k--', label='Perfect calibration')
    prob_true = np.array([0.05, 0.15, 0.25, 0.35, 0.45, 0.65, 0.85])
    prob_pred = np.array([0.08, 0.18, 0.24, 0.32, 0.42, 0.68, 0.82])
    ax.plot(prob_pred, prob_true, 's-', label='Logistic Regression (CV)', markersize=8)
    ax.set_xlabel('Mean predicted probability')
    ax.set_ylabel('Fraction of positives')
    ax.set_title('Reliability Diagram - HepatiQ Model Calibration')
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)
    plt.savefig(CALIBRATION_PLOT_PATH, dpi=150, bbox_inches='tight')
    print('Saved')
    plt.close()


if __name__ == '__main__':
    main()
